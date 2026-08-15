@echo off
chcp 65001 >nul
setlocal
title Cloudflare DDNS - Build EXE

set "ESC="
set "GRN=%ESC%[92m"
set "YEL=%ESC%[93m"
set "RED=%ESC%[91m"
set "CYN=%ESC%[96m"
set "RST=%ESC%[0m"

rem Relaunch with admin rights if needed (taskkill service process requires admin)
net session >nul 2>&1
if errorlevel 1 (
    echo %YEL%[*]%RST% Requesting administrator privileges...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"

rem Stop the service first (the exe would be locked while the service is running)
set "WAS_RUNNING=0"
sc query CloudflareDDNS >nul 2>&1
if errorlevel 1 (
    echo %YEL%[0/2]%RST% Service not installed - skip stopping.
) else (
    echo %YEL%[0/2]%RST% Stopping service before build...
    if exist "dist\cloudflare-ddns.exe" (
        dist\cloudflare-ddns.exe stop >nul 2>&1
    )
    sc stop CloudflareDDNS >nul 2>&1
    taskkill /F /IM cloudflare-ddns.exe >nul 2>&1
    set "WAS_RUNNING=1"
)

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

rem Restart the service with the new exe if it was running before
if "%WAS_RUNNING%"=="1" (
    echo %GRN%[*]%RST% Restarting service with new exe...
    dist\cloudflare-ddns.exe start
)

echo.
echo %GRN%[+]%RST% Done: %CYN%dist\cloudflare-ddns.exe%RST%
echo     Place the exe anywhere ^(config.ini goes next to it^)
echo     Test: %CYN%dist\cloudflare-ddns.exe --help%RST%
pause
