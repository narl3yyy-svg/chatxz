"""Capture process stdout/stderr to a text file (Android Downloads) for field debugging."""

import atexit
import os
import sys
import threading
from datetime import datetime

_lock = threading.Lock()
_log_path = None
_orig_stdout = None
_orig_stderr = None


class _TeeStream:
    def __init__(self, original, log_path):
        self._original = original
        self._path = log_path
        self._file = open(log_path, "a", encoding="utf-8", errors="replace")
        self._file.write(
            f"\n--- chatxz debug log {datetime.now().isoformat()} ---\n"
        )
        self._file.flush()

    def write(self, data):
        if not data:
            return 0
        try:
            self._original.write(data)
        except Exception:
            pass
        with _lock:
            try:
                self._file.write(data)
                self._file.flush()
            except Exception:
                pass
        return len(data)

    def flush(self):
        try:
            self._original.flush()
        except Exception:
            pass
        with _lock:
            try:
                self._file.flush()
            except Exception:
                pass

    def isatty(self):
        return False

    def fileno(self):
        try:
            return self._original.fileno()
        except Exception:
            raise OSError("no fileno")

    def close_log(self):
        with _lock:
            try:
                self._file.close()
            except Exception:
                pass


def _dir_writable(path):
    try:
        os.makedirs(path, exist_ok=True)
        probe = os.path.join(path, ".chatxz_write_test")
        with open(probe, "w", encoding="utf-8") as fh:
            fh.write("ok")
        os.remove(probe)
        return True
    except OSError:
        return False


def android_app_downloads_dir():
    try:
        from java import jclass
        python = jclass("com.chaquo.python.Python")
        ctx = python.getPlatform().getApplication()
        environment = jclass("android.os.Environment")
        files = ctx.getExternalFilesDir(environment.DIRECTORY_DOWNLOADS)
        if files is not None:
            path = str(files.getAbsolutePath())
            if path:
                return path
    except Exception:
        pass
    return None


def android_public_downloads_dir():
    try:
        from java import jclass
        environment = jclass("android.os.Environment")
        downloads = environment.getExternalStoragePublicDirectory(
            environment.DIRECTORY_DOWNLOADS
        )
        if downloads is not None:
            path = str(downloads.getAbsolutePath())
            if path:
                return path
    except Exception:
        pass
    return None


def resolve_android_debug_dir():
    """Prefer app-private paths — public Downloads often needs extra storage permission."""
    try:
        from chatxz.utils.platform import android_files_dir
        files = android_files_dir()
        if files:
            logs = os.path.join(files, "debug_logs")
            if _dir_writable(logs):
                return logs, "app debug_logs folder"
    except Exception:
        pass
    app_dl = android_app_downloads_dir()
    if app_dl and _dir_writable(app_dl):
        return app_dl, "app Downloads folder"
    public = android_public_downloads_dir()
    if public and _dir_writable(public):
        return public, "phone Downloads"
    return None, ""


def debug_log_path():
    return _log_path


def _startup_log_tail(max_bytes=8000):
    try:
        base = os.environ.get("CHATXZ_FILES_DIR") or "."
        path = os.path.join(base, "chatxz-startup.log")
        if not os.path.isfile(path):
            return None
        size = os.path.getsize(path)
        with open(path, "rb") as fh:
            if size > max_bytes:
                fh.seek(size - max_bytes)
            data = fh.read()
        return data.decode("utf-8", errors="replace")
    except OSError:
        return None


def debug_log_tail(max_bytes=32000):
    """Return the tail of the active debug log for in-app viewing."""
    chunks = []
    startup = _startup_log_tail(max_bytes=8000)
    if startup:
        chunks.append("--- startup log ---\n" + startup)
    path = _log_path
    if path and os.path.isfile(path):
        try:
            size = os.path.getsize(path)
            with open(path, "rb") as fh:
                if size > max_bytes:
                    fh.seek(size - max_bytes)
                data = fh.read()
            chunks.append(data.decode("utf-8", errors="replace"))
        except OSError:
            pass
    if not chunks:
        return None
    return "\n".join(chunks)


def start_debug_capture():
    """Mirror stdout/stderr to Downloads/chatxz-debug-*.txt on Android."""
    global _log_path, _orig_stdout, _orig_stderr
    if _log_path:
        return _log_path
    try:
        from chatxz.utils.platform import is_android
        if not is_android():
            return None
    except Exception:
        return None

    downloads, label = resolve_android_debug_dir()
    if not downloads:
        return None

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = os.path.join(downloads, f"chatxz-debug-{stamp}.txt")
    latest = os.path.join(downloads, "chatxz-debug-latest.txt")

    _orig_stdout = sys.stdout
    _orig_stderr = sys.stderr
    sys.stdout = _TeeStream(_orig_stdout, path)
    sys.stderr = _TeeStream(_orig_stderr, path)
    _log_path = path

    try:
        with open(latest, "w", encoding="utf-8") as fh:
            fh.write(path + "\n")
    except OSError:
        pass

    print(f"[debug-log] Capturing logs to {path} ({label})")
    startup = _startup_log_tail(max_bytes=16000)
    if startup:
        try:
            with open(path, "a", encoding="utf-8", errors="replace") as fh:
                fh.write("\n--- chatxz-startup.log (prefixed) ---\n")
                fh.write(startup)
                fh.write("\n")
        except OSError:
            pass
    atexit.register(stop_debug_capture)
    return path


def list_debug_log_files():
    """Return readable debug log file paths (active log + recent archives)."""
    paths = []
    active = _log_path
    if active and os.path.isfile(active):
        paths.append(active)
    try:
        logs_dir, _ = resolve_android_debug_dir()
        if logs_dir and os.path.isdir(logs_dir):
            for name in sorted(os.listdir(logs_dir)):
                if not name.startswith("chatxz-debug") or not name.endswith(".txt"):
                    continue
                full = os.path.join(logs_dir, name)
                if os.path.isfile(full) and full not in paths:
                    paths.append(full)
    except Exception:
        pass
    return paths


def export_debug_logs(dest_dir):
    """Copy debug logs to a user-chosen folder (Android SAF / desktop path)."""
    dest_dir = os.path.normpath(os.path.expanduser((dest_dir or "").strip()))
    if not dest_dir:
        return 0, "Destination folder is empty"
    try:
        os.makedirs(dest_dir, exist_ok=True)
    except OSError as exc:
        return 0, f"Cannot create folder: {exc}"
    if not os.path.isdir(dest_dir):
        return 0, "Destination is not a folder"
    sources = list_debug_log_files()
    if not sources:
        return 0, "No debug log files found — enable Debug mode and restart the app"
    copied = 0
    import shutil
    for src in sources:
        try:
            shutil.copy2(src, os.path.join(dest_dir, os.path.basename(src)))
            copied += 1
        except OSError as exc:
            return copied, f"Copied {copied}, failed on {os.path.basename(src)}: {exc}"
    return copied, None


def stop_debug_capture():
    global _log_path, _orig_stdout, _orig_stderr
    for attr, orig in (("stdout", _orig_stdout), ("stderr", _orig_stderr)):
        stream = getattr(sys, attr, None)
        if stream is not None and hasattr(stream, "close_log"):
            try:
                stream.close_log()
            except Exception:
                pass
        if orig is not None:
            setattr(sys, attr, orig)
    _orig_stdout = None
    _orig_stderr = None
    _log_path = None