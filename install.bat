@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion
title Voicebot Dashboard - Instalator v0.9

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║       VOICEBOT DASHBOARD - INSTALATOR v0.9          ║
echo  ║       ElevenLabs Conversational AI Analytics         ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: =========================================================
:: 1. Sprawdzenie Python 3.10+
:: =========================================================
echo [1/6] Sprawdzanie Pythona...

where python >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ╔══════════════════════════════════════════════════╗
    echo  ║  BŁĄD: Python nie jest zainstalowany!           ║
    echo  ║                                                  ║
    echo  ║  Pobierz z: https://www.python.org/downloads/   ║
    echo  ║  Zaznacz "Add Python to PATH" przy instalacji!  ║
    echo  ╚══════════════════════════════════════════════════╝
    echo.
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo        Python %PYVER% - OK

for /f "tokens=1,2 delims=." %%a in ("%PYVER%") do (
    set PYMAJOR=%%a
    set PYMINOR=%%b
)
if %PYMAJOR% LSS 3 (
    echo  BŁĄD: Wymagany Python 3.10+. Zainstalowany: %PYVER%
    pause
    exit /b 1
)
if %PYMAJOR%==3 if %PYMINOR% LSS 10 (
    echo  BŁĄD: Wymagany Python 3.10+. Zainstalowany: %PYVER%
    pause
    exit /b 1
)

:: =========================================================
:: 2. Tworzenie środowiska wirtualnego
:: =========================================================
echo.
echo [2/6] Tworzenie srodowiska wirtualnego...

if exist "venv" (
    echo        venv juz istnieje - pomijam
) else (
    python -m venv venv
    if errorlevel 1 (
        echo  BŁĄD: Nie udało się utworzyć venv
        pause
        exit /b 1
    )
    echo        venv utworzone - OK
)

:: =========================================================
:: 3. Instalacja zależności
:: =========================================================
echo.
echo [3/6] Instalacja zaleznosci (moze potrwac 1-2 min)...

call venv\Scripts\activate
pip install -r requirements.txt --quiet --disable-pip-version-check 2>nul
if errorlevel 1 (
    echo  BŁĄD: Instalacja zależności nie powiodła się
    pause
    exit /b 1
)
echo        Wszystkie pakiety zainstalowane - OK

:: =========================================================
:: 4. Konfiguracja .env (API key)
:: =========================================================
echo.
echo [4/6] Konfiguracja...

if not exist "csv_archives" (
    mkdir csv_archives
    echo        Katalog csv_archives utworzony
)

if not exist "voicebot.db" (
    echo.
    echo  ┌──────────────────────────────────────────────────┐
    echo  │  Pierwsza instalacja - konfiguracja API          │
    echo  │                                                   │
    echo  │  Klucz API ElevenLabs znajdziesz na:             │
    echo  │  https://elevenlabs.io/app/settings/api-keys     │
    echo  │                                                   │
    echo  │  Agent ID znajdziesz w ustawieniach agenta       │
    echo  │  w panelu ElevenLabs Conversational AI.          │
    echo  └──────────────────────────────────────────────────┘
    echo.
    echo  Te dane mozesz rowniez podac pozniej w dashboardzie
    echo  w zakladce Ustawienia.
    echo.
    echo        Baza danych zostanie utworzona przy pierwszym uruchomieniu - OK
) else (
    echo        Baza danych istnieje - OK
)

:: =========================================================
:: 5. Tworzenie skrótu na pulpicie
:: =========================================================
echo.
echo [5/6] Tworzenie skrotu na pulpicie...

set SCRIPT_DIR=%~dp0
set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%

> "%TEMP%\_voicebot_shortcut.vbs" (
    echo Set WshShell = WScript.CreateObject^("WScript.Shell"^)
    echo Set shortcut = WshShell.CreateShortcut^(WshShell.SpecialFolders^("Desktop"^) ^& "\Voicebot Dashboard.lnk"^)
    echo shortcut.TargetPath = "%SCRIPT_DIR%\start.bat"
    echo shortcut.WorkingDirectory = "%SCRIPT_DIR%"
    echo shortcut.WindowStyle = 7
    echo shortcut.Description = "Voicebot Dashboard - ElevenLabs Analytics"
    if exist "%SCRIPT_DIR%\voicebot.ico" (
        echo shortcut.IconLocation = "%SCRIPT_DIR%\voicebot.ico"
    )
    echo shortcut.Save
)
cscript //nologo "%TEMP%\_voicebot_shortcut.vbs" >nul 2>&1
del "%TEMP%\_voicebot_shortcut.vbs" >nul 2>&1

if exist "%USERPROFILE%\Desktop\Voicebot Dashboard.lnk" (
    echo        Skrot "Voicebot Dashboard" na pulpicie - OK
) else (
    echo        Nie udalo sie utworzyc skrotu (mozesz uzyc start.bat recznie^)
)

:: =========================================================
:: 6. Gotowe!
:: =========================================================
echo.
echo [6/6] Weryfikacja instalacji...

venv\Scripts\python.exe -c "import fastapi, uvicorn, sqlalchemy, httpx, apscheduler; print('        Wszystkie moduły dostępne - OK')"
if errorlevel 1 (
    echo  UWAGA: Niektore moduly mogą być niedostępne
)

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║                                                      ║
echo  ║   ✓ INSTALACJA ZAKOŃCZONA POMYŚLNIE!                ║
echo  ║                                                      ║
echo  ║   Uruchomienie:                                      ║
echo  ║     • Kliknij "Voicebot Dashboard" na pulpicie      ║
echo  ║     • lub uruchom start.bat                          ║
echo  ║                                                      ║
echo  ║   Dashboard otworzy się w przeglądarce:              ║
echo  ║     http://localhost:8000                            ║
echo  ║                                                      ║
echo  ║   Przy pierwszym uruchomieniu podaj:                 ║
echo  ║     • API Key ElevenLabs                             ║
echo  ║     • Agent ID                                       ║
echo  ║     w zakładce "Ustawienia" dashboardu.             ║
echo  ║                                                      ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

set /p RUNAPP="Czy uruchomic dashboard teraz? (T/n): "
if /i "%RUNAPP%"=="n" (
    echo.
    echo  Do zobaczenia! Uzyj start.bat aby uruchomic pozniej.
    pause
    exit /b 0
)

echo.
echo  Uruchamianie dashboardu...
call "%~dp0start.bat"
