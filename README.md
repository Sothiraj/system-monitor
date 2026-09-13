# 🖥️ System Monitor Dashboard v2

Real-time CPU, memory, disk, and network monitoring — a Flask + `psutil` backend
serving a live Chart.js dashboard. v2 is a ground-up hardening of the original
prototype: real data (no synthetic fluctuation), relative API URLs, cross-platform
metric collection, history buffer, alert thresholds, health probes, tests, and
production-ready deployment files.

## ✨ Features

- **Live KPI cards** — CPU, RAM, disk with progress bars; network up/down rates
- **4 real-data charts** — CPU / RAM / disk (%) + network throughput (KB/s, dual series)
- **History preload** — charts populate instantly from `GET /api/v1/history`
- **Alert banner** — configurable thresholds (`ALERT_CPU/RAM/DISK`)
- **Polling controls** — 1s/2s/5s/10s interval, pause/resume, tab-visibility aware
- **Resilience** — fetch timeout, exponential-backoff retry, error toasts, status dot
- **Dark/light theme** — persisted in `localStorage`
- **Enriched API** — per-core CPU, frequency, load avg, memory/swap GB, all partitions,
  network rates, process count, boot time, human uptime
- **Ops endpoints** — `/healthz`, `/readyz`, Server-Sent Events `/api/v1/stream`
- **Legacy compatible** — `GET /stats` keeps the exact v1 key shape

## 🚀 Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Development (debug + sampler on)
FLASK_ENV=development FLASK_DEBUG=1 python app.py
# → http://localhost:5000

# Production parity
gunicorn --bind 0.0.0.0:5000 --workers 1 --threads 4 app:app
```

Or with Docker:

```bash
docker build -t system-monitor .
docker run -p 5000:5000 system-monitor
```

Run tests:

```bash
pytest -q
```

## 🔌 API reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Dashboard UI |
| `GET` | `/healthz` | Liveness `{status, service, version}` |
| `GET` | `/readyz` | Readiness (psutil must respond) |
| `GET` | `/stats`, `/api/stats` | **Legacy** `{hostname, platform, uptime, cpu, ram, disk, net_sent, net_recv}` |
| `GET` | `/api/v1/stats` | Full payload (superset + `cpu_detail/memory/disks/network/system`) |
| `GET` | `/api/v1/history?limit=120` | Ring-buffer samples `{points[], count}` |
| `POST` | `/api/v1/history/clear` | Clear buffer + stats cache |
| `GET` | `/api/v1/system` | Host info only |
| `GET` | `/api/v1/stream?interval=2` | SSE live feed (`data: {...}` per interval) |

Example:

```bash
curl -s localhost:5000/api/v1/stats | python -m json.tool | head -30
curl -s localhost:5000/api/v1/history?limit=3 | python -m json.tool
curl -N localhost:5000/api/v1/stream?interval=1  # Ctrl-C to stop
```

## ⚙️ Configuration (env vars)

| Variable | Default | Purpose |
|----------|---------|---------|
| `FLASK_ENV` | `production` | `development` / `production` / `testing` |
| `FLASK_DEBUG` | _(off)_ | `1` enables debugger (never in prod) |
| `PORT` | `5000` | HTTP port |
| `SECRET_KEY` | dev default | Flask secret — **set in prod** |
| `STATS_CACHE_TTL` | `1.0` | Seconds a stats payload stays cached |
| `ENABLE_SAMPLER` | `1` | Background thread warming `/history` |
| `SAMPLER_INTERVAL` | `2.0` | Sampler cadence (seconds) |
| `HISTORY_MAXLEN` | `180` | Ring-buffer capacity |
| `ALERT_CPU/ALERT_RAM/ALERT_DISK` | `85/90/90` | Alert banner thresholds |

## 🏗️ Project structure

```
app.py                  Flask factory, routes, SSE stream, sampler, error handlers
config.py               Env-driven Development/Production/Testing configs
utils/monitor.py        psutil collection: cpu/mem/disk/net/system (+ legacy shim)
utils/history.py        Thread-safe in-memory ring buffer
templates/index.html    Dashboard markup (no hardcoded URLs, no fake data)
static/css/dashboard.css  Dark/light theme, cards, status dot
static/js/dashboard.js    Polling client: backoff, preload, alerts, charts
tests/                  pytest suite (monitor unit + HTTP integration)
Dockerfile / render.yaml  Prod deploy (gunicorn, /healthz checks)
```

## 📈 What changed from v1 → v2

See **[IMPROVEMENT_PLAN.md](IMPROVEMENT_PLAN.md)** for the full audit, side-by-side
comparison table, implementation blueprint, and risk register.

Highlights: fixed `cpu_percent` first-call-zero bug, fixed Windows `disk_usage('/')`
crash, replaced cumulative network bytes with per-second rates, removed the
`simulateFluctuation()` data fabrication and the hardcoded `onrender.com` fetch URL,
added caching + sampler + history + SSE + tests + Docker + pinned deps.

## ⚠️ Scaling notes

- **History is per-process memory.** With `gunicorn -w 1` (default here) this is
  correct; if you scale to multiple workers, promote `HistoryStore` to Redis
  (the seam is isolated to `utils/history.py`).
- Metrics endpoints send `Cache-Control: no-store` and permissive CORS (`*`) since
  they are read-only host stats. If you add authenticated or multi-tenant views,
  tighten CORS and put auth (e.g. Flask-Login or a reverse-proxy basic-auth) in front.
- For public internet exposure, run behind TLS (Render/containers handle this) and
  consider rate-limiting `/api/*` (e.g. Flask-Limiter, 60 req/min/IP).
