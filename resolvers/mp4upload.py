import re

from core import cliente
from core.modelo import Embed, Stream


def resolver(embed: Embed):
    html, _ = cliente.get_text(embed.url, referer=embed.pagina)
    if not html:
        return []
    m = re.search(r'src:\s*"((?:https?:)?//[^"]+\.mp4)"', html)
    if not m:
        m = re.search(r'"file"\s*:\s*"((?:https?:)?//[^"]+\.mp4)"', html)
    if not m:
        return []
    url = m.group(1)
    if url.startswith("//"):
        url = "https:" + url
    return [
        Stream(
            host=f"mp4upload/{embed.host}",
            url=url,
            referer=embed.pagina or "https://www.mp4upload.com/",
            tipo="mp4",
        )
    ]


__all__ = ["resolver"]