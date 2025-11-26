# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Colosseo Monitor is a Python application for monitoring ticket availability at the Colosseum in Rome. It provides both CLI tools and a Flask web interface for checking tour availability, tracking historical data, and exporting reports.

## Commands

### Install dependencies
```bash
pip install -r requirements.txt
```

### Run the web application
```bash
python app.py
```
The web server runs on http://localhost:5000

### CLI tools
```bash
# Query multiple tours (recommended for CLI usage)
python consultar_multiples_tours.py

# Full check with browser (obtains fresh cookies)
python colosseo_monitor.py

# Report only (uses existing cookies)
python colosseo_monitor.py --only-report

# Save report to file
python colosseo_monitor.py --only-report --save

# Custom dates and GUID
python colosseo_monitor.py --dates 2025-12-20 2025-12-21 --guid YOUR_GUID
```

## Architecture

### Core Modules

- **`colosseo_config.py`**: Central configuration (URLs, GUIDs, timeouts, HTTP headers). Uses `.env` for environment variables (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `FECHAS_INTERES`, `HEADLESS`).

- **`api_client.py`**: `ColosseoAPIClient` handles HTTP requests to the ticketing API. `AvailabilityChecker` normalizes and analyzes calendar data. Cookies are stored in `cookies_colosseo.json`.

- **`stealth_browser.py`**: `StealthBrowser` uses undetected-chromedriver to evade Octofence anti-bot detection. Includes JavaScript evasion scripts and human behavior simulation.

- **`report_generator.py`**: `ReportGenerator` formats availability data for console output and file reports.

### Web Application

- **`app.py`**: Flask app with REST API endpoints:
  - `POST /api/consultar`: Query tour availability (requires cookies in request body)
  - `POST /api/exportar-excel`: Export results to Excel
  - `POST /api/cargar-cookies-archivo`: Load cookies from file
  - `POST /api/guardar-cookies`: Save cookies to file
  - `POST /api/guardar-historico`: Save historical data to `historico_disponibilidad.xlsx`

- **`templates/index.html`**: Frontend UI

### Data Flow

1. Cookies are obtained via browser automation (stealth_browser) or manually pasted
2. API client uses cookies to fetch calendar data from `ticketing.colosseo.it/mtajax/calendars_month`
3. Data is normalized (timeslots aggregated by date) and analyzed for availability
4. Results displayed in console/web or exported to Excel

### Tour Configuration

Tours are configured with name and GUID in `app.py` and `consultar_multiples_tours.py`:
```python
TOURS = {
    "24h-grupos": {
        "nombre": "24h Colosseo, Foro Romano y Palatino - GRUPOS",
        "guid": "a9a4b0f8-bf3c-4f22-afcd-196a27be04b9"
    }
}
```

To get a new tour's GUID: Open Chrome DevTools Network tab, filter for `calendars_month`, click on calendar, and copy `guids[entranceEvent_guid][]` from the payload.

## Key Technical Details

- Windows-specific UTF-8 encoding fix applied at module start
- Cookies expire periodically and need renewal
- API returns timeslots that are aggregated by date for capacity totals
- Historical tracking stores snapshots in matrix format (rows=date+time, columns=timestamp)
