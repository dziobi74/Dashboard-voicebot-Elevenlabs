# Voicebot Dashboard - Analityka ElevenLabs

**Wersja 0.8** | Autor: Robert Malek

> [English documentation](README.md)

Samodzielnie hostowany dashboard webowy do monitorowania i analizy wydajnosci voicebota ElevenLabs Conversational AI. Laczy sie z API ElevenLabs, pobiera dane konwersacji, przechowuje je lokalnie i prezentuje KPI oraz wykresy.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![SQLite](https://img.shields.io/badge/Baza_danych-SQLite-orange)
![License](https://img.shields.io/badge/Licencja-MIT-yellow)

---

## Funkcjonalnosci

- **Dashboard KPI w czasie rzeczywistym** z 12 kluczowymi wskaznikami
- **Interaktywne wykresy** (Chart.js) - konwersja, trendy dzienne, czas rozmow, koszty
- **Tabela konwersacji** z paginacja, numerami telefonow, ocenami, podsumowaniami
- **Ekstrakcja numerow telefonow** - obsluga providerow Twilio i SIP Trunking
- **Automatyczna codzienna synchronizacja** - scheduler pobiera dane przyrostowo od 1. dnia miesiaca
- **Eksport CSV na zadanie** - eksport filtrowanych danych jednym kliknieciem
- **Miesieczna archiwizacja CSV** - automatyczna archiwizacja w pierwszych 5 dniach kazdego miesiaca
- **Lokalna baza SQLite** - wszystkie dane przechowywane lokalnie
- **Skrot na pulpicie** z wlasna ikona (Windows)

## Wskazniki KPI

| # | KPI | Opis |
|---|-----|------|
| 1 | **Skutecznosc konwersji** | % rozmow zakonczonych sukcesem |
| 2 | **Polaczenia udane/nieudane** | Udane vs nieudane, przychodzace/wychodzace |
| 3 | **Scoring sesji** | Wyniki kryteriow oceny (pass/fail) |
| 4 | **Dlugosc rozmowy** | Srednia, min, max, krotkie (<30s) i dlugie (>5min) |
| 5 | **Transfery do agenta** | Liczba i % sesji przekazanych do konsultanta |
| 6 | **Dropout / porzucenia** | Rozmowy przerwane przed osiagnieciem celu |
| 7 | **Sr. wiadomosci bota** | Srednia liczba odpowiedzi bota na sesje |
| 8 | **Koszt sesji** | Sredni i calkowity koszt API na sesje |
| 9 | **Bledy techniczne** | Nieudane sesje i wskaznik bledow |
| 10 | **Srednia ocena** | Ocena uzytkownika w skali 1-5 |
| 11 | **Trendy dzienne** | Wykresy dziennego wolumenu, sukcesu, czasu, kosztow |
| 12 | **Kierunek polaczen** | Przychodzace vs wychodzace |

## Wymagania

- Python 3.10+
- Klucz API ElevenLabs (z dostepem do Conversational AI)
- ID agenta ElevenLabs

## Szybki start

### Windows
```bash
cd voicebot-dashboard
run.bat
```

### Linux / macOS
```bash
cd voicebot-dashboard
chmod +x run.sh
./run.sh
```

### Recznie
```bash
cd voicebot-dashboard
python -m venv venv
source venv/bin/activate   # Linux/Mac
# venv\Scripts\activate    # Windows
pip install -r requirements.txt
python app.py
```

Otworz **http://localhost:8000** w przegladarce.

## Konfiguracja

1. Otworz dashboard w przegladarce
2. Kliknij **"Ustawienia"** w prawym gornym rogu
3. Wpisz swoj **klucz API ElevenLabs** i **Agent ID**
4. Kliknij **"Zapisz"**

Klucz API jest przechowywany wylacznie w lokalnej bazie SQLite. Nie jest nigdzie wysylany poza API ElevenLabs.

## Uzytkowanie

### Pobieranie danych
1. Ustaw zakres dat (domyslnie: 1. dzien biezacego miesiaca - dzis)
2. Kliknij **"Pobierz dane"**
3. Poczekaj na zakonczenie synchronizacji, nastepnie kliknij **"Odswież KPI"**

### Automatyczna synchronizacja
- **Codziennie o 02:00 UTC** - przyrostowa synchronizacja od 1. dnia biezacego miesiaca
- **Dni 1-5 o 03:00 UTC** - automatyczna archiwizacja poprzedniego miesiaca do CSV

### Eksport CSV
- **Na zadanie**: Zakladka "Tabela konwersacji" -> przycisk **"Eksportuj CSV"**
- **Archiwizacja miesieczna**: Zakladka "Archiwa CSV" -> wybierz miesiac -> **"Archiwizuj wybrany miesiac"**

### Numery telefonow
Numery telefonow sa wyciagane ze szczegolów konwersacji. Obslugiwani providerzy:
- **Twilio**: `metadata.body.From` (klient) / `metadata.body.To` (voicebot)
- **SIP Trunking**: `metadata.body.from_number` (klient) / `metadata.body.to_number` (voicebot)

Jesli numery telefonow sa puste, uzyj przycisku **"Pobierz numery tel."** aby ponownie pobrac szczegoly.

## Struktura projektu

```
voicebot-dashboard/
  app.py                  - Serwer FastAPI, scheduler, endpointy API
  database.py             - Modele SQLAlchemy (SQLite)
  elevenlabs_client.py    - Klient API ElevenLabs
  sync_service.py         - Logika synchronizacji, obliczanie KPI, archiwizacja CSV
  create_icon.py          - Generator ikony + tworzenie skrotu na pulpicie
  requirements.txt        - Zaleznosci Python
  run.bat / run.sh        - Skrypty startowe
  voicebot.ico            - Ikona aplikacji
  .gitignore              - Wylaczenia git (baza, venv, archiwa CSV)
  templates/
    dashboard.html        - Jednostronicowy dashboard (HTML + JS + Chart.js)
  static/                 - Katalog plikow statycznych
  csv_archives/           - Miesieczne archiwa CSV (wykluczone z gita)
```

## Endpointy API

| Metoda | Endpoint | Opis |
|--------|----------|------|
| GET | `/` | Strona dashboardu |
| GET | `/api/settings` | Pobierz ustawienia (zamaskowany klucz API) |
| POST | `/api/settings` | Zapisz klucz API i Agent ID |
| POST | `/api/sync` | Uruchom reczna synchronizacje |
| GET | `/api/kpis?month=YYYY-MM` | Pobierz obliczone KPI |
| GET | `/api/conversations?month=&page=&per_page=` | Lista konwersacji |
| GET | `/api/months` | Dostepne partycje miesieczne |
| GET | `/api/export-csv?month=` | Eksport konwersacji do CSV |
| POST | `/api/archive?month=YYYY-MM` | Archiwizuj miesiac do CSV |
| GET | `/api/archives` | Lista istniejacych archiwow |
| GET | `/api/download-csv/{id}` | Pobierz zarchiwizowany CSV |
| POST | `/api/refetch-details` | Ponownie pobierz szczegoly dla konwersacji bez numerow telefonow |
| GET | `/api/sync-logs` | Historia synchronizacji |

## Integracja z API ElevenLabs

Aplikacja korzysta z dwoch endpointow API ElevenLabs:

1. **`GET /v1/convai/conversations`** - Lista konwersacji z paginacja, filtrowanie po agent_id i zakresie dat
2. **`GET /v1/convai/conversations/{conversation_id}`** - Szczegoly konwersacji: transkrypt, analiza, numery telefonow, koszt

## Bezpieczenstwo

- Klucz API przechowywany **wylacznie** w lokalnej bazie SQLite (`voicebot.db`)
- Plik bazy danych jest wykluczony z gita przez `.gitignore`
- Zadne dane nie sa wysylane do stron trzecich - tylko bezposrednia komunikacja z API ElevenLabs
- Aplikacja dziala lokalnie na `localhost:8000`

## Ikona na pulpicie (Windows)

Aby utworzyc skrot na pulpicie z wlasna ikona:
```bash
python create_icon.py
```
Tworzy plik `voicebot.ico` i skrot na pulpicie.

## Stack technologiczny

- **Backend**: Python, FastAPI, SQLAlchemy, APScheduler, httpx
- **Baza danych**: SQLite (plik lokalny)
- **Frontend**: HTML/CSS/JS, Chart.js
- **API**: ElevenLabs Conversational AI REST API

## Historia wersji

| Wersja | Data | Zmiany |
|--------|------|--------|
| 0.8 | 2025-02 | Pierwsze wydanie - dashboard, KPI, synchronizacja, eksport CSV, numery telefonow, ikona pulpitu |

## Licencja

Licencja MIT - wolne uzywanie do celow osobistych i komercyjnych.
