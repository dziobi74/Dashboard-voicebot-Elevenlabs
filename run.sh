#!/bin/bash
echo "================================"
echo " Voicebot Dashboard - Start"
echo "================================"

cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "Tworzenie srodowiska wirtualnego..."
    python3 -m venv venv
fi

echo "Aktywacja venv..."
source venv/bin/activate

echo "Instalacja zaleznosci..."
pip install -r requirements.txt --quiet

echo ""
echo "================================"
echo " Uruchamianie serwera..."
echo " http://localhost:8000"
echo "================================"

python app.py
