from core.modelo import Embed, Stream


def resolver(embed: Embed) -> list:
    import yt_dlp

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "socket_timeout": 20,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": embed.pagina or "https://jkanime.net/",
            "Accept-Language": "es-419,es;q=0.9",
        },
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(embed.url, download=False)
        except Exception:
            return []
        if not info:
            return []
    salida = []
    for f in info.get("formats") or []:
        u = f.get("url")
        if not u or not u.startswith("http"):
            continue
        ext = (f.get("ext") or "").lower()
        tipo = "hls" if (f.get("protocol") or "").startswith("m3u8") or ".m3u8" in u else "mp4"
        salida.append(
            Stream(
                host=f"ytdlp/{embed.host}",
                url=u,
                referer=embed.pagina,
                tipo=tipo,
            )
        )
    return salida


__all__ = ["resolver"]