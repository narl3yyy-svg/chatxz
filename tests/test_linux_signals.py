import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from chatxz.utils.linux_signals import LinuxSignalfdShutdown


def test_linux_signalfd_import():
    assert LinuxSignalfdShutdown is not None


def test_linux_signalfd_skips_non_linux(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    seen = []

    def on_sig(n):
        seen.append(n)

    watcher = LinuxSignalfdShutdown(on_sig)
    assert watcher.start() is False