"""In-memory ring buffer of recent metric samples.

The store is intentionally dependency-free (stdlib only) so history works
without Redis/Postgres. For multi-worker deployments (gunicorn -w 4) each
worker keeps its own buffer — documented in the README; promote to Redis
when horizontal scaling is required.
"""
from __future__ import annotations

import threading
from collections import deque


class HistoryStore:
    def __init__(self, maxlen: int = 180):
        self._data: deque = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def add(self, point: dict) -> None:
        with self._lock:
            self._data.append(point)

    def all(self, limit: int | None = None) -> list:
        with self._lock:
            items = list(self._data)
        if limit is not None and limit > 0:
            items = items[-limit:]
        return items

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def __len__(self) -> int:  # pragma: no cover - trivial
        with self._lock:
            return len(self._data)

    def set_maxlen(self, maxlen: int) -> None:
        """Resize capacity, preserving the most recent items."""
        with self._lock:
            self._data = deque(self._data, maxlen=maxlen)


history_store = HistoryStore(maxlen=180)


def record_from_stats(stats: dict) -> dict:
    """Project a full stats payload down to a compact history point."""
    network = stats.get("network", {}) or {}
    point = {
        "t": stats.get("timestamp"),
        "cpu": stats.get("cpu"),
        "ram": stats.get("ram"),
        "disk": stats.get("disk"),
        "net_down_kbps": network.get("recv_per_sec_kb", 0),
        "net_up_kbps": network.get("sent_per_sec_kb", 0),
    }
    history_store.add(point)
    return point
