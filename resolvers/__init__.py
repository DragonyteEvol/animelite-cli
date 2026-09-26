_modulos = {}


def _cargar():
    global _modulos
    if _modulos:
        return
    import importlib

    for nombre in ("voe", "yourupload", "mp4upload", "packer", "okru", "directo", "maru", "netu", "respaldo"):
        try:
            _modulos[nombre] = importlib.import_module(f".{nombre}", __name__)
        except Exception as exc:
            print(f"  ! resolver {nombre} no cargable: {exc}")


EMBED_HOSTS = {
    "voe": "voe",
    "voe.sx": "voe",
    "voeun": "voe",
    "jamesbornmain.com": "voe",
    "yourves": "voe",
    "yourves.com": "voe",
    "yourupload": "yourupload",
    "vidcache": "yourupload",
    "mp4upload": "mp4upload",
    "mp4upload.com": "mp4upload",
    "vidhide": "packer",
    "vidhidevip": "packer",
    "callistanise": "packer",
    "streamwish": "packer",
    "sfastwish": "packer",
    "flaswish": "packer",
    "mixdrop": "packer",
    "mixdrop.top": "packer",
    "mixdrop.to": "packer",
    "mixdrop.co": "packer",
    "mixdrop.is": "packer",
    "mxdrop": "packer",
    "mxdrop.top": "packer",
    "mdy48tn97": "packer",
    "mdy48tn97.com": "packer",
    "mixdroop": "packer",
    "mixdroop.bz": "packer",
    "filemoon": "packer",
    "bysekoze": "packer",
    "doodstream": "packer",
    "doodstream.com": "packer",
    "playmogo": "packer",
    "playmogo.com": "packer",
    "luluvdo": "packer",
    "luluvdo.com": "packer",
    "swhoi": "packer",
    "swhoi.com": "packer",
    "voeun": "voe",
    "ok.ru": "okru",
    "okru": "okru",
    "videoembed": "okru",
    "sw": "packer",
    "uqload": "directo",
    "uqload.com": "directo",
    "uqload.vc": "directo",
    "solidfiles": "directo",
    "solidfiles.com": "directo",
    "videobin": "directo",
    "videobin.co": "directo",
    "embedwish": "directo",
    "embedwish.com": "directo",
    "vid-guard": "directo",
    "vid-guard.com": "directo",
    "d-s": "directo",
    "d-s.io": "directo",
    "goodstream": "directo",
    "goodstream.uno": "directo",
    "goodstream.one": "directo",
    "maru": "maru",
    "my.mail.ru": "maru",
    "netu": "netu",
    "hqq.tv": "netu",
    "hqq": "netu",
    "streamvid": "netu",
}


def _host_para(embed) -> str:
    if getattr(embed, "modulo", None):
        return embed.modulo
    h = (embed.host or "").lower()
    h2 = h.split(".")[-2] if "." in h else ""
    for k in (h, h2):
        if k in EMBED_HOSTS:
            return EMBED_HOSTS[k]
    return ""


def aplicar(embeds: list, max_workers=5):
    _cargar()
    if not embeds:
        return [], []
    import time
    from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED


    def _uno(e):
        clave = _host_para(e)
        mod = _modulos.get(clave)
        if not mod:
            return e, None, (e.host, "resolver no implementado")
        try:
            r = mod.resolver(e)
            return e, r, None
        except Exception as exc:
            return e, None, (e.host, str(exc)[:80])

    streams = []
    fallidos = []
    limite = 4.0
    tope = 8.0
    t0 = time.perf_counter()
    ex = ThreadPoolExecutor(max_workers=max_workers)
    try:
        futuros = set(ex.submit(_uno, e) for e in embeds)
        pendientes = futuros
        while pendientes:
            t = time.perf_counter() - t0
            if t >= tope:
                break
            restante = limite - t
            if restante <= 0:
                if streams:
                    break
                restante = 2.0
            restante = min(restante, tope - t)
            done, pendientes = wait(
                pendientes, timeout=restante, return_when=FIRST_COMPLETED
            )
            for f in done:
                _e, r, err = f.result()
                if err:
                    fallidos.append(err)
                elif r:
                    streams.extend(r)
        for f in futuros:
            f.cancel()
    finally:
        ex.shutdown(wait=False)
    return streams, fallidos

__all__ = ["aplicar", "EMBED_HOSTS"]