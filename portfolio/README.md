# Portfolio — YOUR NAME · Cybersecurity Analyst & Ethical Hacker

A hand-written, dependency-free personal site: **one HTML file, one stylesheet, two scripts**.
No framework, no bundler, no tracker, no build step — open `index.html` and it works.

```
portfolio/
├── index.html              every section, semantic + accessible, readable with JS off
├── css/style.css           design tokens, dark + light themes, print stylesheet
├── js/theme.js             pre-paint theme pick (kept external so CSP needs no unsafe-inline)
├── js/main.js              all behaviour + the `PROFILE` config block (see below)
├── assets/profile.jpg      your photo (1254×1254, AI-generated placeholder — see "Photo")
├── assets/favicon.svg      shield/prompt mark
├── assets/YOUR-NAME-CV.pdf generated one-page résumé, matches the site
├── tools/make-cv.py        regenerates that PDF  →  python3 tools/make-cv.py
├── _headers                Netlify/Cloudflare response headers (CSP, HSTS, …)
└── README.md               this file
```

---

## 1. Run it

```bash
cd portfolio
python3 tools/serve.py               # → http://localhost:8000
```

`tools/serve.py` is just `http.server` plus no-cache headers (so a refresh always shows
your latest edit) and correct MIME types. `python3 -m http.server 8000` works too.

Any static server works (`npx serve`, `caddy file-server`, nginx). Double-clicking
`index.html` also works; the only thing that needs HTTP is the font request.

## 2. Make it yours

Most values live in **one object** at the top of `js/main.js` — it drives the mailto
composer, the footer links and the résumé path:

```js
const PROFILE = {
  name: 'YOUR NAME', email: 'you@yourhandle.dev', phone: '+91 90000 00000',
  location: 'Salem, Tamil Nadu, India', cvPath: 'assets/YOUR-NAME-CV.pdf',
  roles: ['Cybersecurity Analyst & Ethical Hacker', /* typed in the hero */]
};
```

The rest are literal placeholders in `index.html`. Replace all of them in one pass
(**run from inside `portfolio/`**; order matters — the email is replaced before the
handle because both contain `yourhandle`):

```bash
read -rp "Full name: " NAME
read -rp "Handle (X / blog): " HANDLE
read -rp "Email: " EMAIL
read -rp "GitHub / LinkedIn / HTB slug: " SLUG
read -rp "Monogram, 2 letters (e.g. SN): " MONO

for f in index.html js/main.js js/theme.js css/style.css README.md; do
  [ -f "$f" ] || continue
  sed -i \
    -e "s|YOUR NAME|$NAME|g" \
    -e "s|you@yourhandle\.dev|$EMAIL|g" \
    -e "s|yourhandle\.dev|$HANDLE.dev|g" \
    -e "s|@yourhandle\b|@$HANDLE|g" \
    -e "s|yourusername|$SLUG|g" \
    -e "s|yourhandle|$HANDLE|g" \
    -e "s|>YN<|>$MONO<|g" \
    -e "s|\"YN\"|\"$MONO\"|g" \
    "$f"
done
grep -rn "YOUR NAME\|yourusername\|yourhandle" . --include="*.html" --include="*.js" --include="*.css"   # must print nothing
```

Still hand-edit, because only you know these:

| Placeholder | Where |
|---|---|
| `[College Name]` | Education, JSON-LD |
| `[Client Name] Cyber Defense` | Experience |
| `[VP Name]`, `[Shift Manager]`, `[Faculty Name]` | References (or delete the whole `#references` section) |
| `CVE-2025-XXXXX` | Credentials — never publish an unassigned CVE |
| `ID eJPT-XXXXXXX`, PGP / Signal lines | Credentials, contact |
| every number in `data-count="…"` | hero + evidence stats |
| skill percentages | `style="--lvl:92%"` on each `.skill` |

To drop a section: delete the `<section id="x">…</section>` **and** its link in
`.primary-nav` (the ⌘K palette indexes sections automatically).

## 3. Photo

`assets/profile.jpg` is **AI-generated as a stand-in** — do not ship it as your real
face on a site recruiters will read. Replace it with a plain file copy:

```bash
cp ~/Pictures/headshot.jpg assets/profile.jpg
```

Recipe that matches the layout: square crop, ~1000–1250 px, head at 25–30 % from the
top, dark or neutral background, business-casual, **under 200 KB**.
The frame is `aspect-ratio: 1 / .82` with `object-position: 50% 22%`, so a centred
headshot lands without cropping your chin. Compress with
`cwebp -q 82 -m 6` or `jpegoptim -m --max=82`. Alt text lives on the `<img>` — update it.

## 4. Résumé PDF

The **Résumé** button points at `assets/YOUR-NAME-CV.pdf`, a real one-page PDF generated
from `tools/make-cv.py` (content is a dict at the top of the file):

```bash
pip install fpdf2
python3 tools/make-cv.py            # → assets/YOUR-NAME-CV.pdf
```

Only core PDF fonts are used, so the text stays selectable and parses cleanly in ATS
pipelines. Or delete the button and link your own PDF/Google Doc instead. `@media print`
in `style.css` already turns the page itself into a readable printout — Cmd/Ctrl+P on the
site is a legitimate fallback.

## 5. Deploy

| Host | How |
|---|---|
| **GitHub Pages** | push `portfolio/` to a branch and set it as the source (`.nojekyll` already ships, so `_headers` and dot-files survive the Jekyll pass); point a custom domain via CNAME |
| **Netlify / Cloudflare Pages** | publish directory = `portfolio`, no build command — `_headers` is picked up automatically |
| **Vercel** | `cd portfolio && npx vercel` (move `_headers` into `vercel.json`'s `headers` array) |
| **This repo's Flask app** | add a route and it serves from the same box as the system monitor |

```python
# app.py — serve the portfolio next to the dashboard
@app.route('/portfolio/')
def portfolio():
    return send_from_directory('portfolio', 'index.html')
```
(plus `send_from_directory` to the `flask` import, or use `StaticFiles`/whitenoise.)

## 6. Headers actually shipped

`_headers` gives you an A+ on [securityheaders.com](https://securityheaders.com/) with:

```
Content-Security-Policy: default-src 'self'; …; script-src 'self';
  frame-ancestors 'none'; base-uri 'self'; object-src 'none'; upgrade-insecure-requests
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
Permissions-Policy: camera=(), microphone=(), geolocation=(), interest-cohort=()
Referrer-Policy: strict-origin-when-cross-origin · X-Content-Type-Options: nosniff
```

`script-src 'self'` holds because nothing executes inline — which is exactly why
`theme.js` is a file and not a `<script>` block. `style-src 'unsafe-inline'` stays
on purpose: the skill bars use `style="--lvl:…"` so they still render with JS off.
Self-host Inter + JetBrains Mono if you want to drop the `fonts.googleapis.com`
exception entirely.

## 7. What's in the box

- **11 sections** — hero, about, arsenal (skills + MITRE ATT&CK coverage), services,
  projects, timeline, credentials/CVEs/awards, writeups, references, contact, footer
- **Dark ↔ light** theme, persisted, follows OS until you toggle; no flash on load
- **⌘K / Ctrl-K palette** — jumps to every section *and* runs actions (copy email,
  print CV, switch theme)
- Terminal boot sequence, matrix rain (dark only, ~18 fps, pauses when hidden),
  portrait tilt, count-up stats, project filtering, scrollspy, scroll progress
- Contact form that **never talks to a server**: validated locally, then handed to the
  visitor's mail client pre-filled
- Accessibility: skip link, one `h1`, landmarks, labelled controls, `aria-invalid` +
  `role="alert"` errors, focus-visible rings, `prefers-reduced-motion` honoured,
  keyboard-only usable, works with JS disabled
- SEO: description, Open Graph, Twitter card, `Person` JSON-LD

## 8. Do not fake it

Every stat, quote and certification here is a **placeholder written to look real**.
Swap in what you actually have before you send this to anyone — a security engineer
caught inflating CVE counts or "9 delivered engagements" is finished, and a technical
interviewer will ask you to walk through all of it.
