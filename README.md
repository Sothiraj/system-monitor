# system-monitor + portfolio

Two independent things live in this repo:

| Path | What it is |
|---|---|
| `app.py`, `utils/`, `templates/` | Flask live system-monitor dashboard (CPU / RAM / disk / network via `psutil` + Chart.js) |
| `portfolio/` | Static personal site — B.E. CSE graduate, cybersecurity & ethical hacking. No build step, no dependencies |

```bash
# dashboard
pip install -r requirements.txt
python3 app.py                      # → http://127.0.0.1:5000

# portfolio
python3 -m http.server 8000 --directory portfolio     # → http://localhost:8000
```

The portfolio is deliberately self-contained: nothing in `portfolio/` imports Flask and
nothing in the dashboard imports it, so you can delete or deploy either one alone.
`portfolio/README.md` covers personalising it, the generated CV PDF, and the security
headers it ships with.
