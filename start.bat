@echo off
chcp 65001 >nul 2>&1
title Voicebot Dashboard - Serwer
cd /d "%~dp0"

echo.
echo  ========================================================
echo       VOICEBOT DASHBOARD
echo       ElevenLabs Conversational AI Analytics
echo  ========================================================
echo.

:: Sprawdz czy venv istnieje
if not exist "venv\Scripts\python.exe" (
    echo  BLAD: Srodowisko nie jest zainstalowane!
    echo  Uruchom najpierw: install.bat
    echo.
    pause
    exit /b 1
)

:: Sprawdz czy port 8000 jest wolny
netstat -ano | findstr ":8000.*LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo  Dashboard juz dziala na http://localhost:8000
    echo  Otwieram przegladarke...
    timeout /t 1 /nobreak >nul
    start "" http://localhost:8000
    echo.
    echo  Aby zatrzymac serwer uzyj: stop.bat
    echo.
    pause
    exit /b 0
)

echo  Uruchamianie serwera...
echo  Port: 8000
echo.

:: Otworz przegladarke po 3 sekundach (w tle)
start "" /b cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8000"

:: Info
echo  Dashboard dostepny pod adresem:
echo.
echo    http://localhost:8000
echo.
echo  ---------------------------------------------------------
echo   Aby zatrzymac: zamknij to okno lub uzyj stop.bat
echo  ---------------------------------------------------------
echo.

:: Uruchom serwer (blokuje to okno)
venv\Scripts\python.exe -m uvicorn app:app --host 0.0.0.0 --port 8000

:: Gdy serwer sie zakonczy
echo.
echo  Serwer zatrzymany.
echo.
pause
