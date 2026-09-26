import base64
import json
import re
from html import unescape

from core.cliente import get_json, get_text
from core.modelo import Anime, Embed, Episodio

BASE = "https://jkanime.net"

_RE_ANIME = re.compile(
    r'<h5><a\s+href="(https://jkanime\.net/[^"/]+/)"[^>]*>(.*?)</a></h5>', re.S
)
_RE_ID = re.compile(r"ajax/episodes/(\d+)")
_RE_TOKEN = re.compile(r'<meta name="csrf-token" content="([^"]+)"')
_RE_SERVERS = re.compile(r"var\s+servers\s*=\s*(\[.*?\]);", re.S)

EXCLUIR_HOSTS = ("mediafire", "mega", "streamtape")


def _slug(query: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", query.lower()).strip("_")


def _normalizar(titulo):
    from unicodedata import normalize

    t = normalize("NFKD", titulo.lower())
    t = "".join(c for c in t if ord(c) < 128)
    return re.sub(r"[^a-z0-9]+", " ", t)


def buscar(query: str) -> list:
    slug = _slug(query)
    if not slug:
        return []
    html, _ = get_text(f"{BASE}/buscar/{slug}")
    if html is None:
        return []
    tokens = set(_normalizar(query).split())
    out = []
    for url, titulo in _RE_ANIME.findall(html):
        t = re.sub(r"<[^>]+>", "", titulo)
        t = unescape(re.sub(r"\s+", " ", t)).strip()
        if not t:
            continue
        # jkanime, sin coincidencias, devuelve un listado general sin
        # filtrar: solo aceptar animes que realmente matcheen la query.
        nt = set(_normalizar(t).split())
        if not tokens or not (tokens & nt):
            continue
        out.append(
            Anime(sitio="jkanime", titulo=t, slug=url.rstrip("/").split("/")[-1], url=url)
        )
    return out


def episodios(anime: Anime, limite=999) -> list:
    html, _ = get_text(anime.url)
    if html is None:
        return []
    mid = _RE_ID.search(html)
    token = _RE_TOKEN.search(html)
    if not mid or not token:
        return []
    anime_id = mid.group(1)
    datos, _ = get_json(
        f"{BASE}/ajax/episodes/{anime_id}/1",
        referer=anime.url,
        data={"_token": token.group(1)},
    )
    if not datos:
        return []
    total = int(datos.get("total") or 0)
    if total <= 0:
        return []
    if total > 16 and limite > 16:
        paginas = (total + 15) // 16
        for p in range(2, min(paginas, limite // 16 + 1) + 1):
            if p > 1:
                extra, _ = get_json(
                    f"{BASE}/ajax/episodes/{anime_id}/{p}",
                    referer=anime.url,
                    data={"_token": token.group(1)},
                )
                if extra:
                    datos["data"].extend(extra.get("data") or [])
                else:
                    break
    epis = []
    for item in datos.get("data") or []:
        num = item.get("id")
        titulo = item.get("title") or ""
        m = re.search(r"-\s*(\d+)\s*$", titulo)
        if m:
            num = int(m.group(1))
        if not isinstance(num, int):
            continue
        epis.append(Episodio(numero=num, url=f"{BASE}/{anime.slug}/{num}/"))
    epis.sort(key=lambda e: e.numero)
    return epis


def embeds(episodio: Episodio) -> list:
    html, final = get_text(episodio.url)
    if html is None:
        return []
    m = _RE_SERVERS.search(html)
    if not m:
        return []
    try:
        arr = json.loads(m.group(1))
    except Exception:
        return []
    out = []
    for s in arr:
        host = str(s.get("server") or "")
        try:
            url = base64.b64decode(s.get("remote") or "").decode("utf-8", "replace").strip()
        except Exception:
            continue
        if not url.startswith("http"):
            continue
        if host.lower() in EXCLUIR_HOSTS:
            continue
        out.append(Embed(host=host, url=url, pagina=final))
    return out