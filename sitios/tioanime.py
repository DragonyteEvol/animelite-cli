import re
from html import unescape

from core.cliente import get_text
from core.modelo import Anime, Embed, Episodio

BASE = "https://tioanime.com"

_RE_ANIME = re.compile(
    r'<article class="anime">\s*<a href="(/anime/[^"]+)">(.*?)</a>', re.S
)
_RE_IMG = re.compile(r'<img[^>]+src="([^"]+)"', re.S)
_RE_EPISODES = re.compile(r"var episodes\s*=\s*(\[[^\]]*\])")
_RE_VIDEOS = re.compile(r"var videos\s*=\s*(\[.*?\])\s*;", re.S)
_RE_TOTAL = re.compile(r"([0-9]+)\s+episodios", re.I)


def _titulo(bloque):
    m = re.search(r'<h3 class="title">(.*?)</h3>', bloque, re.S)
    if not m:
        return ""
    t = unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))))
    return t.strip()


def _imagen(bloque):
    m = _RE_IMG.search(bloque)
    if not m:
        return ""
    src = unescape(m.group(1)).strip()
    if src.startswith("//"):
        return "https:" + src
    if src.startswith("http"):
        return src
    if src.startswith("/"):
        return BASE + src
    return BASE + "/" + src


def buscar(query: str) -> list:
    html, _ = get_text(f"{BASE}/directorio?q={query.strip()}")
    if html is None:
        return []
    out = []
    for slug, bloque in _RE_ANIME.findall(html):
        t = _titulo(bloque)
        if t:
            out.append(Anime(
                sitio="tioanime", titulo=t, slug=slug.split("/")[-1],
                url=BASE + slug, imagen=_imagen(bloque),
            ))
    return out


def episodios(anime: Anime) -> list:
    html, _ = get_text(anime.url or f"{BASE}/anime/{anime.slug}")
    if html is None:
        return []
    m = _RE_EPISODES.search(html)
    if not m:
        return []
    nums = [int(n) for n in re.findall(r"\d+", m.group(1))]
    nums = sorted(set(nums), reverse=True)
    return [Episodio(numero=n, url=f"{BASE}/ver/{anime.slug}-{n}") for n in nums]


def embeds(episodio: Episodio) -> list:
    html, final = get_text(episodio.url)
    if html is None:
        return []
    m = _RE_VIDEOS.search(html)
    if not m:
        return []
    try:
        import json

        arr = json.loads(m.group(1))
    except Exception:
        return []
    out = []
    for item in arr:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        host = str(item[0])
        url = str(item[1])
        if not url.startswith("http"):
            continue
        if host.lower() in ("mega", "mediafire"):
            continue
        out.append(Embed(host=host, url=url, pagina=final))
    return out