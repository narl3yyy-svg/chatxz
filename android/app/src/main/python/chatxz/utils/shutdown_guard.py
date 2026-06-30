"""Reliable Ctrl+C / SIGTERM — works when the asyncio loop or PortAudio blocks."""

from __future__ import annotations

import os
import signal
import sys
import threading
from typing import Callable, Optional

_CTRL_C_EVENT = 0
_CTRL_BREAK_EVENT = 1
_CTRL_CLOSE_EVENT = 2


class ShutdownGuard:
    """Platform hooks that deliver shutdown even if signal.signal was clobbered."""

    def __init__(self, on_shutdown: Callable[[int], None]):
        self._on_shutdown = on_shutdown
        self._win_handler = None
        self._sigwait_thread: Optional[threading.Thread] = None
        self._armed = False
        self._lock = threading.Lock()

    def arm(self) -> None:
        with self._lock:
            if sys.platform == "win32":
                self._arm_windows()
            elif sys.platform == "darwin":
                # macOS: use signal.set_wakeup_fd + asyncio pipe (see server.py).
                pass
            elif sys.platform not in ("linux", "linux2"):
                try:
                    signal.pthread_sigmask(
                        signal.SIG_BLOCK,
                        [signal.SIGINT, signal.SIGTERM],
                    )
                except Exception:
                    pass
                self._arm_sigwait()
            self._armed = True

    def refresh(self) -> None:
        """Re-register after RNS or other libs replace handlers."""
        if sys.platform == "win32":
            self._arm_windows()

    def _arm_windows(self) -> None:
        try:
            import ctypes
            from ctypes import wintypes
        except Exception:
            return

        guard = self

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)
        def _handler(ctrl_type):
            if ctrl_type in (_CTRL_C_EVENT, _CTRL_BREAK_EVENT, _CTRL_CLOSE_EVENT):
                try:
                    guard._on_shutdown(signal.SIGINT)
                except Exception:
                    os._exit(130)
                return True
            return False

        self._win_handler = _handler
        try:
            ctypes.windll.kernel32.SetConsoleCtrlHandler(_handler, True)
        except Exception:
            pass

    def _arm_sigwait(self) -> None:
        if self._sigwait_thread and self._sigwait_thread.is_alive():
            return

        def _run() -> None:
            try:
                signal.pthread_sigmask(
                    signal.SIG_BLOCK,
                    [signal.SIGINT, signal.SIGTERM],
                )
            except Exception:
                return
            while True:
                try:
                    sig = signal.sigwait([signal.SIGINT, signal.SIGTERM])
                except Exception:
                    break
                try:
                    self._on_shutdown(int(sig))
                except Exception:
                    os._exit(130 if int(sig) == signal.SIGINT else 0)

        self._sigwait_thread = threading.Thread(
            target=_run,
            name="chatxz-sigwait",
            daemon=True,
        )
        self._sigwait_thread.start()