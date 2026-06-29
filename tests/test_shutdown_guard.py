import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from chatxz.utils.shutdown_guard import ShutdownGuard


def test_shutdown_guard_import():
    assert ShutdownGuard is not None


def test_shutdown_guard_arm_darwin(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    seen = []

    guard = ShutdownGuard(lambda sig: seen.append(sig))
    guard.arm()
    assert guard._sigwait_thread is not None