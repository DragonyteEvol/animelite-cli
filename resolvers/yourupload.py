import base64
import json
import re
from html import unescape
from urllib.parse import unquote

from core.cliente import get_text
from core.modelo import Embed, Stream

HOSTS = ("www.yourupload.com", "yourupload.com", "vidcache.net")

_PATTERNS = [
    re.compile(r'"file"\s*:\s*"((?:[^"\\]|\\.)*)"'),
    re.compile(r'"file"\s*:\s*\'(?:[^\'\\]|\\.)*\''),
    re.compile(r'jwplayerOptions\.file\s*=\s*["\']([^"\']+)'),
    re.compile(r'<meta\s+property="og:video"\s+content="([^"]+)"'),
    re.compile(r"https?://vidcache\.net:[0-9]+/[^\s\"'<>]+\.mp4", re.I),
]


def resolver(embed: Embed) -> list:
    html, final = get_text(embed.url, timeout=20, referer=embed.pagina)
    if html is None:
        raise ValueError(f"YourUpload sin respuesta: {embed.url}")

    candidatos = []
    for rx in _PATTERNS:
        for m in rx.finditer(html):
            v = m.group(1) if m.groups() else m.group(0)
            v = unquote(unescape(v))
            if v.startswith("//"):
                v = "https:" + v
            if v.lower().endswith((".mp4", ".webm", ".m3u8")) and v.startswith("http"):
                candidatos.append(v)

    elegidos = [c for c in candidatos if "vidcache.net" in c or "cdn" in c or ".mp4" in c]
    if not elegidos:
        elegidos = candidatos
    if not elegidos:
        raise ValueError(f"YourUpload sin mp4 en {final}")

    visto = set()
    out = []
    for u in elegidos:
        if u in visto:
            continue
        visto.add(u)
        tipo = "mp4" if u.lower().endswith(".mp4") else "hls"
        out.append(Stream(host="yourupload", url=u, referer=final, tipo=tipo))
    return out


__all__ = ["resolver"]