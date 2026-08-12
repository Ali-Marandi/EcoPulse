@echo off
setlocal enabledelayedexpansion

REM EcoPulse Windows build — run from a 64-bit Windows terminal.
REM A signed production release should be built in a hardened CI runner.

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --name EcoPulse ^
  --collect-all pyqtgraph ^
  --hidden-import pyqtgraph ^
  main.py

if errorlevel 1 (
  echo Build failed.
  exit /b 1
)

echo.
echo Build complete: dist\EcoPulse.exe
endlocal
