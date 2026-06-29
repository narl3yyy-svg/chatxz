"""Linux signalfd shutdown — SIGINT works even when other threads block."""

from __future__ import annotations

import ctypes
import os
import signal
import struct
import sys
import threading
from typing import Callable, Optional

_SIGINFO_STRUCT_SIZE = 128


class LinuxSignalfdShutdown:
    """Dedicated thread reads SIGINT/SIGTERM via signalfd (not main-thread delivery)."""

    def __init__(self, on_signal: Callable[[int], None]):
        self._on_signal = on_signal
        self._thread: Optional[threading.Thread] = None
        self._sfd = -1
        self._closed = threading.Event()

    def start(self) -> bool:
        if sys.platform not in ("linux", "linux2"):
            return False
        if self._thread and self._thread.is_alive():
            return True
        self._closed.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="chatxz-signalfd",
            daemon=True,
        )
        self._thread.start()
        return True

    def stop(self) -> None:
        self._closed.set()
        sfd = self._sfd
        self._sfd = -1
        if sfd >= 0:
            try:
                os.close(sfd)
            except OSError:
                pass

    def _run(self) -> None:
        try:
            libc = ctypes.CDLL(None, use_errno=True)
        except Exception:
            return

        SIG_BLOCK = 0
        SFD_CLOEXEC = 0x80000

        class _Sigset(ctypes.Structure):
            _fields_ = [("bits", ctypes.c_ulong * 16)]

        mask = _Sigset()
        if libc.sigemptyset(ctypes.byref(mask)) != 0:
            return
        for sig in (signal.SIGINT, signal.SIGTERM):
            libc.sigaddset(ctypes.byref(mask), sig)
        if libc.pthread_sigmask(SIG_BLOCK, ctypes.byref(mask), None) != 0:
            return

        sfd = libc.signalfd(-1, ctypes.byref(mask), SFD_CLOEXEC)
        if sfd < 0:
            return
        self._sfd = sfd

        while not self._closed.is_set():
            try:
                data = os.read(sfd, _SIGINFO_STRUCT_SIZE * 4)
            except OSError:
                break
            if not data:
                continue
            for offset in range(0, len(data), _SIGINFO_STRUCT_SIZE):
                chunk = data[offset : offset + _SIGINFO_STRUCT_SIZE]
                if len(chunk) < 4:
                    continue
                signum = struct.unpack_from("I", chunk, 0)[0]
                try:
                    self._on_signal(int(signum))
                except Exception:
                    os._exit(130 if signum == signal.SIGINT else 0)