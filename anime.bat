@echo off
cd /d "C:\Users\Dragonyte\Downloads\Anime"
if not exist ".venv\Scripts\python.exe" (
  echo Falta el entorno .venv. Ejecutar primero instalar.bat.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" main.py %*
if errorlevel 1 pause
