import psutil
import platform
import socket
import time

def get_stats():
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "uptime": time.time() - psutil.boot_time(),
        "cpu": psutil.cpu_percent(interval=None),
        "ram": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage('/').percent,
        "net_sent": round(psutil.net_io_counters().bytes_sent / (1024 * 1024), 2),
        "net_recv": round(psutil.net_io_counters().bytes_recv / (1024 * 1024), 2)
    }
