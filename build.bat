@echo off
setlocal
title Cloudflare DDNS - Build EXE

cd /d "%~dp0"

echo [1/2] ตรวจ dependency...
python -m pip install pyinstaller -q
if errorlevel 1 (
    echo [x] pip install ล้มเหลว
    pause
    exit /b 1
)

echo [2/2] Build exe (dist\cloudflare-ddns.exe)...
python -m PyInstaller --noconfirm --clean --onefile --console ^
    --name cloudflare-ddns ^
    --icon assets\icon.ico ^
    --hidden-import servicemanager ^
    --hidden-import win32serviceutil ^
    --hidden-import win32service ^
    run.py
if errorlevel 1 (
    echo [x] Build ล้มเหลว
    pause
    exit /b 1
)

echo.
echo [+] เสร็จสิ้น: dist\cloudflare-ddns.exe
echo     วาง exe ที่ไหนก็ได้ (วาง config.ini ข้าง ๆ เพื่อตั้งค่า)
echo     เทสต์: dist\cloudflare-ddns.exe --help
pause
