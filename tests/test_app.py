import time

import pytest

from app import app


@pytest.fixture()
def client():
    app.config.update(TESTING=True)
    return app.test_client()


def test_dashboard_renders(client):
    res = client.get("/")
    assert res.status_code == 200
    body = res.get_data(as_text=True)
    assert "System Monitor" in body
    # The dashboard must poll this app, not a hardcoded remote deployment.
    assert "onrender.com" not in body
    assert "'/stats'" in body


def test_stats_returns_real_metrics(client):
    data = client.get("/stats").get_json()
    for key in ("hostname", "platform", "uptime", "cpu", "cpu_count",
                "ram", "disk", "net_sent", "net_recv", "timestamp"):
        assert key in data, key


def test_percentages_are_in_range(client):
    data = client.get("/stats").get_json()
    for key in ("cpu", "ram", "disk"):
        assert 0.0 <= data[key] <= 100.0, (key, data[key])


def test_cpu_readings_are_valid_floats(client):
    # cpu_percent(interval=None) measures the window since the previous call,
    # so an idle box legitimately reports ~0.0. What matters is that every
    # reading is a float within range and never raises.
    first = client.get("/stats").get_json()["cpu"]
    time.sleep(0.15)
    second = client.get("/stats").get_json()["cpu"]
    assert isinstance(first, float) and isinstance(second, float)
    assert 0.0 <= first <= 100.0 and 0.0 <= second <= 100.0


def test_healthz(client):
    assert client.get("/healthz").get_json() == {"status": "ok"}
