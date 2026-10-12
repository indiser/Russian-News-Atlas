# 🇷🇺 Russia News Atlas

Real-time geospatial visualization of news across Russia using async RSS aggregation and PostgreSQL.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Overview

Aggregates news from 28 Russian/international RSS feeds, matches articles to cities using NLP with Cyrillic declension support, and renders an interactive Leaflet.js heatmap with color-coded intensity markers and auto-translation.

**Key Features:**
- Async RSS fetching with `aiohttp` (10s timeout per feed)
- PostgreSQL storage via SQLAlchemy (Neon-compatible)
- Cyrillic-aware geo-matching with stem + declension regex
- Person-name noise filtering (e.g. "Vladimir Putin" ≠ "Vladimir" city)
- Auto-translation of Russian headlines via translate.js
- Dynamic circle markers with hover popups

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure database
echo "DATABASE_URL=postgresql://user:pass@host/db" > .env

# Seed the database (first run)
python seed.py

# Run server
python app.py
```

Visit `http://localhost:5000`

---

## Architecture

```
┌─────────────────────────────────────────────┐
│  fetch_news.py (Async RSS Aggregator)       │
│  └─ 28 feeds → aiohttp → RAM dict          │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│  process_russia_data.py (Geo-Matcher)       │
│  ├─ Loads complete-russian-database-        │
│  │   cleaned.csv                            │
│  ├─ Cyrillic stem + declension regex        │
│  ├─ Person-name noise filter                │
│  └─ Pushes to PostgreSQL (heatmap_data)     │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│  app.py (Flask API)                         │
│  ├─ /api/news → JSON from DB                │
│  └─ / → index.html                         │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│  templates/index.html (Leaflet.js UI)       │
│  ├─ Circle markers + heat layer             │
│  └─ translate.js (RU → EN auto-translate)  │
└─────────────────────────────────────────────┘
```

---

## Project Structure

```
Russian News Heatmap/
├── app.py                               # Flask server
├── fetch_news.py                        # Async RSS scraper (28 feeds)
├── process_russia_data.py               # Geo-matching + DB writer
├── db.py                                # SQLAlchemy engine singleton
├── seed.py                              # One-shot DB seeder (CLI)
├── purge.py                             # Remove regions from CSV
├── unique_regions.py                    # Export regions.json from CSV
├── templates/
│   └── index.html                       # Leaflet.js map interface
├── static/
│   └── favicon.ico / *.png              # Favicons
├── complete-russian-database-cleaned.csv # City/region coordinates
├── feed_list.txt                        # One RSS URL per line
├── vercel.json                          # Vercel deployment config
├── .env                                 # DATABASE_URL config
└── requirements.txt
```

---

## How It Works

### 1. News Fetching (`fetch_news.py`)

Async fetches all feeds from `feed_list.txt` using `aiohttp`. Reads raw bytes so `feedparser` can auto-detect Windows-1251 encoding common in Russian feeds:

```python
async def get_all_news():
    # Returns: {"articles": [{"title": "...", "description": "..."}]}
```

**Sources:** Moscow Times, TASS, RT, RIA Novosti, Sputnik, Meduza, Lenta.ru, regional outlets, and more.

### 2. Geo-Processing (`process_russia_data.py`)

```python
def process_and_push_to_db(news_data):
    # 1. Load cities from complete-russian-database-cleaned.csv
    # 2. Strip person names (Vladimir Putin ≠ Vladimir city)
    # 3. Cyrillic stem match: "Москв" matches "Москва", "Москве", "Москвы"
    # 4. Aggregate counts + headlines per city
    # 5. Push to PostgreSQL (replaces table), skips push if 0 matches
```

**Output Schema:**
| Column | Type | Description |
|--------|------|-------------|
| Name | TEXT | City name (Latin) |
| Russianname | TEXT | City name (Cyrillic) |
| Federal subject | TEXT | Region/oblast |
| lat | FLOAT | Geo-coordinate |
| lon | FLOAT | Geo-coordinate |
| news_count | INT | Article mentions |
| headlines | TEXT | HTML-formatted list |
| last_updated | TEXT | UTC timestamp |

### 3. API Server (`app.py`)

- **`/`** → Renders `index.html`
- **`/api/news`** → Returns JSON from `heatmap_data` table

> No scheduler in `app.py` — use `seed.py` manually or set up a cron job / external trigger to refresh data.

### 4. Visualization (`index.html`)

- **Leaflet.js** map centered on Russia (61.5°N, 99.0°E)
- **Circle Markers:** Size = `news_count * 2` (capped at 30px), Color = intensity
- **Heat Layer:** Gradient overlay, capped at 12 to prevent Moscow from washing out other cities
- **Popups:** Hover to see headlines (city name + region + story count)
- **Auto-translate:** translate.js renders Russian headlines in English via `client.edge` (no API key)

**Color Scale:**
- 🟡 1 story: `#FEB24C`
- 🟠 2-3 stories: `#FD8D3C`
- 🔴 4-5 stories: `#E31A1C`
- 🔻 6-10 stories: `#BD0026`
- ⬛ 11+ stories: `#800026`

---

## Configuration

### Environment Variables

Create `.env` file:

```bash
DATABASE_URL=postgresql://user:password@host:5432/database
```

### RSS Feed Customization

Edit `feed_list.txt` — one URL per line:

```
https://tass.com/rss/v2.xml
https://your-feed.com/rss
```

### Location Data

`complete-russian-database-cleaned.csv` format:

```csv
Name,Russianname,Federal subject,lat,lon,Cities
Moscow,Москва,Moscow,55.7558,37.6173,...
```

---

## Utility Scripts

### `seed.py` — Initial DB Population

Runs the full fetch → process → push pipeline once from the CLI:

```bash
python seed.py
```

### `purge.py` — Remove Noisy Regions

Removes regions listed in `purge.txt` from the CSV to reduce false positives:

```bash
python purge.py
# Writes: cities-in-russia-cleaned-purged.csv
```

### `unique_regions.py` — Export Region Map

Exports a `regions.json` grouped by region from the cleaned CSV:

```bash
python unique_regions.py
```

---

## Dependencies

```
Flask              # Web framework
pandas             # CSV/data processing
feedparser         # RSS parsing (handles Windows-1251)
aiohttp            # Async HTTP client
sqlalchemy         # Database ORM
psycopg[binary]    # PostgreSQL driver
apscheduler        # Background jobs (available, not wired in app.py)
python-dotenv      # Environment config
gunicorn           # Production WSGI server
```

---

## Deployment

### Local Development

```bash
python seed.py   # populate DB first
python app.py    # runs on port 5000
```

### Production (Gunicorn)

```bash
gunicorn app:app --workers 4 --bind 0.0.0.0:8000
```

### Vercel

`vercel.json` is included — routes all traffic to `app.py` via `@vercel/python`.

### Database Setup

```sql
CREATE TABLE heatmap_data (
    "Name" TEXT,
    "Russianname" TEXT,
    "Federal subject" TEXT,
    lat FLOAT,
    lon FLOAT,
    news_count INT,
    headlines TEXT,
    last_updated TEXT
);
```

---

## Performance

- **RSS Fetch:** ~8-12s (parallel async, 28 feeds)
- **Geo-Processing:** <2s for 500+ articles across all cities
- **DB Write:** <1s (table replace)
- **API Response:** <200ms
- **Total Pipeline:** ~15s

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `DATABASE_URL missing` | Create `.env` with connection string |
| Empty map | Run `python seed.py` to populate DB |
| `0 city matches` | Check feed errors; person-noise filter may be over-stripping |
| Encoding errors in feeds | `fetch_news.py` reads raw bytes — feedparser handles Windows-1251 automatically |
| Port conflict | Change `app.run(port=5001)` in `app.py` |
| Vercel cold start | DB connection uses `pool_pre_ping=True` to handle stale connections |

---

## License

MIT License - See [LICENSE](LICENSE) for details.

---

## Credits

Built with Flask, Leaflet.js, OpenStreetMap, and PostgreSQL.

**Data Sources:** 28 Russian and international outlets including Moscow Times, TASS, RT, RIA Novosti, Sputnik, Meduza, Lenta.ru, and regional feeds.
