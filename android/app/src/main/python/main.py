"""Android entry point — starts the full chatxz web server in a background thread."""

import os
import socket
import threading
import time
import traceback

os.environ.setdefault("CHATXZ_ANDROID", "1")

try:
    from chatxz.utils.platform import patch_embedded_signals
    patch_embedded_signals()
except Exception:
    pass

# Bind on all interfaces so LAN peers can reach beacon-ingest and file transfer.
BIND_HOST, PORT = "0.0.0.0", 8742
# WebView always loads the local loopback URL.
WEB_HOST = "127.0.0.1"
_server_error = []


def _wait_for_port(host, port, timeout=90):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _server_error:
            return False
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect((host, port))
            s.close()
            return True
        except OSError:
            time.sleep(0.25)
    return False


def start_server():
    """Called from MainActivity via Chaquopy. Returns (host, port) or (None, error)."""
    try:
        from chatxz.utils.platform import android_files_dir, is_android
        files_dir = android_files_dir()
        if files_dir:
            os.environ["CHATXZ_FILES_DIR"] = files_dir
        if not is_android():
            os.environ["CHATXZ_ANDROID"] = "1"
    except Exception as e:
        return "None", f"Platform init: {type(e).__name__}: {e}"

    def _run():
        try:
            from chatxz.web.server import ChatWebServer
            server = ChatWebServer(
                host=BIND_HOST, port=PORT, verbose=False, force=False, embedded=True,
            )
            server.run_embedded()
        except Exception:
            _server_error.append(traceback.format_exc())

    thread = threading.Thread(target=_run, name="chatxz-server", daemon=True)
    thread.start()

    if not _wait_for_port(WEB_HOST, PORT):
        if _server_error:
            err = _server_error[0]
            # Keep the most useful tail of long tracebacks for the UI dialog.
            if len(err) > 4000:
                err = err[-4000:]
            return "None", err
        return "None", "Server timeout — port 8742 did not open in 90s"

    return WEB_HOST, str(PORT)