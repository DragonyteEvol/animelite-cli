import time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

from .cliente import UA
from .modelo import Embed, Stream


def _probe_one(stream: Stream, timeout=8, bytes_wanted=64 * 1024):
    import ssl
    import urllib.error
    import urllib.request

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(
        stream.url,
        headers={
            "User-Agent": UA,
            "Accept": "*/*",
            "Range": f"bytes=0-{bytes_wanted - 1}",
        },
    )
    if stream.referer:
        req.add_header("Referer", stream.referer)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            status = r.getcode()
            t_ttfb = (time.perf_counter() - t0) * 1000
            bloque = b""
            while len(bloque) < bytes_wanted:
                block = r.read(min(65536, bytes_wanted - len(bloque)))
                if not block:
                    break
                bloque += block
            t_total = (time.perf_counter() - t0) * 1000
        t_body = max(t_total - t_ttfb, 1)
        mbps = (len(bloque) / 1048576) / (t_body / 1000)
        es_playlist = len(bloque) < 64 * 1024
        ok = True
        motivo = ""
        if es_playlist:
            # Una lista HLS falsa (tracking/json/txt) no reproduce en mpv.
            if b"#EXTM3U" not in bloque and b"#EXT-X" not in bloque:
                ok = False
                motivo = "playlist invalida (sin #EXTM3U)"
        return {
            "host": stream.host,
            "url": stream.url,
            "status": status,
            "ttfb_ms": round(t_ttfb, 1),
            "bytes": len(bloque),
            "mbps": round(mbps, 2),
            "buscado": bytes_wanted,
            "playlist": es_playlist,
            "ok": ok,
            "motivo": motivo,
        }
    except Exception as e:
        return {
            "host": stream.host,
            "url": stream.url,
            "status": getattr(e, "code", None),
            "ttfb_ms": None,
            "bytes": 0,
            "mbps": 0.0,
            "buscado": bytes_wanted,
            "ok": False,
            "error": str(e),
        }


def probar(streams: list, max_workers=8):
    if not streams:
        return []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        results = list(ex.map(_probe_one, streams))
    results.sort(key=lambda r: (not r["ok"], r.get("ttfb_ms") or 1e9))
    return results


def probar_rapido(streams: list, max_workers=8, ventana=1.5):
    """Lanza los probes en paralelo y devuelve el resultado OK de menor TTFB
    entre los que responden dentro de `ventana` segundos. Si ninguno responde
    a tiempo, espera al primero que de OK (hasta el timeout de cada probe).

    Devuelve el mejor (dict) o None si ningun stream responde OK."""
    if not streams:
        return None
    ok = probar_rapido_lista(streams, max_workers=max_workers, ventana=ventana)
    return ok[0] if ok else None


def probar_rapido_lista(streams: list, max_workers=8, ventana=1.5, fallback=3.0):
    """Igual que `probar_rapido` pero devuelve la lista de resultados OK
    ordenados por TTFB (los que respondieron dentro de `ventana`; si ninguno
    responde a tiempo, espera hasta `fallback` s extra por el primer OK).
    Util para reintentos."""
    if not streams:
        return []
    from concurrent.futures import ThreadPoolExecutor

    t0 = time.perf_counter()
    ok = []
    vistos = set()
    ex = ThreadPoolExecutor(max_workers=max_workers)
    try:
        futuros = [ex.submit(_probe_one, s) for s in streams]
        pendientes = set(futuros)
        while pendientes:
            restante = ventana - (time.perf_counter() - t0)
            if restante <= 0:
                break
            done, pendientes = wait(
                pendientes, timeout=restante, return_when=FIRST_COMPLETED
            )
            for f in done:
                r = f.result()
                if r["ok"] and r["url"] not in vistos:
                    vistos.add(r["url"])
                    ok.append(r)
        if not ok:
            # dar una ultima oportunidad al primer OK (los probes que acabaron
            # mal ya devolvieron; esperar solo hasta `fallback` por los lentos)
            t_fin = time.perf_counter() + fallback
            while pendientes:
                restante = t_fin - time.perf_counter()
                if restante <= 0:
                    break
                done, pendientes = wait(
                    pendientes, timeout=restante, return_when=FIRST_COMPLETED
                )
                for f in done:
                    r = f.result()
                    if r["ok"] and r["url"] not in vistos:
                        ok.append(r)
                        break
                if ok:
                    break
        for f in futuros:
            f.cancel()
    finally:
        ex.shutdown(wait=False)
    ok.sort(key=lambda r: r["ttfb_ms"])
    return ok