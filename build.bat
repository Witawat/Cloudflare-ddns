@echo off
chcp 65001 >nul
setlocal
title Cloudflare DDNS - Build EXE

set "ESC="
set "GRN=%ESC%[92m"
set "RED=%ESC%[91m"
set "CYN=%ESC%[96m"
set "RST=%ESC%[0m"

cd /d "%~dp0"

echo %GRN%[1/2]%RST% Checking dependencies...
python -m pip install pyinstaller -q
if errorlevel 1 (
    echo %RED%[x]%RST% pip install failed.
    pause
    exit /b 1
)

echo %GRN%[2/2]%RST% Building exe ^(dist\cloudflare-ddns.exe^)...
python -m PyInstaller --noconfirm --clean --onefile --console ^
    --name cloudflare-ddns ^
    --icon assets\icon.ico ^
    --hidden-import servicemanager ^
    --hidden-import win32serviceutil ^
    --hidden-import win32service ^
    run.py
if errorlevel 1 (
    echo %RED%[x]%RST% Build failed.
    pause
    exit /b 1
)

echo.
echo %GRN%[+]%RST% Done: %CYN%dist\cloudflare-ddns.exe%RST%
echo     Place the exe anywhere ^(config.ini goes next to it^)
echo     Test: %CYN%dist\cloudflare-ddns.exe --help%RST%
pause
