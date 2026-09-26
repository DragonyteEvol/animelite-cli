import os
import re
import sys
import time
import unicodedata
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import reproductor
from core import probe
from resolvers import aplicar
from sitios import animeflv, jkanime, tioanime

SITIOS = [tioanime, jkanime, animeflv]

try:
    import colorama
    colorama.just_fix_windows_console()
except ImportError:
    pass

COL = {
    "verde": "\033[92m",
    "amarillo": "\033[93m",
    "cian": "\033[96m",
    "rojo": "\033[91m",
    "neg": "\033[0m",
}


def sin_tildes(texto):
    """Quita tildes y caracteres no-ASCII (la consola ANSI los muestra mal)."""
    t = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in t if ord(c) < 128)


def pintar(texto, color):
    print(f"{COL[color]}{sin_tildes(texto)}{COL['neg']}")


def normalizar(titulo):
    t = unicodedata.normalize("NFKD", titulo.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


@dataclass
class Grupo:
    titulo: str
    coincidencias: list = field(default_factory=list)

    def sitios(self):
        return sorted({c[0].__name__.split(".")[-1] for c in self.coincidencias})


def agrupar(todos):
    grupos = {}
    for sitio_mod, anime in todos:
        clave = normalizar(anime.titulo)
        if clave not in grupos:
            grupos[clave] = Grupo(titulo=anime.titulo)
        grupos[clave].coincidencias.append((sitio_mod, anime))
    return list(grupos.values())


def banner():
    pintar("=" * 60, "cian")
    pintar("  ANIME CLI  -  buscador y reproductor por consola", "cian")
    pintar("=" * 60, "cian")


LIMITE_RESULTADOS = 15


def buscar():
    """Busca en paralelo en todos los sitios y devuelve (grupo, animes).

    Reintenta hasta 3 veces ante fallos de conexion. Devuelve ("salir", None)
    si la consulta esta vacia, o (None, None) si se agotaron los intentos."""
    query = input("Buscar anime").strip()
    if not query:
        return "salir", None
    from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

    LIMITE_QUERY = 8.0
    INTENTOS = 3
    for intento in range(1, INTENTOS + 1):
        resultados = {}
        errores = {}
        t0 = time.perf_counter()
        ex = ThreadPoolExecutor(max_workers=len(SITIOS))
        try:
            futuros = {ex.submit(s.buscar, query): s for s in SITIOS}
            pendientes = set(futuros)
            while pendientes:
                restante = LIMITE_QUERY - (time.perf_counter() - t0)
                if restante <= 0:
                    break
                done, pendientes = wait(pendientes, timeout=restante,
                                        return_when=FIRST_COMPLETED)
                for f in done:
                    sitio = futuros[f]
                    try:
                        resultados[sitio] = f.result()
                    except Exception as exc:
                        errores[sitio] = str(exc)
            for f in futuros:
                f.cancel()
        finally:
            ex.shutdown(wait=False)

        todos = []
        for sitio in SITIOS:
            if sitio in errores:
                continue
            if sitio in resultados:
                todos.extend((sitio, a) for a in resultados[sitio])
        if todos:
            break
        if intento < INTENTOS:
            pintar(
                f"Fallo de conexion al buscar. Reintentando ({intento + 1}/"
                f"{INTENTOS}) ...",
                "amarillo",
            )
            time.sleep(2)
    else:
        pintar("No se pudo buscar (probable fallo de conexion).", "rojo")
        return None, None

    grupos = agrupar(todos)[:LIMITE_RESULTADOS]
    pintar(f"\nResultados ({len(grupos)} anime(s), maximo {LIMITE_RESULTADOS}):", "amarillo")
    for i, g in enumerate(grupos):
        print(f"  [{i}] {sin_tildes(g.titulo)}")
    while True:
        sel = input("Elige un anime (numero): ").strip()
        if sel.isdigit() and int(sel) < len(grupos):
            return grupos[int(sel)], [c[1] for c in grupos[int(sel)].coincidencias]
        print("Seleccion invalida.")


def _paralelo_por_clave(entradas, fn, limite=8.0):
    """Ejecuta fn(key) en paralelo. Devuelve dict key -> resultado (o None si
    se colgo). Imprime errores capturados por fn."""
    from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

    ex = ThreadPoolExecutor(max_workers=len(entradas))
    try:
        futuros = {ex.submit(fn, k): i for i, k in enumerate(entradas)}
        pendientes = set(futuros)
        envio = {}
        t0 = time.perf_counter()
        while pendientes:
            restante = limite - (time.perf_counter() - t0)
            if restante <= 0:
                break
            done, pendientes = wait(pendientes, timeout=restante,
                                    return_when=FIRST_COMPLETED)
            for f in done:
                envio[futuros[f]] = f.result()
        for f in futuros:
            f.cancel()
        return envio
    finally:
        ex.shutdown(wait=False)


def recoger_episodios(animes):
    """Devuelve [{sitio, epis, anime, rango}] para el anime en cada sitio (paralelo)."""
    def _uno(anime):
        sitio_mod = next(s for s in SITIOS if s.__name__.endswith("." + anime.sitio))
        try:
            return sitio_mod.episodios(anime)
        except Exception:
            return []

    envio = _paralelo_por_clave(animes, _uno)
    resultado = []
    for i, anime in enumerate(animes):
        epis = envio.get(i) or []
        if not epis:
            continue
        sitio_mod = next(s for s in SITIOS if s.__name__.endswith("." + anime.sitio))
        nums = [e.numero for e in epis]
        rango = f"{min(nums)}-{max(nums)}"
        resultado.append({"sitio": anime.sitio, "mod": sitio_mod, "anime": anime,
                          "epis": epis, "rango": rango})
    return resultado


def recoger_streams(cap, bloques, on_progreso=None, verbose=True):
    """Recolecta y resuelve los servidores de todos los sitios para ese capitulo.

    Cada sitio se procesa en paralelo (embeds + aplicar). `on_progreso(pct, texto)`
    se llama con el porcentaje correspondiente a la fase 0-60% del total.
    Si `verbose` es False, no imprime el listado de embeds (reintentos)."""
    from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

    total = len(bloques)

    def _worker(b):
        sitio = b["sitio"]
        lineas = []
        ep = next((e for e in b["epis"] if e.numero == cap), None)
        if ep is None and isinstance(cap, int) and cap >= 1:
            # Numeracion corrida del sitio (p. ej. jkanime usa 7050+ para el
            # cap 1): mapear por posicion si la lista es consecutiva.
            nums_ord = sorted(e.numero for e in b["epis"])
            if nums_ord and 0 < cap <= len(nums_ord):
                esperado = nums_ord[0] + (cap - 1)
                if nums_ord == list(range(nums_ord[0], nums_ord[0] + len(nums_ord))):
                    ep = next((e for e in b["epis"]
                               if e.numero == esperado), None)
        if not ep:
            rango = b['rango']
            if len(b["epis"]) == 1 and int(rango.split('-')[0]) > 400:
                lineas.append(f"  - {sitio}: solo disponible como Movie "
                              f"(rango {rango})")
            else:
                lineas.append(f"  - {sitio}: capitulo {cap} no disponible "
                              f"(rango {rango})")
            return lineas, [], []
        try:
            for _intento in range(2):
                embeds = b["mod"].embeds(ep)
                if embeds:
                    break
        except Exception as exc:
            lineas.append(f"  - {sitio}: error al leer embeds -> {exc}")
            return lineas, [], []
        if not embeds:
            lineas.append(f"  - {sitio}: sin servidores en el cap {cap}")
            return lineas, [], []
        lineas.append(f"  - {sitio} ({len(embeds)} embed(s)):")
        for e in embeds:
            lineas.append(f"      {e.host}: {e.url[:70]}")
        try:
            ss, ff = aplicar(embeds)
        except Exception as exc:
            lineas.append(f"  - {sitio}: error resolviendo -> {exc}")
            return lineas, [], []
        return lineas, ss, ff

    ex = ThreadPoolExecutor(max_workers=total)
    try:
        futuros = {ex.submit(_worker, b): b for b in bloques}
        pendientes = set(futuros)
        dsitio = {}
        completados = 0
        limite = 10.0
        t0 = time.perf_counter()
        while pendientes:
            restante = limite - (time.perf_counter() - t0)
            if restante <= 0:
                if dsitio:
                    break
                restante = 3.0
            done, pendientes = wait(pendientes, timeout=restante,
                                    return_when=FIRST_COMPLETED)
            for f in done:
                dsitio[futuros[f]["sitio"]] = f.result()
                completados += 1
                if on_progreso:
                    on_progreso(60 * completados / total,
                                f"Escaneando sitios del cap {cap} ...")
    finally:
        ex.shutdown(wait=False)

    streams = []
    fallidos = []
    for b in bloques:
        datos = dsitio.get(b["sitio"])
        if datos is None:
            if verbose:
                print(f"  - {b['sitio']}: no respondio a tiempo")
            continue
        lineas, ss, ff = datos
        if verbose:
            for ln in lineas:
                print(ln)
        for s in ss:
            s.host = f"{b['sitio']}/{s.host}"
            streams.append(s)
        for h, razon in ff:
            fallidos.append((f"{b['sitio']}/{h}", razon))
    return streams, fallidos


def barra(pct, texto=""):
    pct = max(0, min(100, int(pct)))
    ancho = 28
    lleno = int(ancho * pct / 100)
    bar = "#" * lleno + "-" * (ancho - lleno)
    print(f"\r  [{bar}] {pct:3d}% {sin_tildes(texto):<24}", end="", flush=True)


def _probe_con_barra(streams):
    """Mide latencia en paralelo y anima la barra (60-85%). Devuelve la lista
    de resultados OK ordenados por TTFB (vacia si ninguno responde)."""
    from concurrent.futures import ThreadPoolExecutor

    t0 = time.perf_counter()
    ex = ThreadPoolExecutor(max_workers=1)
    fut = ex.submit(probe.probar_rapido_lista, streams,
                    ventana=1.5, fallback=2.0)
    try:
        while not fut.done():
            t = time.perf_counter() - t0
            pct = 60 + 25 * min((t + 1.0) / 3.5, 1.0)
            barra(pct, "Midiendo latencia ...")
            time.sleep(0.1)
        return fut.result()
    finally:
        ex.shutdown(wait=False)


def reproducir_capitulo(grupo, bloques, cap, mayor, reintentar=True):
    barra(0, "Cargando ...")
    streams, fallidos = recoger_streams(cap, bloques, on_progreso=barra,
                                        verbose=False)
    if streams:
        barra(60, "Sitios escaneados")
        print()
    elif reintentar:
        # El primer escaneo no dio streams (alguna sitio tardo, o el cap no
        # estaba indexado aun): insistir una vez mas antes de rendirse.
        pintar("No se obtuvieron servidores en el primer escaneo. "
               "Reintentando ...", "amarillo")
        streams, fallidos = recoger_streams(cap, bloques,
                                            on_progreso=barra, verbose=False)
        if streams:
            barra(60, "Sitios escaneados")
            print()

    candidatos = _probe_con_barra(streams) if streams else []

    # Intento 1: los candidatos del probe (si hay) o, si el probe no
    # respondio (CDN lento/url expirada), los primeros streams directos.
    if candidatos:
        seleccion = candidatos
        etiqueta = None
    else:
        seleccion = [{"host": s.host, "url": s.url} for s in streams[:2]]
        etiqueta = ("Ningun stream respondio a la prueba de velocidad. "
                    "Probando con mpv directamente ...")

    if not seleccion:
        pintar("\nNo se obtuvieron servidores para este capitulo. Reintenta.", "rojo")
        return

    if etiqueta:
        pintar(f"\n{etiqueta}", "amarillo")
    if _reproducir_varios(streams, seleccion, grupo, cap):
        return

    # Si mpv fallo con los enlaces actuales, re-obtener frescos (los tokens
    # de los embeds expiran) y reintentar una vez mas.
    if not reintentar:
        pintar("\nTodos los servidores disponibles fallaron al abrir con "
               "mpv. Elige otra opcion.", "rojo")
        return
    pintar("Los enlaces podrian haber vencido. Re-obteniendo enlaces "
           "frescos ...", "amarillo")
    streams, fallidos = recoger_streams(cap, bloques,
                                        on_progreso=barra, verbose=False)
    if streams:
        barra(60, "Sitios re-escaneados")
        print()
    candidatos = _probe_con_barra(streams) if streams else []
    seleccion = candidatos or [
        {"host": s.host, "url": s.url} for s in streams[:2]
    ]
    if seleccion and _reproducir_varios(streams, seleccion, grupo, cap):
        return

    barra(85, "Ningun stream respondio a tiempo")
    print()
    pintar("\nNingun servidor respondio a prueba de velocidad. Reintenta.", "rojo")


def _reproducir_varios(streams, seleccion, grupo, cap):
    """Intenta reproducir con mpv los streams de `seleccion` (lista de dicts
    con host/url). Devuelve True si alguno reproduce."""
    for i, r in enumerate(seleccion):
        stream_mejor = next((s for s in streams
                             if s.host == r["host"] and s.url == r["url"]), None)
        if stream_mejor is None:
            continue
        barra(90, f"Lanzando mpv (intento {i + 1}/{len(seleccion)}) ...")
        print()
        pintar(
            f"\nAbriendo en mpv: {grupo.titulo} - Capitulo {cap} ...",
            "verde",
        )
        ok = reproductor.reproducir(
            stream_mejor.url,
            referer=stream_mejor.referer,
            titulo=f"{grupo.titulo} - Capitulo {cap}",
        )
        if ok:
            pintar(
                f"Reproduciendo {grupo.titulo} - Capitulo {cap}",
                "verde",
            )
            return True
        if i + 1 < len(seleccion):
            pintar(
                f"mpv fallo con ese servidor. Probando el siguiente "
                f"({i + 2}/{len(seleccion)}) ...",
                "amarillo",
            )
    return False


def menu_post_reproduccion(cap, mayor):
    print("\n--- Que sigue? ---")
    print("  [Enter]  Siguiente capitulo")
    print("  [a]      Capitulo anterior")
    print("  [n]      Elegir otro numero")
    print("  [b]      Buscar otro anime")
    print("  [q]      Salir")
    op = input("> ").strip().lower()
    if op in ("", "s", "siguiente"):
        return "siguiente", min(cap + 1, mayor)
    if op == "a":
        return "anterior", max(cap - 1, 1)
    if op == "n":
        sel = input(f"Nuevo capitulo? (1-{mayor}) > ").strip()
        if sel.isdigit() and 1 <= int(sel) <= mayor:
            return "cap", int(sel)
        print("Numero invalido.")
        return "menu", cap
    if op == "b":
        return "buscar", cap
    if op == "q":
        return "salir", cap
    return "menu", cap


def main():
    banner()
    errores_consecutivos = 0
    while True:
        try:
            grupo, animes = buscar()
            if grupo is None:
                # Si hay fallo de red o episodios no obtenibles, volver a
                # preguntar en lugar de cerrar el programa.
                continue
            if grupo == "salir":
                return
            # Flujo normal: los errores de una sola iteracion no cuentan
            # como racha.
            errores_consecutivos = 0
            bloques = []
            for _intento in range(3):
                if bloques:
                    break
                bloques = recoger_episodios(animes)
                if not bloques:
                    pintar("Fallo de conexion al obtener episodios. "
                           "Reintentando ...", "amarillo")
                    time.sleep(2)
            if not bloques:
                pintar("No se pudo obtener episodios de ningun sitio. "
                       "Vuelve a buscar.", "rojo")
                continue
            # El maximo utilizable: ignorar bloques con numeracion anomala
            # (p. ej. Movies en jkanime usan IDs 16xxx/58xxx, remasters, etc.).
            normales = [b for b in bloques
                        if b["epis"] and max(e.numero for e in b["epis"]) <= 400]
            elegibles = normales or bloques
            bloque_mayor = max(elegibles,
                               key=lambda b: max(e.numero for e in b["epis"]))
            mayor = max(e.numero for e in bloque_mayor["epis"])
            total_epis = len(bloque_mayor["epis"])
            print(f"\nTotal: {total_epis} episodios (rango 1-{mayor})")
            sel = input(f"Que capitulo reproducir? (1-{mayor}) > ").strip()
            if not sel.isdigit() or not (1 <= int(sel) <= mayor):
                pintar("Numero invalido.", "rojo")
                continue
            cap = int(sel)

            reproducir_capitulo(grupo, bloques, cap, mayor)

            # Tras cerrar mpv: menu para continuar sin salir del programa.
            while True:
                accion, cap = menu_post_reproduccion(cap, mayor)
                if accion == "salir":
                    return
                if accion == "buscar":
                    break
                if accion in ("siguiente", "anterior", "cap"):
                    reproducir_capitulo(grupo, bloques, cap, mayor)
                # "menu" (entrada invalida) vuelve a mostrar el menu
        except KeyboardInterrupt:
            break
        except Exception as exc:
            errores_consecutivos += 1
            pintar(f"Error inesperado: {exc}. Reintentando ...", "rojo")
            if errores_consecutivos >= 3:
                pintar("Demasiados errores seguidos. Saliendo.", "rojo")
                break
            time.sleep(0.5)
            continue


if __name__ == "__main__":
    main()
