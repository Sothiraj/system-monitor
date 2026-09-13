# System Monitor

A small Flask dashboard that polls the host machine and charts live CPU, RAM,
disk and network usage.

## Layout

```
app.py                  Flask app: / (dashboard), /stats (JSON), /healthz
utils/monitor.py        psutil-based metric collection
templates/index.html    Bootstrap 5 + Chart.js dashboard
tests/test_app.py       pytest suite for the routes and payload
requirements.txt        runtime deps
requirements-dev.txt    dev deps (pytest)
```

## Run it

```bash
pip install -r requirements.txt
python app.py
```

Then open http://localhost:5000. The page polls `/stats` every 3 seconds.

### Configuration

| Variable      | Default | Purpose                                          |
|---------------|---------|--------------------------------------------------|
| `PORT`        | `5000`  | Port to listen on                                |
| `FLASK_DEBUG` | unset   | Set to `1` to enable the Werkzeug debugger       |

The server binds `0.0.0.0`, so it is reachable from containers, proxies and
port-forwarded previews — not just from the host itself.

> The Werkzeug debugger allows arbitrary code execution. It is off unless you
> explicitly set `FLASK_DEBUG=1`; never enable it on a public deployment.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

## `/stats` payload

```json
{
  "hostname": "...", "platform": "...", "uptime": 123.4,
  "cpu": 12.5, "cpu_count": 8,
  "ram": 7.4, "ram_used_gb": 1.2, "ram_total_gb": 16.0,
  "disk": 4.0, "disk_used_gb": 10.1, "disk_total_gb": 250.0,
  "net_sent": 0.22, "net_recv": 1.31, "timestamp": 1789000000.0
}
```

`cpu`, `ram` and `disk` are percentages; `net_sent` / `net_recv` are cumulative
megabytes since boot.

## Notes

- `cpu_percent(interval=None)` measures CPU busy time since the previous call,
  and psutil seeds that baseline at import. A reading of `0.0` on an idle box
  is a genuine measurement, not an error. `utils/monitor.py` still makes one
  call at import as a guard in case psutil's import-time seed fails.
- `disk_usage()` targets the `SystemDrive` root on Windows and `/` on POSIX, so
  the collector works on both.
