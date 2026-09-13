"""HTTP-level tests for the Flask app factory."""
import json

import pytest

from app import create_app
from utils.history import history_store


@pytest.fixture()
def client():
    app = create_app("testing")
    app.config.update(TESTING=True)
    history_store.clear()
    with app.test_client() as client:
        yield client


def test_dashboard_renders(client):
    res = client.get("/")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    # No hardcoded production URL may remain in the template.
    assert "onrender.com" not in html
    assert "simulateFluctuation" not in html
    assert "/api/v1/stats" in html
    assert "cpuChart" in html and "netChart" in html


def test_health_and_ready(client):
    assert client.get("/healthz").get_json()["status"] == "ok"
    assert client.get("/readyz").get_json()["status"] == "ready"


def test_legacy_stats_compat(client):
    data = client.get("/stats").get_json()
    assert {"hostname", "platform", "uptime", "cpu", "ram", "disk", "net_sent", "net_recv"} <= set(data)
    # Alias behaves identically.
    assert client.get("/api/stats").status_code == 200


def test_v1_stats_and_history_flow(client):
    stats = client.get("/api/v1/stats").get_json()
    assert stats["timestamp"]
    assert stats["network"]["recv_per_sec_kb"] >= 0
    assert "cpu_detail" in stats

    history = client.get("/api/v1/history?limit=5").get_json()
    assert history["count"] >= 1
    assert history["points"][-1]["cpu"] == stats["cpu"]

    assert client.get("/api/v1/system").get_json()["hostname"]

    res = client.get("/api/v1/stats")
    assert res.headers["Cache-Control"] == "no-store"
    assert res.headers["Access-Control-Allow-Origin"] == "*"


def test_history_clear(client):
    client.get("/api/v1/stats")
    assert client.post("/api/v1/history/clear").get_json() == {"status": "cleared"}
    assert client.get("/api/v1/history").get_json()["count"] == 0


def test_api_404_is_json(client):
    res = client.get("/api/v1/nope")
    assert res.status_code == 404
    assert res.get_json()["error"] == "not found"


def test_stream_first_chunk(client):
    res = client.get("/api/v1/stream?interval=0.5", buffered=False)
    assert res.status_code == 200
    assert "text/event-stream" in res.content_type
    first = next(res.response).decode()
    assert "connected" in first or "data:" in first
