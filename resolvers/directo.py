import re
from html import unescape

from core import cliente
from core.modelo import Embed, Stream

HOSTS = (
    "uqload",
    "solidfiles",
    "videobin",
    "embedwish",
    "vid-guard",
    "d-s",
)

_RE_M3U8 = re.compile(r'"(https?://[^"]+\.m3u8[^"]*)"')
_RE_MP4 = re.compile(r'"(https?://[^"]+\.mp4[^"]*)"')


def resolver(embed: Embed) -> list:
    html, _ = cliente.get_text(
        embed.url, timeout=12, referer=embed.pagina or f"https://{embed.host}/"
    )
    if not html:
        return []
    html = unescape(html.replace("\\/", "/"))
    urls = []
    for m in _RE_M3U8.findall(html):
        urls.append((m, "hls"))
    if not urls:
        for m in _RE_MP4.findall(html):
            if not m.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
                urls.append((m, "mp4"))
    return [
        Stream(
            host=f"directo/{embed.host}",
            url=u,
            referer=embed.pagina or f"https://{embed.host}/",
            tipo=t,
        )
        for u, t in urls
    ]


__all__ = ["resolver"]