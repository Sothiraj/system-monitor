import os
import platform
import socket
import time

import psutil

# psutil seeds its CPU baseline at import time (psutil/__init__.py wraps the
# seed in try/except and falls back to an empty dict). This call guarantees a
# baseline for the current thread even if that seed failed, so the first
# /stats response measures a real window instead of dividing over nothing.
psutil.cpu_percent(interval=None)



def _disk_root():
    """Return a path psutil.disk_usage() accepts on the current OS.

    '/' is correct on POSIX but unreliable on Windows (this project was
    developed on a Windows box), so use the system drive root there.
    """
    if os.name == "nt":
        return os.environ.get("SystemDrive", "C:") + os.sep
    return "/"


def get_stats():
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage(_disk_root())
    net = psutil.net_io_counters()

    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "uptime": time.time() - psutil.boot_time(),
        "cpu": psutil.cpu_percent(interval=None),
        "cpu_count": psutil.cpu_count(logical=True) or 1,
        "ram": mem.percent,
        "ram_used_gb": round(mem.used / (1024 ** 3), 2),
        "ram_total_gb": round(mem.total / (1024 ** 3), 2),
        "disk": disk.percent,
        "disk_used_gb": round(disk.used / (1024 ** 3), 2),
        "disk_total_gb": round(disk.total / (1024 ** 3), 2),
        "net_sent": round(net.bytes_sent / (1024 * 1024), 2),
        "net_recv": round(net.bytes_recv / (1024 * 1024), 2),
        "timestamp": time.time(),
    }
