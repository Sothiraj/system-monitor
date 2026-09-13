"""System Monitor Dashboard — Flask application factory.

Routes
------
    GET /                  Dashboard UI
    GET /healthz           Liveness probe  {"status": "ok", ...}
    GET /readyz            Readiness probe (psutil must respond)
    GET /stats             Legacy v1 JSON (backwards compatible)
    GET /api/stats         Legacy alias
    GET /api/v1/stats      Full enriched stats payload
    GET /api/v1/history    Recent samples ring buffer (?limit=N)
    GET /api/v1/system     Static-ish system info
    GET /api/v1/stream     Server-Sent Events live feed
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time

from flask import Flask, jsonify, render_template, request, Response

from config import get_config
from utils.history import history_store, record_from_stats
from utils.monitor import clear_cache, get_stats_cached, get_system_info

log = logging.getLogger(__name__)
_sampler_started = False
_sampler_lock = threading.Lock()


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    # Keep request logs but quiet the per-poll noise in production.
    if not app.debug:
        logging.getLogger("werkzeug").setLevel(logging.WARNING)

    history_store.set_maxlen(app.config.get("HISTORY_MAXLEN", 180))

    _register_routes(app)
    _register_errors(app)
    _maybe_start_sampler(app)
    return app


# ---------------------------------------------------------------- routes ---
def _register_routes(app: Flask) -> None:

    @app.get("/")
    def dashboard():
        return render_template(
            "index.html",
            app_version=app.config["APP_VERSION"],
            alert_cpu=app.config["ALERT_CPU"],
            alert_ram=app.config["ALERT_RAM"],
            alert_disk=app.config["ALERT_DISK"],
        )

    @app.get("/healthz")
    def healthz():
        return jsonify(
            {
                "status": "ok",
                "service": app.config["APP_NAME"],
                "version": app.config["APP_VERSION"],
            }
        )

    @app.get("/readyz")
    def readyz():
        try:
            info = get_system_info()
            ready = bool(info.get("hostname"))
        except Exception as exc:  # psutil failure => not ready
            log.warning("readiness check failed: %s", exc)
            return jsonify({"status": "not_ready", "error": str(exc)}), 503
        if not ready:
            return jsonify({"status": "not_ready"}), 503
        return jsonify({"status": "ready"})

    @app.get("/stats")
    @app.get("/api/stats")
    def legacy_stats():
        """Legacy endpoint — same keys as v1, served from the shared cache
        so rapid pollers never see back-to-back cpu_percent artefacts."""
        try:
            ttl = float(app.config.get("STATS_CACHE_TTL", 1.0))
            full = get_stats_cached(ttl=ttl)
            return jsonify({k: full[k] for k in (
                "hostname", "platform", "uptime", "cpu",
                "ram", "disk", "net_sent", "net_recv",
            )})
        except Exception as exc:
            log.exception("legacy /stats failed")
            return jsonify({"error": "failed to collect stats", "detail": str(exc)}), 500

    @app.get("/api/v1/stats")
    def api_stats():
        try:
            ttl = float(app.config.get("STATS_CACHE_TTL", 1.0))
            stats = get_stats_cached(ttl=ttl)
            record_from_stats(stats)
            return jsonify(stats)
        except Exception as exc:
            log.exception("/api/v1/stats failed")
            return jsonify({"error": "failed to collect stats", "detail": str(exc)}), 500

    @app.get("/api/v1/system")
    def api_system():
        try:
            return jsonify(get_system_info())
        except Exception as exc:
            log.exception("/api/v1/system failed")
            return jsonify({"error": "failed to collect system info", "detail": str(exc)}), 500

    @app.get("/api/v1/history")
    def api_history():
        try:
            limit = request.args.get("limit", default=120, type=int)
            limit = max(1, min(limit or 120, 500))
            return jsonify({"points": history_store.all(limit=limit), "count": len(history_store)})
        except Exception as exc:
            log.exception("/api/v1/history failed")
            return jsonify({"error": "failed to read history", "detail": str(exc)}), 500

    @app.post("/api/v1/history/clear")
    def api_history_clear():
        history_store.clear()
        clear_cache()
        return jsonify({"status": "cleared"})

    @app.get("/api/v1/stream")
    def api_stream():
        """Server-Sent Events: pushes a stats event every ``interval`` sec."""
        try:
            interval = float(request.args.get("interval", "2.0"))
        except ValueError:
            interval = 2.0
        interval = max(0.5, min(interval, 30.0))

        def generate():
            yield ": connected\n\n"
            while True:
                try:
                    stats = get_stats_cached(ttl=0.9)
                    record_from_stats(stats)
                    yield f"data: {json.dumps(stats)}\n\n"
                except GeneratorExit:
                    break
                except Exception as exc:  # keep stream alive on transient errors
                    log.warning("stream sample failed: %s", exc)
                    yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"
                time.sleep(interval)

        return Response(generate(), mimetype="text/event-stream")

    @app.after_request
    def _headers(resp):
        # API responses must never be cached by intermediaries.
        if request.path.startswith(("/api/", "/stats", "/healthz", "/readyz")):
            resp.headers["Cache-Control"] = "no-store"
        # Read-only metrics API: allow embedding/fetching from any origin.
        if request.path.startswith(("/api/", "/stats")):
            resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        return resp


# ---------------------------------------------------------------- errors ---
def _register_errors(app: Flask) -> None:

    def _is_api() -> bool:
        return request.path.startswith(("/api/", "/stats", "/healthz", "/readyz"))

    @app.errorhandler(404)
    def not_found(_exc):
        if _is_api():
            return jsonify({"error": "not found", "path": request.path}), 404
        return (
            "<h1>404</h1><p>Page not found. <a href='/'>Back to dashboard</a></p>",
            404,
        )

    @app.errorhandler(500)
    def server_error(exc):
        log.exception("unhandled error: %s", exc)
        if _is_api():
            return jsonify({"error": "internal server error"}), 500
        return (
            "<h1>500</h1><p>Something went wrong. <a href='/'>Back to dashboard</a></p>",
            500,
        )


# --------------------------------------------------------------- sampler ---
def _maybe_start_sampler(app: Flask) -> None:
    """Background thread keeping history warm even with no active viewers."""
    global _sampler_started
    if not app.config.get("ENABLE_SAMPLER", True):
        return
    if app.config.get("TESTING"):
        return
    with _sampler_lock:
        if _sampler_started:
            return
        _sampler_started = True

    interval = float(app.config.get("SAMPLER_INTERVAL", 2.0))

    def _loop():
        log.info("history sampler started (every %.1fs)", interval)
        while True:
            try:
                # ttl=0 forces a fresh sample on the sampler cadence.
                stats = get_stats_cached(ttl=0)
                record_from_stats(stats)
            except Exception as exc:  # never let the sampler die
                log.warning("sampler sample failed: %s", exc)
            time.sleep(interval)

    thread = threading.Thread(target=_loop, name="history-sampler", daemon=True)
    thread.start()


# Backwards-compatible module-level app (gunicorn app:app, Flask CLI, tests).
app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    # Debug only when explicitly requested AND not production.
    debug = os.getenv("FLASK_DEBUG", "") == "1" and os.getenv("FLASK_ENV") != "production"
    app.run(host="0.0.0.0", port=port, debug=debug)
