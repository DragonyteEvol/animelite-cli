import os
import os.path
import shlex
import shutil
import subprocess
import time

EXTRA_ARGS = [
    "--hwdec=auto",
    "--cache=yes",
    "--demuxer-readahead-secs=30",
    "--network-timeout=30",
    "--ytdl=no",
]


def _args_extra():
    """Args adicionales desde la variable de entorno MPV_EXTRA (para pruebas
    A/B, p. ej. `--hwdec=no` o `--gpu-api=d3d11`)."""
    extra = os.environ.get("MPV_EXTRA", "").strip()
    return shlex.split(extra) if extra else []


def _encontrar_mpv():
    for cand in (
        shutil.which("mpv"),
        r"C:\Users\Public\Documents\mpv\mpv.exe",
        r"mpv.com",
        r"C:\Program Files\mpv\mpv.exe",
        r"C:\Program Files (x86)\mpv\mpv.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\mpv\mpv.exe"),
    ):
        if cand and os.path.isfile(cand):
            return cand
    return None


def reproducir(url, referer="", titulo=""):
    mpv = _encontrar_mpv()
    if not mpv:
        print(
            "\n[reproductor] No se encontro mpv. Instalalo con:\n"
            '  winget install --id shinchiro.mpv -e\n'
            "y vuelve a ejecutar."
        )
        return False

    args = ([mpv, "--force-window=yes", "--keep-open=yes"]
            + EXTRA_ARGS + _args_extra())
    if referer:
        args.append(f"--http-header-fields=Referer: {referer}")
    if titulo:
        args.append(f"--title={titulo}")
    args.append(url)
    try:
        subprocess.run(args, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n[reproductor] mpv termino con error ({e.returncode})")
        return False


def reproducir_y_verificar(url, referer="", espera=9):
    """Lanza mpv, espera `espera` s y comprueba que el proceso sigue vivo
    (reproduciendo). Devuelve True si carga el stream. Mata el proceso al final."""
    mpv = _encontrar_mpv()
    if not mpv:
        return False
    args = ([mpv, "--force-window=yes", "--keep-open=yes",
             "--msg-level=all=error", "--no-osc"]
            + EXTRA_ARGS + _args_extra())
    if referer:
        args.append(f"--http-header-fields=Referer: {referer}")
    args.append(url)
    try:
        proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        return False
    time.sleep(espera)
    vivo = proc.poll() is None
    if vivo:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
    return vivo