#!/usr/bin/env python3
"""Dev server for the portfolio: http://localhost:8000

    python3 tools/serve.py            # port 8000
    python3 tools/serve.py 5000       # any port

Plain `python3 -m http.server` works too; this just adds no-cache headers (so a
refresh always shows your latest edit), the right MIME types, and binds 0.0.0.0
so the preview proxy can reach it.
"""
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent


class Handler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".js": "text/javascript",
        ".css": "text/css",
        ".svg": "image/svg+xml",
        ".woff2": "font/woff2",
        ".webp": "image/webp",
        ".mjs": "text/javascript",
    }

    def end_headers(self):
        # never serve a stale build while someone is editing
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write("  %-15s %s\n" % (self.address_string(), fmt % args))


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    handler = partial(Handler, directory=str(SITE))
    with ThreadingHTTPServer(("0.0.0.0", port), handler) as httpd:
        print(f"  portfolio  →  http://localhost:{port}\n  serving    →  {SITE}\n  Ctrl+C to stop\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n  stopped.")


if __name__ == "__main__":
    main()
