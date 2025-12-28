import psutil
import socket
import requests
from datetime import datetime

MIN_FREE_PERCENT = 10
BARK_URL = "https://api.day.app/7xLt8jGJxwJXQy7H5fGG4m"

hostname = socket.gethostname()
alerts = []

for part in psutil.disk_partitions(all=False):
    if "cdrom" in part.opts or part.fstype == "":
        continue
    usage = psutil.disk_usage(part.mountpoint)
    free_gb = usage.free / (1024 ** 3)
    free_percent = 100 - usage.percent

    is_alert = free_percent < MIN_FREE_PERCENT

    if is_alert:
        alerts.append(
            f"{datetime.now().strftime('%Y-%m-%d %H:%M')} | {hostname} | {part.device} | 剩余 {free_gb:.1f} GB ({free_percent:.1f}%)")


if alerts:
    content = "\n".join(alerts)
    title = f"⚠ 硬盘报警 - {hostname}"
    payload = {
        "title": title,
        "body": content
    }
    requests.post(f"{BARK_URL}", json=payload)
