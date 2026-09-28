@echo off
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo No se encontro Python. Instalarlo con:
  echo   winget install --id Python.Python.3.12 -e
  pause
  exit /b 1
)
python "%~dp0instalar.py"
pause