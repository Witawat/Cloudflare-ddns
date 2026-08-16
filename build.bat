@echo off
chcp 65001 >nul
setlocal
title Cloudflare DDNS - Build EXE (build only)

set "ESC="
set "GRN=%ESC%[92m"
set "YEL=%ESC%[93m"
set "RED=%ESC%[91m"
set "CYN=%ESC%[96m"
set "RST=%ESC%[0m"

cd /d "%~dp0"

rem Admin only needed when the service is installed (stopping it requires admin).
rem On a dev machine without the service, build directly as normal user.
set "HAS_SVC=0"
sc query CloudflareDDNS >nul 2>&1
if errorlevel 1 (
    echo %YEL%[*]%RST% Service not installed - no admin needed.
) else (
    set "HAS_SVC=1"
    net session >nul 2>&1
    if errorlevel 1 (
        echo %YEL%[*]%RST% Requesting administrator privileges...
        powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
        exit /b
    )
)

rem Stop the service if running (the exe is locked while the service is running)
if "%HAS_SVC%"=="1" (
    echo %YEL%[*]%RST% Stopping service ^(build only - will NOT restart^)...
    sc stop CloudflareDDNS >nul 2>&1
    taskkill /F /IM cloudflare-ddns.exe >nul 2>&1
)

echo %GRN%[1/2]%RST% Building exe ^(dist\cloudflare-ddns.exe^)...
python -m PyInstaller --noconfirm --clean --onefile --console ^
    --name cloudflare-ddns ^
    --icon assets\icon.ico ^
    --hidden-import servicemanager ^
    --hidden-import win32serviceutil ^
    --hidden-import win32service ^
    --add-data "cloudflare_ddns\webui.html;cloudflare_ddns" ^
    --add-data "cloudflare_ddns\webui.js;cloudflare_ddns" ^
    --add-data "cloudflare_ddns\webui_login.html;cloudflare_ddns" ^
    run.py
if errorlevel 1 (
    echo %RED%[x]%RST% Build failed ^(exe locked? close webui/python first^).
    pause
    exit /b 1
)

echo.
echo %GRN%[+]%RST% Done ^(build only - service NOT started^).
echo     %CYN%dist\cloudflare-ddns.exe%RST%
echo     Run %CYN%build-install.bat%RST% to install/start the service,
echo     or %CYN%dist\cloudflare-ddns.exe start%RST% manually.
pause
