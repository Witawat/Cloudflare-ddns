@echo off
chcp 65001 >nul
setlocal
title Cloudflare DDNS - Build + Install Service

set "ESC="
set "GRN=%ESC%[92m"
set "YEL=%ESC%[93m"
set "RED=%ESC%[91m"
set "CYN=%ESC%[96m"
set "RST=%ESC%[0m"

rem Relaunch with admin rights if needed
net session >nul 2>&1
if errorlevel 1 (
    echo %YEL%[*]%RST% Requesting administrator privileges...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"

rem Stop the service first (the exe is locked while the service is running)
sc query CloudflareDDNS >nul 2>&1
if errorlevel 1 (
    echo %YEL%[*]%RST% Service not installed yet.
) else (
    echo %YEL%[*]%RST% Stopping service...
    sc stop CloudflareDDNS >nul 2>&1
    taskkill /F /IM cloudflare-ddns.exe >nul 2>&1
)

echo %GRN%[1/3]%RST% Building exe ^(dist\cloudflare-ddns.exe^)...
python -m PyInstaller --noconfirm --clean --onefile --console ^
    --name cloudflare-ddns ^
    --icon assets\icon.ico ^
    --hidden-import servicemanager ^
    --hidden-import win32serviceutil ^
    --hidden-import win32service ^
    --add-data "cloudflare_ddns\webui.html;cloudflare_ddns" ^
    --add-data "cloudflare_ddns\webui.js;cloudflare_ddns" ^
    run.py
if errorlevel 1 (
    echo %RED%[x]%RST% Build failed.
    pause
    exit /b 1
)

echo %GRN%[2/3]%RST% Installing service...
dist\cloudflare-ddns.exe remove >nul 2>&1
dist\cloudflare-ddns.exe install
if errorlevel 1 (
    echo %RED%[x]%RST% Install failed.
    pause
    exit /b 1
)

echo %GRN%[3/3]%RST% Starting service...
dist\cloudflare-ddns.exe start

echo.
echo %GRN%[+]%RST% Done.
pause