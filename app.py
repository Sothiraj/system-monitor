import os

from flask import Flask, jsonify, render_template

from utils.monitor import get_stats

app = Flask(__name__)


@app.route("/")
def dashboard():
    return render_template("index.html")


@app.route("/stats")
def stats():
    return jsonify(get_stats())


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    # Bind 0.0.0.0 so the app is reachable from outside the host (containers,
    # proxies, the Arena live preview) rather than only from 127.0.0.1.
    # Debug is opt-in via FLASK_DEBUG=1: the Werkzeug debugger is a remote code
    # execution surface and must never be enabled unconditionally.
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
