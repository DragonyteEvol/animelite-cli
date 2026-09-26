import http.cookiejar
import ssl
import threading
import urllib.error
import urllib.parse
import urllib.request

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE

_cj = http.cookiejar.CookieJar()
_opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(_cj),
    urllib.request.HTTPSHandler(context=_CTX),
)

# Limite global de conexiones HTTP simultaneas (evita saturar la red/bloqueos).
SEM = threading.Semaphore(6)


def _base_headers():
    return {
        "User-Agent": UA,
        "Accept": "*/*",
        "Accept-Language": "es-419,es;q=0.9",
    }


def request(url, timeout=25, referer=None, headers=None, data=None):
    h = _base_headers()
    if referer:
        h["Referer"] = referer
    if headers:
        h.update(headers)
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode()
        h.setdefault("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8")
        h.setdefault("X-Requested-With", "XMLHttpRequest")
    req = urllib.request.Request(url, data=body, headers=h)
    try:
        with SEM:
            with _opener.open(req, timeout=timeout) as r:
                return r.getcode(), r.read(), r.geturl(), r.headers
    except urllib.error.HTTPError as e:
        return e.code, b"", e.url or url, e.headers
    except Exception as e:
        return None, str(e).encode(), url, None


def get_text(url, timeout=25, referer=None, headers=None):
    status, body, final_url, h = request(url, timeout, referer, headers)
    if status is None or status >= 400:
        return None, final_url
    encoding = "utf-8"
    if h is not None:
        ct = h.get("Content-Type", "")
        if "charset=" in ct:
            encoding = ct.split("charset=")[-1].split(";")[0].strip()
    try:
        text = body.decode(encoding)
    except (UnicodeDecodeError, LookupError):
        text = body.decode("utf-8", "replace")
    return text, final_url


def get_json(url, timeout=25, referer=None, headers=None, data=None):
    status, body, final_url, _h = request(url, timeout, referer, headers, data)
    if status is None or status >= 400:
        return None, final_url
    import json

    try:
        return json.loads(body.decode("utf-8")), final_url
    except Exception:
        return None, final_url