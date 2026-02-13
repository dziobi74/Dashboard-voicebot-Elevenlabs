# Voicebot Dashboard - ElevenLabs Analytics

**Version 0.8** | Author: Robert Malek

> [Dokumentacja po polsku / Polish documentation](README_PL.md)

A self-hosted web dashboard for monitoring and analyzing ElevenLabs Conversational AI voicebot performance. Connects to the ElevenLabs API, fetches conversation data, stores it locally, and presents actionable KPIs and charts.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![SQLite](https://img.shields.io/badge/Database-SQLite-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Features

- **Real-time KPI dashboard** with 12 key performance indicators
- **Interactive charts** (Chart.js) - conversion rates, daily trends, call duration, costs
- **Conversation table** with pagination, phone numbers, ratings, summaries
- **Phone number extraction** supporting Twilio and SIP Trunking providers
- **Automatic daily sync** - scheduler fetches data incrementally from 1st of current month
- **CSV export on demand** - export filtered data with one click
- **Monthly CSV archival** - automatic archival in first 5 days of each month
- **Local SQLite database** - all data stored locally, no external dependencies
- **Desktop shortcut** with custom icon (Windows)

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

## Requirements

- Python 3.10+
- ElevenLabs API key (with Conversational AI access)
- ElevenLabs Agent ID

## Quick Start

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

### Manual
```bash
cd voicebot-dashboard
python -m venv venv
source venv/bin/activate   # Linux/Mac
# venv\Scripts\activate    # Windows
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

### Phone Numbers
Phone numbers are extracted from conversation details. Supported providers:
- **Twilio**: `metadata.body.From` / `metadata.body.To`
- **SIP Trunking**: `metadata.body.from_number` / `metadata.body.to_number`

If phone numbers are missing, use the **"Pobierz numery tel."** button to re-fetch details.

## Project Structure

```
voicebot-dashboard/
  app.py                  - FastAPI server, scheduler, API endpoints
  database.py             - SQLAlchemy models (SQLite)
  elevenlabs_client.py    - ElevenLabs API client
  sync_service.py         - Sync logic, KPI computation, CSV archival
  create_icon.py          - Icon generator + desktop shortcut creator
  requirements.txt        - Python dependencies
  run.bat / run.sh        - Startup scripts
  voicebot.ico            - Application icon
  .gitignore              - Git exclusions (database, venv, CSV archives)
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
| GET | `/api/conversations?month=&page=&per_page=` | List conversations |
| GET | `/api/months` | Available month partitions |
| GET | `/api/export-csv?month=` | Export conversations to CSV |
| POST | `/api/archive?month=YYYY-MM` | Archive month to CSV |
| GET | `/api/archives` | List existing archives |
| GET | `/api/download-csv/{id}` | Download archived CSV |
| POST | `/api/refetch-details` | Re-fetch details for conversations missing phone numbers |
| GET | `/api/sync-logs` | Sync history |

## ElevenLabs API Integration

The application uses two ElevenLabs API endpoints:

1. **`GET /v1/convai/conversations`** - List conversations with pagination, filtering by agent_id and date range
2. **`GET /v1/convai/conversations/{conversation_id}`** - Conversation details including transcript, analysis, phone numbers, cost

## Security Notes

- API key is stored **only** in the local SQLite database (`voicebot.db`)
- The database file is excluded from git via `.gitignore`
- No data is sent to third parties - only direct communication with ElevenLabs API
- The application runs locally on `localhost:8000`

## Desktop Icon (Windows)

To create a desktop shortcut with custom icon:
```bash
python create_icon.py
```
This generates `voicebot.ico` and creates a shortcut on your Desktop.

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy, APScheduler, httpx
- **Database**: SQLite (local file)
- **Frontend**: Vanilla HTML/CSS/JS, Chart.js
- **API**: ElevenLabs Conversational AI REST API

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.8 | 2025-02 | Initial release - dashboard, KPIs, sync, CSV export, phone numbers, desktop icon |

## License

MIT License - free for personal and commercial use.
