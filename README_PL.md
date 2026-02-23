# Voicebot Dashboard - Analityka ElevenLabs

**Wersja 1.0** | Autor: Robert Malek

> [English documentation](README.md)

Samodzielnie hostowany dashboard webowy do monitorowania i analizy wydajnosci voicebota ElevenLabs Conversational AI. Laczy sie z API ElevenLabs, pobiera dane konwersacji, przechowuje je lokalnie i prezentuje KPI oraz wykresy.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![SQLite](https://img.shields.io/badge/Baza_danych-SQLite-orange)
![License](https://img.shields.io/badge/Licencja-MIT-yellow)

---

## Szybka instalacja (Windows)

### Krok 0: Zainstaluj Python (wymagane)
Jesli nie masz jeszcze Pythona:
1. Wejdz na **https://www.python.org/downloads/**
2. Pobierz Python **3.10 lub nowszy** (zalecany: najnowszy 3.12 lub 3.13)
3. Uruchom instalator — **WAZNE: zaznacz "Add Python to PATH"** na dole okna instalatora!
4. Kliknij "Install Now"
5. Sprawdz: otworz **CMD** (Wiersz polecen) i wpisz: `python --version` — powinno pokazac `Python 3.1x.x`

> Jesli `python --version` pokazuje blad lub "nie rozpoznano polecenia", Python nie jest w PATH. Przeinstaluj z zaznaczonym "Add Python to PATH".

### Krok 1: Pobierz
```
git clone https://github.com/dziobi74/Dashboard-voicebot-Elevenlabs.git
```
lub pobierz ZIP z GitHub i rozpakuj.

### Krok 2: Zainstaluj
Kliknij dwukrotnie **`install.bat`** — to wszystko!

Instalator automatycznie:
- Sprawdzi czy Python 3.10+ jest zainstalowany
- Utworzy srodowisko wirtualne
- Zainstaluje wszystkie zaleznosci
- Utworzy skrot na pulpicie
- Zapyta czy uruchomic dashboard

### Krok 3: Uruchom
- Kliknij ikone **"Voicebot Dashboard"** na pulpicie
- lub uruchom **`start.bat`**
- Dashboard otworzy sie automatycznie w przegladarce: **http://localhost:8000**

### Krok 4: Skonfiguruj
Przy pierwszym uruchomieniu w zakladce **"Ustawienia"** podaj:
- **API Key ElevenLabs** — [pobierz tutaj](https://elevenlabs.io/app/settings/api-keys)
- **Agenci** — dodaj do 10 agentow (Agent ID + nazwa wyswietlana) z panelu ElevenLabs

---

## Pliki instalacyjne

| Plik | Opis |
|------|------|
| `install.bat` | Jednorazowa instalacja (venv, pakiety, skrot na pulpicie) |
| `start.bat` | Uruchomienie dashboardu + otwarcie przegladarki |
| `stop.bat` | Zatrzymanie serwera |
| `uninstall.bat` | Usiniecie srodowiska (zachowuje baze danych i archiwa) |
| `run.bat` | Alias do start.bat (kompatybilnosc wsteczna) |

---

## Funkcjonalnosci

- **Multi-agent** — monitorowanie do 10 agentow ElevenLabs jednoczesnie z selektorem na dashboardzie
- **Dashboard KPI w czasie rzeczywistym** z 12 kluczowymi wskaznikami
- **Interaktywne wykresy** (Chart.js) - konwersja, trendy dzienne, czas rozmow, koszty
- **Tabela konwersacji** z paginacja, numerami telefonow, ocenami, podsumowaniami
- **Kryteria oceny** w tabeli — kolorowe wartosci 2/1/0 (sukces/unknown/failure) dla kazdego kryterium
- **Kolumna zrodla** — kolorowe badge Twilio / SIP / Web dla identyfikacji kanalu
- **Ekstrakcja numerow telefonow** - obsluga providerow Twilio i SIP Trunking
- **Automatyczna codzienna synchronizacja** - scheduler pobiera dane dla wszystkich agentow
- **Eksport CSV na zadanie** — eksport z osobnymi kolumnami kryteriow (0/1/2)
- **Miesieczna archiwizacja CSV** - automatyczna archiwizacja w pierwszych 5 dniach kazdego miesiaca
- **Lokalna baza SQLite** - wszystkie dane przechowywane lokalnie
- **Jednorazowa instalacja** - install.bat i gotowe

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

## Wymagania systemowe

- **Windows 10/11** (dla install.bat) lub Linux/macOS (recznie)
- **Python 3.10+** — [pobierz](https://www.python.org/downloads/) (zaznacz "Add Python to PATH")
- **Klucz API ElevenLabs** z dostepem do Conversational AI
- **ID agentow ElevenLabs** — do 10 agentow

## Instalacja reczna (Linux / macOS)

```bash
cd voicebot-dashboard
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Otworz **http://localhost:8000** w przegladarce.

## Konfiguracja

1. Otworz dashboard w przegladarce
2. Kliknij **"Ustawienia"** w prawym gornym rogu
3. Wpisz swoj **klucz API ElevenLabs**
4. Dodaj **agentow** (Agent ID + nazwa wyswietlana) — do 10 agentow
5. Kliknij **"Zapisz"**

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
- Eksport zawiera osobne kolumny kryteriow z wartosciami: **2** (sukces), **1** (unknown), **0** (failure)

### Numery telefonow
Numery telefonow sa wyciagane ze szczegolów konwersacji. Obslugiwani providerzy:
- **Twilio**: `metadata.body.From` (klient) / `metadata.body.To` (voicebot)
- **SIP Trunking**: `metadata.body.from_number` (klient) / `metadata.body.to_number` (voicebot)
- **React SDK (Web)**: Konwersacje z widgetu webowego — brak numerow telefonow (to normalne)

## Struktura projektu

```
voicebot-dashboard/
  install.bat             - Jednorazowy instalator (Windows)
  start.bat               - Uruchomienie serwera + przegladarka
  stop.bat                - Zatrzymanie serwera
  uninstall.bat           - Deinstalacja (zachowuje dane)
  run.bat                 - Alias do start.bat
  app.py                  - Serwer FastAPI, scheduler, endpointy API
  database.py             - Modele SQLAlchemy (SQLite)
  elevenlabs_client.py    - Klient API ElevenLabs
  sync_service.py         - Logika synchronizacji, KPI, archiwizacja CSV
  create_icon.py          - Generator ikony + skrot na pulpicie
  requirements.txt        - Zaleznosci Python
  voicebot.ico            - Ikona aplikacji
  .gitignore              - Wylaczenia git
  templates/
    dashboard.html        - Jednostronicowy dashboard (HTML + JS + Chart.js)
  static/                 - Katalog plikow statycznych
  csv_archives/           - Miesieczne archiwa CSV (wykluczone z gita)
```

## Endpointy API

| Metoda | Endpoint | Opis |
|--------|----------|------|
| GET | `/` | Strona dashboardu |
| GET | `/api/settings` | Pobierz ustawienia (zamaskowany klucz API, lista agentow) |
| POST | `/api/settings` | Zapisz klucz API i agentow (do 10) |
| GET | `/api/agents` | Lista skonfigurowanych agentow |
| POST | `/api/sync` | Uruchom synchronizacje (wszystkich lub jednego agenta) |
| GET | `/api/kpis?agent_id=&month=` | Pobierz KPI dla agenta |
| GET | `/api/conversations?agent_id=&month=&page=` | Lista konwersacji dla agenta |
| GET | `/api/months?agent_id=` | Dostepne miesiace dla agenta |
| GET | `/api/export-csv?agent_id=&month=` | Eksport konwersacji do CSV |
| POST | `/api/archive?agent_id=&month=` | Archiwizuj miesiac do CSV |
| GET | `/api/archives` | Lista istniejacych archiwow |
| GET | `/api/download-csv/{id}` | Pobierz zarchiwizowany CSV |
| POST | `/api/refetch-details?agent_id=` | Ponownie pobierz szczegoly konwersacji |
| GET | `/api/sync-logs` | Historia synchronizacji (wszystkich agentow) |
| GET | `/api/debug-metadata?agent_id=` | Diagnostyka surowych metadanych JSON |

## Bezpieczenstwo

- Klucz API przechowywany **wylacznie** w lokalnej bazie SQLite (`voicebot.db`)
- Plik bazy danych jest wykluczony z gita przez `.gitignore`
- Zadne dane nie sa wysylane do stron trzecich - tylko bezposrednia komunikacja z API ElevenLabs
- Aplikacja dziala lokalnie na `localhost:8000`

## Stack technologiczny

- **Backend**: Python, FastAPI, SQLAlchemy, APScheduler, httpx
- **Baza danych**: SQLite (plik lokalny)
- **Frontend**: HTML/CSS/JS, Chart.js
- **API**: ElevenLabs Conversational AI REST API

## Historia wersji

| Wersja | Data | Zmiany |
|--------|------|--------|
| 1.0 | 2026-02 | Multi-agent (do 10 agentow), selektor agenta na dashboardzie, KPI per agent |
| 0.9 | 2026-02 | Profesjonalny instalator one-click, start/stop/uninstall, skrot na pulpicie |
| 0.8.2 | 2026-02 | Kryteria oceny w tabeli i CSV (2/1/0), kolumna zrodla (Twilio/SIP/Web) |
| 0.8.1 | 2026-02 | Diagnostyka metadanych, ulepszona ekstrakcja numerow telefonow |
| 0.8 | 2026-02 | Pierwsze wydanie - dashboard, KPI, synchronizacja, eksport CSV, numery telefonow, ikona pulpitu |

## Licencja

Licencja MIT - wolne uzywanie do celow osobistych i komercyjnych.
