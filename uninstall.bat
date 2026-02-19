@echo off
chcp 65001 >nul 2>&1
setlocal
title Voicebot Dashboard - Deinstalacja
cd /d "%~dp0"

echo.
echo  ========================================================
echo       VOICEBOT DASHBOARD - DEINSTALACJA
echo  ========================================================
echo.
echo  Ta operacja usunie:
echo    - Srodowisko wirtualne (venv)
echo    - Skrot z pulpitu
echo.
echo  NIE zostana usuniete:
echo    - Baza danych (voicebot.db) - Twoje dane
echo    - Archiwa CSV (csv_archives/)
echo    - Pliki zrodlowe aplikacji
echo.

set /p CONFIRM="Czy na pewno chcesz kontynuowac? (t/N): "
if /i not "%CONFIRM%"=="t" (
    echo  Anulowano.
    pause
    exit /b 0
)

echo.

:: Zatrzymaj serwer jesli dziala
echo  [1/3] Zatrzymywanie serwera...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000.*LISTENING" 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
)
echo        OK

:: Usun venv
echo  [2/3] Usuwanie srodowiska wirtualnego...
if exist "venv" (
    rmdir /s /q venv
    echo        venv usuniete
) else (
    echo        venv nie istnieje - pomijam
)

:: Usun skrot
echo  [3/3] Usuwanie skrotu z pulpitu...
if exist "%USERPROFILE%\Desktop\Voicebot Dashboard.lnk" (
    del "%USERPROFILE%\Desktop\Voicebot Dashboard.lnk"
    echo        Skrot usuniety
) else (
    echo        Skrot nie istnieje - pomijam
)

echo.
echo  ========================================================
echo.
echo   [OK] Deinstalacja zakonczona
echo.
echo   Baza danych i archiwa CSV zostaly zachowane.
echo   Aby je usunac, zrob to recznie.
echo.
echo   Aby zainstalowac ponownie: install.bat
echo.
echo  ========================================================
echo.
pause
