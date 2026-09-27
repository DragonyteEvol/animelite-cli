import json
import os

_RUTA = os.path.join(
    os.environ.get("APPDATA") or os.path.expanduser("~"),
    "animelite",
    "config.json",
)


def ruta_config() -> str:
    return _RUTA


def leer() -> dict:
    """Devuelve el dict de config (vacio si no existe o esta corrupto)."""
    try:
        with open(_RUTA, "r", encoding="utf-8") as f:
            datos = json.load(f)
        return datos if isinstance(datos, dict) else {}
    except Exception:
        return {}


def guardar(mpv_path: str = "") -> str:
    """Escribe (o crea) la config, actualizando `mpv_path`. Devuelve la ruta."""
    datos = leer()
    if mpv_path:
        datos["mpv_path"] = mpv_path
    os.makedirs(os.path.dirname(_RUTA), exist_ok=True)
    with open(_RUTA, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    return _RUTA