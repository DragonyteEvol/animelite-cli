import re
import urllib.parse
from html import unescape

from core.cliente import get_text, request
from core.modelo import Anime, Embed, Episodio

BASE = "https://vww.animeflv.one"
REF = "https://animeflv.one/"

_RE_CARD = re.compile(
    r'<article class="li">.*?<a href="(\./anime/[^"]+)"[^>]*title="Ver\s+Anime\s+(.*?)"\s*>',
    re.S,
)
_RE_TITLE_SUF = re.compile(r"\s*(?:Sub\s+espa[ñn]ol\s+latino|Online\s+Gratis)\s*$", re.I)
_RE_EPS = re.compile(r"var eps\s*=\s*\[((?:\[[^\]]*\]\s*,?\s*)+)\];")
_RE_ENCRYPT = re.compile(r'data-encrypt="([^"]+)"')
_RE_LI = re.compile(
    r"<li[^>]*encrypt=\"([0-9a-fA-F]+)\"[^>]*>(.*?)</li>", re.S
)
_RE_SPAN = re.compile(r"<span>(.*?)</span>", re.S)

_SALTOS = {"mega", "mediafire"}


def _hex(texto):
    try:
        return bytes.fromhex(texto).decode("utf-8")
    except Exception:
        return ""


def _dec_eps(txt):
    out = []
    for m in re.finditer(r"\[\"(\d+)\",\"[0-9]\",\"([^\"]*)\"\]", txt):
        out.append((int(m.group(1)), m.group(2)))
    return out


def buscar(query: str) -> list:
    url = f"{BASE}/animes?buscar={urllib.parse.quote(query.strip())}"
    html, _ = get_text(url, referer=REF)
    if html is None:
        return []
    out = []
    for enlace, titulo in _RE_CARD.findall(html):
        t = unescape(re.sub(r"\s+", " ", titulo)).strip()
        t = _RE_TITLE_SUF.sub("", t).strip()
        slug = enlace.split("/anime/")[-1]
        if t:
            out.append(Anime(
                sitio="animeflv", titulo=t, slug=slug,
                url=f"{BASE}/anime/{slug}",
                imagen=f"{BASE}/cdn/img/portada/{slug}.webp",
            ))
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
    m = _RE_EPS.search(html)
    if not m:
        return []
    out = []
    for num, cod in _dec_eps(m.group(1)):
        url = f"{BASE}/ver/{anime.slug}-{num}" + (f"-{cod}" if cod else "")
        out.append(Episodio(numero=num, url=url))
    out.sort(key=lambda e: e.numero)
    return out


def embeds(episodio: Episodio) -> list:
    html, final = get_text(episodio.url, referer=REF)
    if html is None:
        return []
    m = _RE_ENCRYPT.search(html)
    if not m:
        return []
    st, body, _final, _h = request(
        f"{BASE}/flv",
        data={"acc": "opt", "i": m.group(1)},
        referer=episodio.url,
    )
    if st is None or st >= 400:
        return []
    txt = body.decode("utf-8", "replace")
    out = []
    for hexdata, inner in _RE_LI.findall(txt):
        url = _hex(hexdata)
        if not url.startswith("http"):
            continue
        sp = _RE_SPAN.search(inner)
        host = unescape(re.sub(r"<[^>]+>", "", sp.group(1))).strip() if sp else "animeflv"
        if host.lower() in _SALTOS:
            continue
        out.append(Embed(host=host, url=url, pagina=final or episodio.url))
    return out