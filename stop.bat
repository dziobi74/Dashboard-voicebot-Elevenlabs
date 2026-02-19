@echo off
chcp 65001 >nul 2>&1
title Voicebot Dashboard - Stop
cd /d "%~dp0"

echo.
echo  Zatrzymywanie Voicebot Dashboard...
echo.

:: Znajdz i zabij procesy na porcie 8000
set FOUND=0
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000.*LISTENING" 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
    if not errorlevel 1 (
        echo  Zatrzymano proces PID %%a
        set FOUND=1
    )
)

if %FOUND%==0 (
    echo  Dashboard nie jest uruchomiony.
) else (
    echo.
    echo  [OK] Dashboard zatrzymany pomyslnie.
)

echo.
timeout /t 3 /nobreak >nul
