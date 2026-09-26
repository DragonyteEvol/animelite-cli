import re
from html import unescape

from core import cliente
from core.modelo import Embed, Stream

_RE_M3U8 = re.compile(r"(https?://[^\"'\s<>\\]+\.m3u8[^\"'\s<>\\]*)")


def resolver(embed: Embed) -> list:
    html, final = cliente.get_text(
        embed.url, timeout=15, referer=embed.pagina or "https://hqq.tv/"
    )
    if not html:
        return []
    for m in _RE_M3U8.findall(unescape(html.replace("\\/", "/"))):
        if ".m3u8" in m:
            return [
                Stream(
                    host="netu",
                    url=m,
                    referer=final or embed.url,
                    tipo="hls",
                )
            ]
    return []


__all__ = ["resolver"]