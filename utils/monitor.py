"""System metric collection built on psutil.

Design notes
------------
* Cross-platform: disk probing falls back across mount points so the code
  works on Linux ('/'), Windows ('C:\\\\') and macOS.
* ``cpu_percent`` is primed at import: the first call with
  ``interval=None`` is otherwise always meaningless (0.0).
* Network counters are cumulative bytes since boot; this module converts
  them into per-second rates via a thread-safe delta tracker.
* ``get_stats`` preserves the v1 legacy shape for backwards compatibility.
  New consumers should use :func:`get_stats_full` / :func:`get_stats_cached`.
"""
from __future__ import annotations

import datetime
import os
import platform as platform_mod
import socket
import sys
import threading
import time

import psutil

_MB = 1024 * 1024
_GB = 1024 * 1024 * 1024

# Prime cpu_percent so subsequent interval=None calls return real values.
try:
    psutil.cpu_percent(interval=None)
except Exception:
    pass

_net_lock = threading.Lock()
_prev_net = None
_prev_net_time: float | None = None

_cache_lock = threading.Lock()
_cache_value: dict | None = None
_cache_time: float = 0.0


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def format_uptime(seconds: float) -> str:
    seconds = max(0, int(seconds))
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, secs = divmod(seconds, 60)
    if days:
        return f"{days}d {hours}h {minutes}m {secs}s"
    if hours:
        return f"{hours}h {minutes}m {secs}s"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def _safe_root_usage():
    """Return psutil disk usage for the most appropriate root path."""
    candidates: list[str] = []
    # Preferred candidates first.
    candidates.append(os.path.abspath(os.sep))
    if os.name == "nt":
        drive = os.getenv("SystemDrive", "C:") + os.sep
        candidates.append(drive)
    candidates.append("/")

    errors = []
    for path in candidates:
        try:
            return psutil.disk_usage(path), path
        except (FileNotFoundError, OSError) as exc:  # pragma: no cover - env dependent
            errors.append(exc)
    # Last resort: first accessible partition.
    for part in psutil.disk_partitions(all=False):
        try:
            return psutil.disk_usage(part.mountpoint), part.mountpoint
        except (FileNotFoundError, OSError, PermissionError):
            continue
    raise OSError(f"No accessible disk mount found ({errors!r})")


def _net_snapshot():
    """Return (counters, sent_per_sec_bytes, recv_per_sec_bytes)."""
    global _prev_net, _prev_net_time
    with _net_lock:
        cur = psutil.net_io_counters()
        now = time.monotonic()
        sent_rate = 0.0
        recv_rate = 0.0
        if _prev_net is not None and _prev_net_time is not None:
            dt = max(now - _prev_net_time, 1e-6)
            sent_rate = max(0.0, (cur.bytes_sent - _prev_net.bytes_sent) / dt)
            recv_rate = max(0.0, (cur.bytes_recv - _prev_net.bytes_recv) / dt)
        _prev_net = cur
        _prev_net_time = now
        return cur, sent_rate, recv_rate


def get_cpu_detail() -> dict:
    try:
        per_cpu = psutil.cpu_percent(interval=None, percpu=True) or []
    except Exception:
        per_cpu = []
    try:
        overall = psutil.cpu_percent(interval=None)
    except Exception:
        overall = 0.0
    try:
        freq = psutil.cpu_freq()
        freq_info = (
            {"current_mhz": round(freq.current, 1), "min_mhz": freq.min, "max_mhz": freq.max}
            if freq
            else None
        )
    except Exception:
        freq_info = None
    try:
        load_avg = list(os.getloadavg())  # Unix only; raises on Windows
    except (AttributeError, OSError):
        load_avg = None
    return {
        "percent": float(overall or 0.0),
        "per_cpu": [float(x) for x in per_cpu],
        "count_logical": psutil.cpu_count(logical=True),
        "count_physical": psutil.cpu_count(logical=False),
        "freq": freq_info,
        "load_avg_1_5_15": load_avg,
    }


def get_memory_detail() -> dict:
    vm = psutil.virtual_memory()
    try:
        swap = psutil.swap_memory()
        swap_info = {
            "percent": float(swap.percent),
            "total_gb": round(swap.total / _GB, 2),
            "used_gb": round(swap.used / _GB, 2),
        }
    except Exception:
        swap_info = {"percent": 0.0, "total_gb": 0.0, "used_gb": 0.0}
    return {
        "percent": float(vm.percent),
        "total_gb": round(vm.total / _GB, 2),
        "available_gb": round(vm.available / _GB, 2),
        "used_gb": round(vm.used / _GB, 2),
        "free_gb": round(vm.free / _GB, 2),
        "swap": swap_info,
    }


def get_disk_detail() -> dict:
    usage, root_path = _safe_root_usage()
    partitions: list[dict] = []
    try:
        for part in psutil.disk_partitions(all=False):
            # Skip pseudo-filesystems that raise or report nothing useful.
            if part.fstype in ("", "squashfs", "overlay") and os.name != "nt":
                # Still try, but tolerate failure silently.
                pass
            try:
                u = psutil.disk_usage(part.mountpoint)
            except (FileNotFoundError, OSError, PermissionError):
                continue
            partitions.append(
                {
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "fstype": part.fstype,
                    "percent": float(u.percent),
                    "total_gb": round(u.total / _GB, 2),
                    "used_gb": round(u.used / _GB, 2),
                    "free_gb": round(u.free / _GB, 2),
                }
            )
    except Exception:
        pass
    return {
        "percent": float(usage.percent),
        "root_path": root_path,
        "total_gb": round(usage.total / _GB, 2),
        "used_gb": round(usage.used / _GB, 2),
        "free_gb": round(usage.free / _GB, 2),
        "partitions": partitions,
    }


def get_network_detail() -> dict:
    counters, sent_bps, recv_bps = _net_snapshot()
    return {
        "sent_mb": round(counters.bytes_sent / _MB, 2),
        "recv_mb": round(counters.bytes_recv / _MB, 2),
        "sent_per_sec_kb": round(sent_bps / 1024, 2),
        "recv_per_sec_kb": round(recv_bps / 1024, 2),
        "packets_sent": counters.packets_sent,
        "packets_recv": counters.packets_recv,
        "errin": getattr(counters, "errin", 0),
        "errout": getattr(counters, "errout", 0),
    }


def get_system_info() -> dict:
    boot_ts = psutil.boot_time()
    now = time.time()
    try:
        process_count = len(psutil.pids())
    except Exception:
        process_count = 0
    try:
        users = len(psutil.users())
    except Exception:
        users = 0
    return {
        "hostname": socket.gethostname(),
        "platform": platform_mod.platform(),
        "platform_release": platform_mod.release(),
        "python_version": sys.version.split()[0],
        "boot_time": boot_ts,
        "boot_time_iso": datetime.datetime.fromtimestamp(
            boot_ts, tz=datetime.timezone.utc
        ).isoformat(),
        "uptime_seconds": now - boot_ts,
        "process_count": process_count,
        "users": users,
    }


def get_stats() -> dict:
    """Legacy v1 shape — fixed but backwards compatible.

    Keys: hostname, platform, uptime, cpu, ram, disk, net_sent, net_recv.
    """
    sysinfo = get_system_info()
    cpu = get_cpu_detail()
    mem = get_memory_detail()
    disk = get_disk_detail()
    net = get_network_detail()
    return {
        "hostname": sysinfo["hostname"],
        "platform": sysinfo["platform"],
        "uptime": sysinfo["uptime_seconds"],
        "cpu": round(cpu["percent"], 1),
        "ram": round(mem["percent"], 1),
        "disk": round(disk["percent"], 1),
        "net_sent": net["sent_mb"],
        "net_recv": net["recv_mb"],
    }


def get_stats_full() -> dict:
    """Enriched stats payload for /api/v1/stats (superset of legacy)."""
    sysinfo = get_system_info()
    cpu = get_cpu_detail()
    mem = get_memory_detail()
    disk = get_disk_detail()
    net = get_network_detail()
    uptime = sysinfo["uptime_seconds"]
    return {
        "timestamp": _now_iso(),
        # Legacy-compatible top-level keys:
        "hostname": sysinfo["hostname"],
        "platform": sysinfo["platform"],
        "uptime": uptime,
        "uptime_seconds": uptime,
        "uptime_human": format_uptime(uptime),
        "cpu": round(cpu["percent"], 1),
        "ram": round(mem["percent"], 1),
        "disk": round(disk["percent"], 1),
        "net_sent": net["sent_mb"],
        "net_recv": net["recv_mb"],
        # Enriched detail blocks:
        "cpu_detail": cpu,
        "memory": mem,
        "disks": disk,
        "network": net,
        "system": sysinfo,
    }


def get_stats_cached(ttl: float = 1.0) -> dict:
    """Return a cached full payload, recomputing at most every ``ttl`` sec."""
    global _cache_value, _cache_time
    now = time.monotonic()
    with _cache_lock:
        if _cache_value is not None and (now - _cache_time) < ttl:
            return _cache_value
    fresh = get_stats_full()
    with _cache_lock:
        _cache_value = fresh
        _cache_time = now
    return fresh


def clear_cache() -> None:  # helper for tests
    global _cache_value, _cache_time
    with _cache_lock:
        _cache_value = None
        _cache_time = 0.0
