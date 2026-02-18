# Voicebot Dashboard - ElevenLabs Analytics

**Version 0.9** | Author: Robert Malek

> [Dokumentacja po polsku / Polish documentation](README_PL.md)

A self-hosted web dashboard for monitoring and analyzing ElevenLabs Conversational AI voicebot performance. Connects to the ElevenLabs API, fetches conversation data, stores it locally, and presents actionable KPIs and charts.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![SQLite](https://img.shields.io/badge/Database-SQLite-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Quick Install (Windows)

### Step 1: Download
```
git clone https://github.com/dziobi74/Dashboard-voicebot-Elevenlabs.git
```
or download ZIP from GitHub and extract.

### Step 2: Install
Double-click **`install.bat`** — that's it!

The installer automatically:
- Checks Python 3.10+ is installed
- Creates a virtual environment
- Installs all dependencies
- Creates a desktop shortcut
- Asks to launch the dashboard

### Step 3: Run
- Click **"Voicebot Dashboard"** icon on your desktop
- or run **`start.bat`**
- Dashboard opens automatically in your browser: **http://localhost:8000**

### Step 4: Configure
On first launch, go to **"Ustawienia"** (Settings) tab and enter:
- **ElevenLabs API Key** — [get it here](https://elevenlabs.io/app/settings/api-keys)
- **Agent ID** — from your agent settings in ElevenLabs panel

---

## Installer Files

| File | Description |
|------|-------------|
| `install.bat` | One-time setup (venv, packages, desktop shortcut) |
| `start.bat` | Launch dashboard + open browser |
| `stop.bat` | Stop the server |
| `uninstall.bat` | Remove environment (preserves database and archives) |
| `run.bat` | Alias for start.bat (backward compatibility) |

---

## Features

- **Real-time KPI dashboard** with 12 key performance indicators
- **Interactive charts** (Chart.js) - conversion rates, daily trends, call duration, costs
- **Conversation table** with pagination, phone numbers, ratings, summaries
- **Evaluation criteria** in table — colored 2/1/0 values (success/unknown/failure) per criterion
- **Source column** — colored badges for Twilio / SIP / Web channel identification
- **Phone number extraction** supporting Twilio and SIP Trunking providers
- **Automatic daily sync** - scheduler fetches data incrementally from 1st of current month
- **CSV export on demand** — export with separate criteria columns (0/1/2)
- **Monthly CSV archival** - automatic archival in first 5 days of each month
- **Local SQLite database** - all data stored locally, no external dependencies
- **One-click installer** — install.bat and you're ready to go

## KPI Indicators

| # | KPI | Description |
|---|-----|-------------|
| 1 | **Conversion rate** | % of conversations completed successfully |
| 2 | **Call connection rate** | Successful vs failed connections, inbound/outbound split |
| 3 | **Session scoring** | Evaluation criteria pass/fail rates |
| 4 | **Call duration** | Average, min, max, short (<30s) and long (>5min) calls |
| 5 | **Agent transfers** | Count and % of sessions transferred to live agent |
| 6 | **Dropout rate** | Conversations abandoned before completion |
| 7 | **Avg bot messages** | Average number of bot responses per session |
| 8 | **Session cost** | Average and total API cost per session |
| 9 | **Technical errors** | Failed sessions and error rate |
| 10 | **Average rating** | User rating on 1-5 scale |
| 11 | **Daily trends** | Charts showing daily volume, success rate, duration, cost |
| 12 | **Call direction** | Inbound vs outbound breakdown |

## System Requirements

- **Windows 10/11** (for install.bat) or Linux/macOS (manual setup)
- **Python 3.10+** — [download](https://www.python.org/downloads/) (check "Add Python to PATH")
- **ElevenLabs API key** with Conversational AI access
- **ElevenLabs Agent ID**

## Manual Install (Linux / macOS)

```bash
cd voicebot-dashboard
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open **http://localhost:8000** in your browser.

## Configuration

1. Open the dashboard in your browser
2. Click **"Ustawienia"** (Settings) in the top-right corner
3. Enter your **ElevenLabs API Key** and **Agent ID**
4. Click **"Zapisz"** (Save)

The API key is stored in the local SQLite database only. It is never sent anywhere except to the ElevenLabs API.

## Usage

### Fetching Data
1. Set the date range (defaults to 1st of current month - today)
2. Click **"Pobierz dane"** (Fetch data)
3. Wait for sync to complete, then click **"Odswież KPI"** (Refresh KPIs)

### Automatic Sync
- **Daily at 02:00 UTC** - incremental sync from 1st of current month
- **Days 1-5 at 03:00 UTC** - automatic archival of previous month to CSV

### CSV Export
- **On-demand export**: Go to "Tabela konwersacji" tab, click **"Eksportuj CSV"**
- **Monthly archival**: Go to "Archiwa CSV" tab, select month, click **"Archiwizuj"**
- Export includes separate criteria columns with values: **2** (success), **1** (unknown), **0** (failure)

### Phone Numbers
Phone numbers are extracted from conversation details. Supported providers:
- **Twilio**: `metadata.body.From` / `metadata.body.To`
- **SIP Trunking**: `metadata.body.from_number` / `metadata.body.to_number`
- **React SDK (Web)**: Web widget conversations — no phone numbers (this is normal)

## Project Structure

```
voicebot-dashboard/
  install.bat             - One-click installer (Windows)
  start.bat               - Launch server + browser
  stop.bat                - Stop server
  uninstall.bat           - Uninstall (preserves data)
  run.bat                 - Alias for start.bat
  app.py                  - FastAPI server, scheduler, API endpoints
  database.py             - SQLAlchemy models (SQLite)
  elevenlabs_client.py    - ElevenLabs API client
  sync_service.py         - Sync logic, KPI computation, CSV archival
  create_icon.py          - Icon generator + desktop shortcut creator
  requirements.txt        - Python dependencies
  voicebot.ico            - Application icon
  .gitignore              - Git exclusions
  templates/
    dashboard.html        - Single-page dashboard (HTML + JS + Chart.js)
  static/                 - Static files directory
  csv_archives/           - Monthly CSV archives (gitignored)
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Dashboard page |
| GET | `/api/settings` | Get current settings (masked API key) |
| POST | `/api/settings` | Save API key and Agent ID |
| POST | `/api/sync` | Trigger manual data sync |
| GET | `/api/kpis?month=YYYY-MM` | Get computed KPIs |
| GET | `/api/conversations?month=&page=&per_page=` | List conversations with criteria |
| GET | `/api/months` | Available month partitions |
| GET | `/api/export-csv?month=` | Export conversations to CSV (with criteria columns) |
| POST | `/api/archive?month=YYYY-MM` | Archive month to CSV |
| GET | `/api/archives` | List existing archives |
| GET | `/api/download-csv/{id}` | Download archived CSV |
| POST | `/api/refetch-details` | Re-fetch conversation details |
| GET | `/api/sync-logs` | Sync history |
| GET | `/api/debug-metadata` | Raw metadata JSON diagnostics |

## Security Notes

- API key is stored **only** in the local SQLite database (`voicebot.db`)
- The database file is excluded from git via `.gitignore`
- No data is sent to third parties - only direct communication with ElevenLabs API
- The application runs locally on `localhost:8000`

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy, APScheduler, httpx
- **Database**: SQLite (local file)
- **Frontend**: Vanilla HTML/CSS/JS, Chart.js
- **API**: ElevenLabs Conversational AI REST API

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.9 | 2026-02 | Professional one-click installer, start/stop/uninstall, desktop shortcut |
| 0.8.2 | 2026-02 | Evaluation criteria in table and CSV (2/1/0), source column (Twilio/SIP/Web) |
| 0.8.1 | 2026-02 | Metadata diagnostics, enhanced phone number extraction |
| 0.8 | 2026-02 | Initial release - dashboard, KPIs, sync, CSV export, phone numbers, desktop icon |

## License

MIT License - free for personal and commercial use.
