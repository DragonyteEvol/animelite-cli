import base64
import json
import re

from core.cliente import get_text
from core.modelo import Embed, Stream

ROT13 = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
    "NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm",
)
SEPS = ["@$", "^^", "~@", "%?", "*~", "!!", "#&"]

# Espejos reales conocidos de Voe (se rotan; el embed hostname puede cambiar).
MIRRORS = [
    "jamesbornmain.com",
]

_BLOB_RE = [
    re.compile(r'<script type="application/json">\s*(.*?)\s*</script>', re.S),
    re.compile(r'<script class="voe-player">(.*?)</script>', re.S),
    re.compile(r'\[\s*\{[^]]*"source"[^]]*\}\s*\]', re.S),
]
_REDIR = re.compile(r'location\.href\s*=\s*["\']([^"\']+)["\']', re.I)
_HOST = re.compile(r"https?://([^/\"']+)")


def _decodificar_blob(blob: str) -> dict:
    s = blob.translate(ROT13)
    for sep in SEPS:
        s = s.replace(sep, "_")
    s = s.replace("_", "")
    raw = base64.b64decode(s + "=" * (-len(s) % 4))
    raw = bytes((b - 3) & 0xFF for b in raw)[::-1]
    data = base64.b64decode(raw.decode("latin-1"))
    return json.loads(data.decode("utf-8"))


def _extraer_blob(html: str):
    for rx in _BLOB_RE:
        m = rx.search(html)
        if m:
            txt = m.group(1) if m.groups() else m.group(0)
            try:
                return _decodificar_blob(txt)
            except Exception:
                continue
    return None


def _candidatos(url: str, code: str) -> list:
    """URLs a probar: la original + espejos conocidos, sin duplicados."""
    cand = [url]
    m = _HOST.search(url)
    host_original = m.group(1) if m else ""
    for host in MIRRORS + [host_original] if host_original else MIRRORS:
        cand.append(f"https://{host}/e/{code}")
    vistos = set()
    salida = []
    for u in cand:
        base = u.split("?")[0]
        if base in vistos:
            continue
        vistos.add(base)
        salida.append(u)
    return salida


def _procesar(html: str, final: str):
    if "source" in html and ("application/json" in html or '<script' in html):
        blob = _extraer_blob(html)
        if blob:
            out = []
            source = blob.get("source")
            if source:
                out.append(Stream(host="voe", url=source, referer=final, tipo="hls"))
            directo = blob.get("direct_access_url")
            if directo and blob.get("direct_access_allowed"):
                out.append(Stream(host="voe", url=directo, referer=final, tipo="mp4"))
            if out:
                return out
    return None


def resolver(embed: Embed) -> list:
    code = re.search(r"/e/([A-Za-z0-9_-]+)", embed.url)
    if not code:
        raise ValueError(f"URL Voe sin codigo: {embed.url}")
    code = code.group(1)

    timeout = 8
    candidatos = _candidatos(embed.url, code)
    errores = []

    def _probar(url, reintentos, to):
        visitadas = set()
        for _ in range(reintentos):
            if url in visitadas:
                return None
            visitadas.add(url)
            html, final = get_text(url, timeout=to, referer=embed.pagina)
            if html is None:
                errores.append(f"sin respuesta {url}")
                return None
            r = _procesar(html, final)
            if r:
                return r
            redir = _REDIR.search(html)
            if redir:
                target = redir.group(1)
                if not target.startswith("http"):
                    target = f"https://{_HOST.search(url).group(1)}{target}"
                url = target.replace("&amp;", "&")
                continue
            errores.append(f"sin blob {url}")
            return None
        return None

    from concurrent.futures import ThreadPoolExecutor, as_completed
    ex = ThreadPoolExecutor(max_workers=len(candidatos))
    try:
        futuros = {ex.submit(_probar, url, 1, timeout): url for url in candidatos}
        for f in as_completed(futuros):
            r = f.result()
            if r:
                # cancelar los que aun corren y devolver ya
                for g in futuros:
                    g.cancel()
                return r
    finally:
        ex.shutdown(wait=False)

    raise ValueError("Voe agoto espejos: " + " ; ".join(errores) or "sin detalles")


__all__ = ["resolver"]