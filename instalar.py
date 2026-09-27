import os
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)

VENV = os.path.join(REPO, ".venv")
PY_VENV = os.path.join(VENV, "Scripts", "python.exe")
PIP_VENV = os.path.join(VENV, "Scripts", "pip.exe")

ANIME_BAT = os.path.join(REPO, "anime.bat")

WINGET_MPV = [
    "winget", "install", "--id", "shinchiro.mpv", "-e",
    "--accept-source-agreements", "--accept-package-agreements",
]


def _info(msg):
    print("  [..]", msg)


def _ok(msg):
    print("  [OK]", msg)


def _err(msg):
    print("  [XX]", msg)


def _python_ok():
    r = subprocess.run([sys.executable, "--version"],
                       capture_output=True, text=True)
    linea = (r.stdout or r.stderr).strip()
    _info(f"Python detectado: {linea}")
    try:
        num = linea.split(" ")[-1].split(".")
        return int(num[0]) >= 3 and int(num[1]) >= 10
    except Exception:
        return False


def _crear_venv():
    if os.path.isfile(PY_VENV):
        _ok(".venv ya existia")
        return True
    r = subprocess.run([sys.executable, "-m", "venv", VENV])
    if r.returncode != 0:
        _err("Fallo al crear .venv")
        return False
    _ok(".venv creado")
    return True


def _instalar_deps():
    r = subprocess.run(
        [PIP_VENV, "install", "-r", os.path.join(REPO, "requirements.txt")],
        stdout=subprocess.DEVNULL,
    )
    if r.returncode != 0:
        _err("Fallo al instalar dependencias (sin red?)")
        return False
    _ok("dependencias instaladas")
    return True


def _detectar_mpv():
    from reproductor import _encontrar_mpv
    return _encontrar_mpv()


def _instalar_mpv():
    from config import guardar
    if shutil.which("winget") is None:
        _err("No se encontro winget. Instala mpv manualmente (ver README).")
        return False
    _info("Instalando mpv con winget (puede tardar)...")
    try:
        subprocess.run(WINGET_MPV)
    except Exception as exc:
        _err(f"Error al instalar mpv: {exc}")
        return False
    return _detectar_mpv() is not None


def _crear_anime_bat():
    contenido = (
        "@echo off\r\n"
        "cd /d \"%~dp0\"\r\n"
        "if not exist \".venv\\Scripts\\python.exe\" (\r\n"
        "  echo Falta el entorno .venv. Ejecuta primero instalar.bat.\r\n"
        "  pause\r\n"
        "  exit /b 1\r\n"
        ")\r\n"
        "\".venv\\Scripts\\python.exe\" main.py %*\r\n"
        "if errorlevel 1 pause\r\n"
    )
    with open(ANIME_BAT, "w", encoding="utf-8") as f:
        f.write(contenido)
    _ok("lanzador anime.bat creado")


def main():
    print("=" * 56)
    print("  instalador de animelite-cli")
    print("=" * 56)

    if not _python_ok():
        _err("Se necesita Python 3.10 o superior. Instalalo con:")
        print("  winget install --id Python.Python.3.12 -e")
        print("  o desde https://www.python.org/downloads/ (marcar -Add to PATH-).")
        return 1

    if not _crear_venv():
        return 1

    if not _instalar_deps():
        return 1

    from config import guardar

    mpv = _detectar_mpv()
    if mpv:
        _ok(f"mpv encontrado: {mpv}")
        guardar(mpv_path=mpv)
    else:
        print()
        print("  No se encontro mpv (necesario para reproducir).")
        print("  La app funciona para buscar/listar servidores sin el, pero")
        print("  no podra reproducir.")
        op = input("  [s] Instalar mpv con winget / [n] Omitir (despues) > ").strip().lower()
        if op == "s":
            if _instalar_mpv():
                guardar(mpv_path=_detectar_mpv())
                _ok(f"mpv instalado: {_detectar_mpv()}")
            else:
                _err("mpv sigue sin detectarse tras la instalacion.")
                print("  Puedes configurarlo luego con la variable MPV_PATH")
                print("  o ejecutando de nuevo el instalador.")
        else:
            guardar()
            _info("Config creada sin ruta de mpv (la app lo avisara al reproducir).")

    _crear_anime_bat()

    print()
    print("  Instalacion lista. Para usar:")
    print("    anime.bat")
    print("  (la primera corrida puede tardar en cargar los sitios).")
    return 0


if __name__ == "__main__":
    sys.exit(main())