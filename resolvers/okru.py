import re
from html import unescape

from core.cliente import get_text
from core.modelo import Embed, Stream

HOSTS = ("ok.ru", "okru")


def resolver(embed: Embed) -> list:
    html, final = get_text(embed.url, timeout=20, referer=embed.pagina)
    if html is None:
        raise ValueError(f"Okru sin respuesta: {embed.url}")

    txt = unescape(html)
    m = re.search(r'"hlsManifestUrl"\s*:\s*"(https?[^"\\]+(?:\\u0026[^"\\]*)*)"', txt)
    if not m:
        raise ValueError(f"Okru sin hlsManifestUrl en {final}")

    url = m.group(1).replace("\\u0026", "&")
    if "\\" in url or "\u0026" in url:
        url = url.replace("\\u0026", "&").replace("\\", "")
    return [Stream(host="okru", url=url, referer=final or embed.pagina, tipo="hls")]


__all__ = ["resolver"]