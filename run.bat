@echo off
echo ================================
echo  Voicebot Dashboard - Start
echo ================================
echo.

cd /d "%~dp0"

if not exist "venv" (
    echo Tworzenie srodowiska wirtualnego...
    python -m venv venv
)

echo Aktywacja venv...
call venv\Scripts\activate

echo Instalacja zaleznosci...
pip install -r requirements.txt --quiet

echo.
echo ================================
echo  Uruchamianie serwera...
echo  http://localhost:8000
echo ================================
echo.

python app.py
