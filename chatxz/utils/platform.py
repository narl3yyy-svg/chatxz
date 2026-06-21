"""Platform detection and storage paths (desktop vs Android/Chaquopy)."""

import os
import sys

_android = None
_files_dir = None


def is_android():
    global _android
    if _android is not None:
        return _android
    try:
        from java import jclass
        jclass("com.chaquo.python.android.AndroidPlatform")
        _android = True
    except Exception:
        _android = "chaquopy" in sys.modules or os.environ.get("CHATXZ_ANDROID") == "1"
    return _android


def android_files_dir():
    global _files_dir
    if _files_dir:
        return _files_dir
    env = os.environ.get("CHATXZ_FILES_DIR")
    if env:
        _files_dir = env
        return _files_dir
    try:
        from java import jclass
        Python = jclass("com.chaquo.python.Python")
        ctx = Python.getPlatform().getApplication()
        _files_dir = str(ctx.getFilesDir().getAbsolutePath())
        return _files_dir
    except Exception:
        return None


def storage_root():
    """Writable root for config, data, and received files."""
    if is_android():
        base = android_files_dir() or os.path.expanduser("~")
        return os.path.join(base, "chatxz")
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return os.path.join(xdg, "chatxz")
    return os.path.join(os.path.expanduser("~"), ".config", "chatxz")


def lan_ip():
    """Best-effort LAN IP for direct file transfers."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            return ip
    except OSError:
        pass
    return None