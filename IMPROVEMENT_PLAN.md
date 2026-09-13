# System Monitor — Comprehensive Improvement Plan (v1 → v2)

> **Project:** System Monitor Dashboard (real-time host monitoring) ·
> **Stack:** Python (Flask, psutil) + Bootstrap 5 + Chart.js ·
> **Baseline:** single-file Flask app (`app.py` + `utils/monitor.py` + `templates/index.html`),
> 2 routes (`/` + `/stats`), 8-metric JSON, 4 line charts polling every 3s.
> **Known pain points (confirmed by code audit):** hardcoded production fetch URL,
> fabricated chart data (`simulateFluctuation`), `cpu_percent` first-call-zero bug,
> Windows `disk_usage('/')` crash, cumulative (not rate) network counters, `debug=True`
> in code, unpinned deps, no tests/health/docs, committed `__pycache__`.

---

### 1. Comprehensive Improvement Audit

**Codebase & Architecture Upgrades**
- **App factory + central config** (`app.py::create_app`, `config.py`): env-driven
  Development/Production/Testing configs; no more `debug=True` hardcoded; `PORT`,
  thresholds, TTLs all overridable. Enables Flask CLI, gunicorn `app:app`, and tests.
- **Versioned REST API**: `/api/v1/{stats,history,system,stream}` with legacy shims
  (`/stats`, `/api/stats`) preserving the exact v1 key shape — zero breaking change.
- **Enriched domain model** (`utils/monitor.py`): per-core CPU, frequency, load avg,
  memory/swap in GB, all disk partitions, network **rates** (KB/s), process count,
  boot-time ISO, human uptime. Each collector isolated + exception-guarded.
- **Correctness fixes**: primed `cpu_percent`, cross-platform disk probing with
  partition fallback, thread-safe network delta tracker and TTL cache.
- **History seam** (`utils/history.py`): dependency-free thread-safe ring buffer;
  isolated module so Redis can replace it later without touching routes or UI.
- **Background sampler thread**: keeps `/history` warm even with zero viewers;
  daemonised, exception-proof, disabled under `TESTING`.
- **Real-time option**: SSE endpoint `/api/v1/stream` (push) alongside polling (pull).
- **Hygiene**: `.gitignore` + removed `__pycache__` from Git, pinned `requirements.txt`,
  structured logging, JSON error handlers, `Cache-Control: no-store` + `nosniff` headers,
  `Dockerfile`, `render.yaml` (health-checked deploys), pytest suite (17 tests).

**Feature Enhancements (high value, low risk)**
- **Truthful charts**: deleted `simulateFluctuation()`; all points are server samples
  with correct units (% vs KB/s) and sensible scales (0–100% fixed, throughput autoscaled).
- **KPI cards with context**: values + progress bars + sub-lines (cores/MHz, used/total GB,
  totals) instead of bare numbers.
- **Alert banner**: threshold-driven (`ALERT_*`), `aria-live` for screen readers.
- **Ops UX**: status dot (ok/warn/err/paused), last-updated time, 1s–10s interval picker,
  pause/resume, history preload (instant charts), auto-refresh on tab focus.
- **System details panel**: boot time, cores, load avg, freq, processes, Python version.
- **Dark/light theme** persisted in `localStorage`; responsive cards; accessible
  progressbars/labels; footer deep-links to raw JSON + probes.
- **Micro-interactions**: animated progress transitions, pulsing live dot, toast on
  disconnect, exponential-backoff retry without user action.

**Performance & Scalability**
- **TTL cache (1s)** on stats: concurrent pollers + sampler share one `psutil` snapshot
  instead of stampeding the collector.
- **Sampler cadence decoupled** from poll rate: cheap reads scale to many viewers.
- **Payload discipline**: history points are 6-key projections, not full payloads;
  `?limit=` capped at 500; charts capped at 60 points with `update('none')` (no animation jank).
- **Client efficiency**: `cache: 'no-store'` fetches, 8s abort timeout, polling paused
  when tab hidden, backoff slows the loop under failure instead of hammering.
- **Production serving**: gunicorn (`1 worker × 4 threads`) instead of the Flask dev
  server; documented path to Redis-backed history + Flask-Limiter + multi-worker scale-out.

### 2. Feature & Architecture Comparison Table

| Evaluation Metric/Feature | Existing Baseline Point | Newly Implemented Upgraded Point | Expected Impact & ROI |
|---|---|---|---|
| Data fidelity | `simulateFluctuation()` fabricates all chart points around 50 Hz | 100% real `psutil` samples; correct units/scales per metric | **Trust restored** — dashboard becomes decision-grade; eliminates misleading-ops risk |
| API URL handling | Hardcoded `https://system-monitor-6efz.onrender.com/stats` (breaks local/preview, CORS-prone) | Relative `/api/v1/stats` + `/history` preload; works on any host | **Zero-env-breakage**; preview/local/prod parity; fewer support incidents |
| CPU accuracy | `cpu_percent(interval=None)` first call always `0.0` | Primed at import + per-core/freq/load-avg detail | Correct first paint; richer capacity analysis at no extra cost |
| Disk portability | `disk_usage('/')` crashes on Windows | Multi-candidate probing + all-partitions listing | **Crash eliminated**; Windows/macOS/Linux support unlocks wider adoption |
| Network insight | Cumulative MB since boot (ever-growing, unactionable) | Per-second KB/s rates + totals + packets | Actionable throughput view; enables spike detection |
| Memory insight | Single % number | % + used/total/available/free GB + swap | Faster triage ("which GB, swap pressure?") |
| Uptime readability | Raw float seconds | `uptime_human` (`2d 3h 15m`) + boot ISO | Instant comprehension; fewer misread seconds |
| History | None (blank charts on load) | 180-pt ring buffer + sampler + `GET /history` + preload | Instant context on open; trend visibility without refresh wait |
| Live transport | 3s polling only | Polling (configurable) **+** SSE `/stream` push option | Lower latency available; polling fallback keeps compat |
| Alerting | None | Threshold banner (env-configurable) + aria-live | Proactive notice of CPU/RAM/disk pressure |
| UX controls | Fixed 3s, no pause | 1s–10s picker, pause/resume, theme toggle, status dot, toasts | Operator control; calmer incident UX; accessibility gains |
| Error handling | Unhandled exceptions → Flask HTML 500; silent JS failures | JSON API errors, route guards, JS timeout/backoff/retry | **MTTR down**; no silent dead dashboards |
| Health/ops probes | None | `/healthz`, `/readyz`, structured logs, security headers | K8s/Render-ready; deploy + monitoring integration |
| Config management | `debug=True` in code; no env support | `config.py` env-driven Dev/Prod/Test; `PORT/SECRET_KEY/TTL` vars | Safe prod deploys; 12-factor compliance |
| Dependencies | Unpinned `Flask, psutil` | Pinned `Flask 3.1.3 / psutil 7.2.2 / gunicorn / pytest` | Reproducible builds; no surprise breakage |
| Serving stack | Flask dev server (`app.run`) | Gunicorn `1×4` + Dockerfile + `render.yaml` | Threaded concurrency; health-checked deploys |
| Tests | 0 tests | 17 pytest tests (unit + HTTP incl. regression guards) | Regression safety; confident iteration |
| Docs | Empty README | README (quickstart/API/config/scaling) + this plan | Faster onboarding; fewer "how do I run it?" questions |
| Repo hygiene | `__pycache__` committed; no ignores | `.gitignore/.dockerignore`; pycache removed from Git | Cleaner diffs, smaller images, fewer accidents |
| Scalability seam | N/A | History isolated for Redis swap; documented limiter/auth/TLS next steps | Clear, low-cost path to multi-worker + public exposure |

### 3. Step-by-Step Implementation Blueprint

**Phase 1 — Preparation, Refactoring & Environment Configuration** ✅ *done*
1. Audit baseline: mapped routes, payload shape, and all 5 correctness bugs above.
2. Scaffold `config.py` (Dev/Prod/Test), `.gitignore`, `.dockerignore`; remove
   `__pycache__` from tracking.
3. Refactor `app.py` to `create_app()` factory; keep module-level `app` for gunicorn/CLI.
4. Rewrite `utils/monitor.py` with guarded collectors + priming + rate tracking + TTL cache.
5. Add `utils/history.py` ring buffer + sampler thread wiring.
6. Pin `requirements.txt`; add `Dockerfile`, `render.yaml`; venv-based local setup.

**Phase 2 — Core Feature Implementation (iterative)** ✅ *done*
1. API slice: `/api/v1/{stats,history,system,stream}` + legacy shims + probes + error handlers.
2. History slice: `record_from_stats` on every sample + sampler loop + `?limit=` cap.
3. UI slice A (structure): rewrite `index.html` — KPI cards, 4 charts, details panel,
   controls, alert banner, toast, footer API links; external CSS/JS.
4. UI slice B (behaviour): `dashboard.js` — relative fetch, history preload, backoff
   retry, pause/interval/theme, threshold alerts, status dot, visibility handling.
5. UI slice C (polish): `dashboard.css` themes, responsive grid, progress animations.
6. Verify each slice manually (`/`, `/api/v1/stats`, `/history`, `/stream`, `/healthz`)
   and via the pytest suite before proceeding.

**Phase 3 — Testing, QA & Performance Benchmarking** ✅ *done, monitor in prod*
1. **Automated**: `pytest -q` — 17 tests covering legacy shape, ranges, cross-platform
   disk, rate non-negativity, cache TTL, ring eviction, HTTP codes/headers, template
   regression guards (`onrender.com` / `simulateFluctuation` must be absent), SSE first chunk.
2. **Manual QA matrix**: cold load (charts preloaded?), pause/resume, interval switch,
   server-kill retry → toast → recover, light/dark persist, mobile 360px layout,
   Windows-path fallback review, `/stats` legacy key-diff.
3. **Benchmarks**: single `/stats` p50/p95 via `curl` loop; 4-thread gunicorn soak with
   5 concurrent pollers; confirm sampler keeps history growing with zero viewers.
4. **Prod checklist**: set `SECRET_KEY`, confirm `/healthz` green on Render, verify
   `FLASK_DEBUG` off, watch logs for sampler/collected warnings for 24h.

### 4. Risk Management & Preemptive Edge Cases

| # | Risk / Blockage | Likelihood × Impact | Mitigation (implemented + next) |
|---|---|---|---|
| 1 | **Stale/phantom breakage from the old hardcoded Render URL** — cached HTML/JS or bookmarks still hitting `...onrender.com/stats` after redeploy | Med × Med | ✅ Relative URLs everywhere + regression test asserting `onrender.com` absent; legacy `/stats` shim kept so old clients still resolve on the new host. Next: purge CDN/Render cache on release; announce new `/api/v1/*` paths. |
| 2 | **Per-process history diverges under multi-worker serving** — `gunicorn -w 4` would give each worker its own ring buffer | Med × Med (today: Low — default is `-w 1`) | ✅ Default `workers=1` in Dockerfile + `render.yaml`; seam isolated to `utils/history.py` with Redis-swap documented in README. Next: add `REDIS_URL` adapter + sticky-session or shared-store check in `/readyz` before scaling workers. |
| 3 | **Host-metric collection failures on constrained/odd platforms** (permissions on `/proc`, missing `cpu_freq`, no load-avg on Windows, Render free-tier throttling) | Med × High | ✅ Every collector is exception-guarded with sane fallbacks (`None`/`n/a`/empty list); sampler never dies; `/readyz` gates traffic; JS backoff + toast degrades gracefully. Next: add Flask-Limiter (60/min/IP), alert on sustained `/readyz` 503s, log collector latency to catch slow `psutil` calls. |

**Bonus edge cases already handled:** tab-hidden polling pause (battery/CPU),
8s fetch abort (no hung UI), SSE `GeneratorExit` clean close, `?limit=` clamping
(1–500), `interval=` clamping (0.5–30s), disk-partition permission skips, swap-missing
hosts, Chart.js CDN outage → page still renders cards/system info with charts empty
rather than a blank screen.
