"""Unit tests for utils/monitor.py — no network, no fixtures needed."""
import time

from utils.history import HistoryStore, record_from_stats
from utils.monitor import (
    clear_cache,
    format_uptime,
    get_cpu_detail,
    get_disk_detail,
    get_memory_detail,
    get_network_detail,
    get_stats,
    get_stats_cached,
    get_stats_full,
    get_system_info,
)


def test_format_uptime():
    assert format_uptime(5) == "5s"
    assert format_uptime(125) == "2m 5s"
    assert format_uptime(3700) == "1h 1m 40s"
    assert format_uptime(90061) == "1d 1h 1m 1s"


def test_legacy_stats_shape_and_ranges():
    stats = get_stats()
    assert set(stats) == {
        "hostname", "platform", "uptime", "cpu", "ram", "disk",
        "net_sent", "net_recv",
    }
    assert isinstance(stats["hostname"], str) and stats["hostname"]
    assert 0 <= stats["cpu"] <= 100
    assert 0 <= stats["ram"] <= 100
    assert 0 <= stats["disk"] <= 100
    assert stats["uptime"] > 0
    assert stats["net_sent"] >= 0 and stats["net_recv"] >= 0


def test_cpu_detail():
    cpu = get_cpu_detail()
    assert 0 <= cpu["percent"] <= 100
    assert cpu["count_logical"] and cpu["count_logical"] >= 1
    assert isinstance(cpu["per_cpu"], list)
    # load average is None on Windows, a 3-tuple elsewhere.
    assert cpu["load_avg_1_5_15"] is None or len(cpu["load_avg_1_5_15"]) == 3


def test_memory_detail():
    mem = get_memory_detail()
    assert 0 <= mem["percent"] <= 100
    assert mem["total_gb"] > 0
    assert mem["used_gb"] <= mem["total_gb"] + 0.5  # rounding tolerance


def test_disk_detail_cross_platform():
    disk = get_disk_detail()
    assert 0 <= disk["percent"] <= 100
    assert disk["root_path"]
    assert disk["total_gb"] > 0
    assert isinstance(disk["partitions"], list)


def test_network_rates_non_negative():
    first = get_network_detail()
    time.sleep(0.05)
    second = get_network_detail()
    assert first["sent_per_sec_kb"] >= 0
    assert second["recv_per_sec_kb"] >= 0
    assert second["sent_mb"] >= 0


def test_full_stats_is_legacy_superset():
    full = get_stats_full()
    for key in ("hostname", "platform", "uptime", "cpu", "ram", "disk", "net_sent", "net_recv"):
        assert key in full
    for block in ("cpu_detail", "memory", "disks", "network", "system"):
        assert block in full
    assert full["timestamp"]
    assert full["uptime_human"]


def test_system_info():
    info = get_system_info()
    assert info["boot_time_iso"]
    assert info["uptime_seconds"] > 0
    assert info["process_count"] > 0


def test_cached_stats_respects_ttl():
    clear_cache()
    a = get_stats_cached(ttl=60)
    b = get_stats_cached(ttl=60)
    assert a is b  # cache hit returns identical object
    clear_cache()
    c = get_stats_cached(ttl=60)
    assert c is not a


def test_history_store_and_record():
    store = HistoryStore(maxlen=3)
    for i in range(5):
        store.add({"t": i})
    assert len(store) == 3  # ring eviction
    assert [p["t"] for p in store.all()] == [2, 3, 4]
    assert [p["t"] for p in store.all(limit=2)] == [3, 4]
    store.clear()
    assert len(store) == 0

    point = record_from_stats(get_stats_full())
    assert {"t", "cpu", "ram", "disk", "net_down_kbps", "net_up_kbps"} <= set(point)
