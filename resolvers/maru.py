import re

from core import cliente
from core.modelo import Embed, Stream


def resolver(embed: Embed) -> list:
    m = re.search(r"video/embed/(\d+)", embed.url)
    if not m:
        return []
    vid = m.group(1)
    datos, _ = cliente.get_json(
        f"https://my.mail.ru/+/video/meta/{vid}",
        timeout=15,
        referer=embed.pagina or embed.url,
    )
    if not datos or not datos.get("videos"):
        return []
    videos = [v for v in datos["videos"] if v.get("url")]
    if not videos:
        return []
    for pref in ("1080p", "720p", "480p", "360p"):
        for v in videos:
            if str(v.get("key", "")).lower() == pref:
                elegido = v
                break
        else:
            continue
        break
    else:
        elegido = videos[0]
    url = elegido["url"]
    if url.startswith("//"):
        url = "https:" + url
    return [
        Stream(
            host="maru",
            url=url,
            referer=f"https://my.mail.ru/video/embed/{vid}",
            tipo="mp4",
        )
    ]


__all__ = ["resolver"]