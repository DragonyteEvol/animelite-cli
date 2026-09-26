import re

from core import cliente
from core.modelo import Embed, Stream


def _base_n(c, a):
    s = ""
    while True:
        s = ("0123456789abcdefghijklmnopqrstuvwxyz"[c % a] if c % a <= 35 else chr(c % a + 29)) + s
        c //= a
        if c == 0:
            return s


def _desempacar(trozo):
    m = re.search(
        r"',\s*(\d+)\s*,\s*(\d+)\s*,\s*'((?:\\.|[^'\\])*)'\.split\('\|'\)",
        trozo,
        re.S,
    )
    if not m:
        return None
    radix, count, wordlist = int(m.group(1)), int(m.group(2)), m.group(3)
    cierre = trozo.find("}")
    body0 = trozo[cierre + 1 :]
    j = body0.find("('")
    body = body0[j + 2 :]
    k = wordlist.split("|")
    while len(k) < count:
        k.append("")
    for i in range(count):
        token = _base_n(i, radix)
        if token:
            body = re.sub(r"\b" + re.escape(token) + r"\b", k[i] or "", body)
    return body


def resolver(embed: Embed):
    html, _ = cliente.get_text(embed.url, timeout=8, referer=embed.pagina)
    if not html:
        return []
    idx = html.find("eval(function(p,a,c,k,e,d)")
    if idx == -1:
        return []
    trozo = html[idx : html.find("</script>", idx)]
    try:
        d = _desempacar(trozo)
    except Exception:
        return []
    if not d:
        return []
    urls = []
    for m in re.finditer(r'"(https://[^"]+)"', d):
        u = m.group(1)
        if ".m3u8" in u:
            urls.append(u)

    salida = []
    for u in urls:
        ref = embed.pagina or "https://jkanime.net/"
        salida.append(Stream(host=f"packer/{embed.host}", url=u, referer=ref, tipo="hls"))
    return salida


__all__ = ["resolver"]