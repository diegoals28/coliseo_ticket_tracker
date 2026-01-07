# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Colosseo Monitor is a Python application for monitoring ticket availability at the Colosseum in Rome. It provides CLI tools and a Flask web interface for checking tour availability, tracking historical data, and exporting reports. The system uses browser automation to bypass Octofence anti-bot protection and obtain session cookies.

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
```

## Architecture

### Data Flow

1. **Cookie Acquisition**: Cookies obtained via browser automation (`stealth_browser.py`, `cookie_fetcher.py`) or manually pasted. Must bypass Octofence anti-bot protection.
2. **API Requests**: `api_client.py` uses cookies to fetch calendar data from `ticketing.colosseo.it/mtajax/calendars_month`
3. **Data Processing**: Timeslots aggregated by date, analyzed for availability
4. **Storage**: Results stored locally or in Supabase cloud storage
5. **Output**: Console, web UI, or Excel exports

### Core Modules

- **`colosseo_config.py`**: Central configuration (URLs, GUIDs, timeouts, HTTP headers). Uses `.env` for environment variables.

- **`api_client.py`**: `ColosseoAPIClient` handles HTTP requests to the ticketing API. `AvailabilityChecker` normalizes and analyzes calendar data. Supports proxy rotation.

- **`stealth_browser.py`**: `StealthBrowser` uses undetected-chromedriver to evade Octofence anti-bot detection. Includes JavaScript evasion scripts and human behavior simulation.

- **`cookie_fetcher.py`**: Railway-specific cookie fetcher. Uses Chrome with proxy authentication extension. Fetches availability and updates historical Excel in Supabase.

- **`storage_client.py`**: Supabase Storage client. Handles cookies sync (`cookies/cookies_auto.json`), availability cache (`availability/availability_cache.json`), and historical Excel files (`historico/historico_disponibilidad.xlsx`).

- **`proxy_manager.py`**: `ProxyManager` with round-robin/random rotation, health checking, and automatic reactivation of failed proxies.

### Web Application (app.py)

Key API endpoints:
- `POST /api/consultar`: Query tour availability (requires cookies in body)
- `POST /api/exportar-excel`: Export results to Excel
- `GET /api/cookies/auto`: Get auto-refreshed cookies from Supabase
- `POST /api/cookies/sync`: Sync cookies to cloud
- `POST /api/guardar-historico`: Save historical data (local or Supabase)
- `GET /api/descargar-historico`: Download historical Excel with optional filters
- `GET /api/availability/cached`: Get cached availability from Supabase
- `POST /api/railway/trigger`: Trigger Railway job to refresh cookies

Proxy management endpoints:
- `GET /api/proxy/status`: Get proxy stats
- `POST /api/proxy/add`: Add proxies
- `POST /api/proxy/test`: Test all proxies

### Deployment Architecture

- **Vercel**: Hosts the Flask web app (`api/index.py` wrapper)
- **Railway**: Runs `cookie_fetcher.py` with Chrome to bypass Octofence and refresh cookies
- **Supabase**: Cloud storage for cookies, availability cache, and historical data
- **GitHub Actions**: `auto-cookies.yml` runs every 6 hours to refresh cookies

### Tour Configuration

Tours are configured with name and GUID:
```python
TOURS = {
    "24h-grupos": {
        "nombre": "24h Colosseo, Foro Romano y Palatino - GRUPOS",
        "guid": "a9a4b0f8-bf3c-4f22-afcd-196a27be04b9"
    },
    "arena": {
        "nombre": "Colosseo con ACCESO A LA ARENA",
        "guid": "8d1c991c-a15f-42bc-8cb5-bd738aa19c70"
    }
}
```

To get a new tour's GUID: Open Chrome DevTools Network tab, filter for `calendars_month`, click on calendar, and copy `guids[entranceEvent_guid][]` from the payload.

## Environment Variables

Required for cloud features:
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_KEY`: Supabase anon key

Proxy configuration (Webshare):
- `WEBSHARE_PROXY`: Full proxy URL (http://user:pass@host:port)
- Or: `WEBSHARE_HOST`, `WEBSHARE_PORT`, `WEBSHARE_USER`, `WEBSHARE_PASS`
- `WEBSHARE_API_KEY`: For automatic proxy list fetching

Railway deployment:
- `RAILWAY_API_TOKEN`: For triggering Railway jobs
- `RAILWAY_SERVICE_ID`: Service ID of cookie-fetcher

Optional:
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`: For notifications
- `FECHAS_INTERES`: Comma-separated dates to monitor
- `HEADLESS`: Run browser headless (true/false)

## Key Technical Details

- Windows-specific UTF-8 encoding fix applied at module start in Flask app
- Cookies expire periodically and need renewal (Octofence protection)
- API returns timeslots that are aggregated by date for capacity totals
- Historical tracking stores snapshots in matrix format (rows=date+time, columns=timestamp)
- UTC timestamps from API are converted to Rome timezone (CET/CEST) for display
- File operations can fail with "Device or resource busy" if Excel files are open in another program
