# animelite-cli

Buscador y reproductor de anime por consola. Consulta **tioanime, jkanime,
animeflv y monoschinos**, agrupa resultados, lista servidores con medicion de
latencia y reproduce con **mpv** (HLS/DASH/mp4) seleccionando el mejor enlace.

No requiere navegador: todo se resuelve con `urllib` estandar de Python.

## Requisitos

- **Windows** (probado en Windows 10/11, PowerShell y cmd).
- **Python 3.10 o superior** (probado en 3.10.11).
- **mpv** (reproductor) — *necesario solo para reproducir*.
- Conexion a internet (los sitios se consultan en vivo).
- Opcional: `colorama` (colores en consola). Se instala solo al usar el
  instalador.

> Sin mpv la aplicacion arranca, busca, lista episodios y servidores y mide
> latencia sin problema. Lo unico que no hace es reproducir: avisa con el
> comando para instalarlo y sigue navegable. No hay reproductor alternativo.

## Instalacion (rapida)

1. **Doble clic en `instalar.bat`** (o, desde una terminal, `python instalar.py`).

El instalador hace por ti:

1. Verifica Python 3.10+ (si falta, te indica instalarlo con `winget`).
2. Crea un entorno virtual `.venv` y instala las dependencias.
3. Detecta mpv (variable `MPV_PATH`, archivo de config, `PATH` o rutas
   habituales). **Si no lo encuentra, te pregunta si lo instala con winget**
   (`winget install --id shinchiro.mpv -e`).
4. Guarda la ruta de mpv en `%APPDATA%\animelite\config.json` y crea el
   lanzador `anime.bat`.

3. **Ejecuta `anime.bat`**.

### Instalacion manual (sin el instalador)

```bat
git clone https://github.com/DragonyteEvol/animelite-cli.git
cd animelite-cli
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python main.py
```

## El reproductor (mpv)

mpv se usa para abrir el stream final (m3u8/mp4). El programa lo busca en
este orden:

1. **`MPV_PATH`** (variable de entorno) — apunta directamente al exe, e.g.
   `set MPV_PATH=C:\ruta\a\mpv.exe`.
2. **`mpv_path`** del archivo de config `%APPDATA%\animelite\config.json`
   (lo escribe el instalador).
3. **`PATH`**: `mpv` en la ruta del sistema (instalacion con winget, zip
   manual descomprimido, etc.).
4. **Rutas habituales**: `C:\Program Files\mpv`, `%LOCALAPPDATA%\Programs\mpv`,
   `C:\Users\Public\Documents\mpv`, etc.

### Instalar mpv

Con winget:

```bat
winget install --id shinchiro.mpv -e
```

O manual: descarga el zip de mpv, descomprimelo en una carpeta (ej.
`C:\mpv`) y anade esa carpeta al PATH, o simplemente define `MPV_PATH`.

### Si no encuentras mpv

La app imprime:

```
[reproductor] No se encontro mpv. Instalalo con:
  winget install --id shinchiro.mpv -e
```

Tras instalarlo reinicia el programa (o vuelve a ejecutar `instalar.bat`
para que detecte y guarde la ruta).

## Uso

```
anime.bat
```

1. Escribe el nombre del anime y elige el resultado.
2. Elige capitulo.
3. La app escanea los 4 sitios, resuelve embeds y mide la latencia de cada
   servidor (los que responden se marcan "(respondio)") y abre el mejor en
   mpv.

Menu tras reproducir:

- `Enter` — siguiente capitulo
- `a` — capitulo anterior
- `n` — elegir otro numero
- `v` — **elegir otro servidor** (lista todos los obtenidos)
- `b` — buscar otro anime
- `q` — salir

Dentro de la lista de servidores: `[i]` numero del servidor para abrirlo,
`[r]` re-escanear servidores (los enlaces vencen), `[m]` volver al menu.

## Configuracion avanzada

- `MPV_PATH`: ruta al mpv.exe (prioridad maxima sobre la deteccion).
- `MPV_EXTRA`: argumentos extra para mpv, e.g. `MPV_EXTRA=--hwdec=no` o
  `--gpu-api=d3d11` (espacios por comillas).
- `%APPDATA%\animelite\config.json`: config generada por el instalador con la
  clave `mpv_path`.

## Problemas frecuentes

- **"No se encontro mpv"** — instala mpv (arriba) y lanza de nuevo el
  instalador o define `MPV_PATH`.
- **"Ningun servidor respondio a prueba de velocidad"** — los CDN de los
  embeds caen/vacien o la URL vencio. Vuelve a intentar o usa `[r]` para
  re-escanear.
- **Fallan todos los servidores de un capitulo** — suele ser temporal
  (Cloudflare/anti-bot del sitio o el CDN del host); intenta mas tarde.
- **Sin colores** — instala colorama (`pip install colorama`); es opcional.

## Estructura

```
main.py            CLI principal (busqueda, replica, menu)
sitios/            adaptadores por sitio (tioanime, jkanime, animeflv, monoschinos)
resolvers/         resolucion de embeds (voe, mp4upload, packer, okru, netu, maru, ...)
core/              cliente HTTP, modelo, sondeo de latencia
reproductor.py     deteccion y lanzamiento de mpv
config.py          config de usuario (%APPDATA%\animelite\config.json)
instalar.py/.bat   instalador (env .venv, deps, mpv)
anime.bat          lanzador
```