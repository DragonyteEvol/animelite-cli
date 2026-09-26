import base64
import json
import re
import urllib.parse
from html import unescape

from core.cliente import get_text
from core.modelo import Anime, Embed, Episodio

BASE = "https://monoschinos.st"
REF = BASE + "/"

_RE_CARD = re.compile(
    r'<a href="(' + re.escape(BASE) + r'/anime/[^"]+)"[^>]*>.*?<h3[^>]*>(.*?)</h3>',
    re.S,
)
_RE_AJAX = re.compile(r'data-ajax="[^"]*/ajax/ajax_pagination/(\d+)"')
_RE_PLAYER = re.compile(r'class="srv[^"]*"[^>]*data-player="([^"]+)"')


def _limpia(texto):
    return unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", texto))).strip()


def buscar(query: str) -> list:
    url = f"{BASE}/buscar?q={urllib.parse.quote(query.strip())}"
    html, _ = get_text(url, referer=REF)
    if html is None:
        return []
    out = []
    for enlace, titulo in _RE_CARD.findall(html):
        t = _limpia(titulo)
        slug = enlace.split("/anime/")[-1]
        if t and slug:
            out.append(Anime(sitio="monoschinos", titulo=t, slug=slug, url=enlace))
    vistos = set()
    unicos = []
    for a in out:
        if a.slug not in vistos:
            vistos.add(a.slug)
            unicos.append(a)
    return unicos


def episodios(anime: Anime) -> list:
    html, _ = get_text(anime.url or f"{BASE}/anime/{anime.slug}", referer=REF)
    if html is None:
        return []
    m = _RE_AJAX.search(html)
    if not m:
        return []
    pag, _ = get_text(f"{BASE}/ajax/caplist/{m.group(1)}", referer=anime.url)
    if not pag:
        return []
    try:
        datos = json.loads(pag)
    except Exception:
        return []
    out = []
    for cap in datos.get("caps") or []:
        num, u = cap.get("episodio"), cap.get("url")
        if num and u:
            out.append(Episodio(numero=int(num), url=u))
    out.sort(key=lambda e: e.numero)
    return out


def embeds(episodio: Episodio) -> list:
    html, final = get_text(episodio.url, referer=REF)
    if html is None:
        return []
    out = []
    for b64 in _RE_PLAYER.findall(html):
        try:
            txt = base64.b64decode(b64 + "=" * (-len(b64) % 4)).decode(
                "utf-8", "replace"
            )
        except Exception:
            continue
        if not txt.startswith("http"):
            continue
        host = (urllib.parse.urlparse(txt).netloc or "monoschinos").lower()
        if host.startswith("www."):
            host = host[4:]
        out.append(Embed(host=host, url=txt, pagina=final or episodio.url))
    return out


__all__ = ["buscar", "episodios", "embeds"]