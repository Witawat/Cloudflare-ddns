@echo off
chcp 65001 >nul
setlocal
title Cloudflare DDNS - Install

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

rem Use the built exe when available, otherwise fall back to Python
if exist "dist\cloudflare-ddns.exe" (
    set "DDNS_CMD=dist\cloudflare-ddns.exe"
) else (
    set "DDNS_CMD=python -m cloudflare_ddns.main"
)

if not exist "dist\cloudflare-ddns.exe" (
    echo %GRN%[1/3]%RST% Installing dependencies ^(pywin32^)...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo %RED%[x]%RST% pip install failed.
        pause
        exit /b 1
    )
)

echo %GRN%[2/3]%RST% Installing Windows Service...
%DDNS_CMD% install
if errorlevel 1 (
    echo %RED%[x]%RST% Failed to install service.
    pause
    exit /b 1
)

echo %GRN%[3/3]%RST% Starting service...
%DDNS_CMD% start

echo.
echo %GRN%[+]%RST% Done. Check services.msc, or run:
echo     %CYN%%DDNS_CMD% status%RST%
echo     %CYN%%DDNS_CMD% webui%RST%
pause
