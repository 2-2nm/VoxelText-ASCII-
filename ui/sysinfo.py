import datetime
import getpass
import os
import platform
import time

from core.utils import MAX_WORKERS

try:
    import psutil
except ImportError:
    psutil = None

_GB = 1024 ** 3


def _gb(n):
    return round(n / _GB, 1)


def current_user():
    try:
        return os.getlogin()
    except Exception:
        pass
    try:
        return getpass.getuser()
    except Exception:
        return "root"


def _registry_value(subkey, name):
    import winreg
    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, subkey)
    try:
        return winreg.QueryValueEx(key, name)[0].strip()
    finally:
        winreg.CloseKey(key)


def _cpu_name():
    if platform.system() == "Windows":
        try:
            return _registry_value(r"HARDWARE\DESCRIPTION\System\CentralProcessor\0", "ProcessorNameString")
        except Exception:
            pass
    return platform.processor() or "Unknown CPU"


def _gpu_name():
    if platform.system() != "Windows":
        return "Unknown GPU"
    try:
        return _registry_value(
            r"SYSTEM\ControlSet001\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000",
            "DriverDesc",
        )
    except Exception:
        return "Integrated / System Graphics"


def _disk_summary():
    parts = []
    for p in psutil.disk_partitions(all=False):
        if os.name == "nt" and "cdrom" in p.opts.lower():
            continue
        try:
            usage = psutil.disk_usage(p.mountpoint)
        except PermissionError:
            continue
        parts.append(f"{p.mountpoint.replace(chr(92), '')} {_gb(usage.used)}/{_gb(usage.total)} GB")
    return " | ".join(parts)


def _uptime():
    hours, rem = divmod(int(time.time() - psutil.boot_time()), 3600)
    minutes = rem // 60
    return f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"


def _memory_disk_uptime():
    if not psutil:
        return "N/A", "N/A", "N/A"
    try:
        mem = psutil.virtual_memory()
        ram = f"{_gb(mem.used)} GB / {_gb(mem.total)} GB ({mem.percent}%)"
        return ram, _disk_summary(), _uptime()
    except Exception:
        return "N/A", "N/A", "N/A"


def get_sys_info():
    ram, disk, uptime = _memory_disk_uptime()
    return {
        "title": f"{current_user()}@{platform.node() or 'terminal'}",
        "OS": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "Kernel": platform.version().split(" ")[0],
        "Uptime": uptime,
        "DateTime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "CPU": _cpu_name(),
        "GPU": _gpu_name(),
        "Memory": ram,
        "Disk": disk,
        "Terminal": f"VXL Engine v4.0.0 Global ({MAX_WORKERS} Threads)",
    }
