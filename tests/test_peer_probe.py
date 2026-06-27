"""Tests for peer probe RTT tracking and stale eviction."""

import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from chatxz.core.discovery import PeerDiscovery
from chatxz.core.peer_probe import avg_ms, register_probe_ack, rolling_avg_ms


class PeerProbeTests(unittest.TestCase):
    def test_rolling_average(self):
        samples = rolling_avg_ms([], 120)
        samples = rolling_avg_ms(samples, 80)
        self.assertEqual(avg_ms(samples), 100)

    def test_register_probe_ack(self):
        import threading
        event = threading.Event()
        from chatxz.core import peer_probe
        with peer_probe._pending_lock:
            peer_probe._pending_probes["abc"] = {"event": event, "rtt_ms": None, "ts": time.time()}
        ok = register_probe_ack("abc", 42)
        self.assertTrue(ok)

    def test_purge_stale_probes_on_high_rtt_requires_samples(self):
        disc = PeerDiscovery()
        disc.peers["a" * 32] = {
            "hash": "a" * 32,
            "via": "rns",
            "ip": "10.10.10.2",
            "last_seen": time.time() - 60,
            "rtt_avg_ms": 12000,
            "rtt_samples": [12000, 11000, 13000],
            "last_probe_ok": time.time() - 60,
            "probe_failures": 0,
        }
        removed = disc.purge_stale_probes()
        self.assertEqual(removed, 1)

    def test_serial_peers_never_probe_evicted(self):
        disc = PeerDiscovery()
        disc.peers["b" * 32] = {
            "hash": "b" * 32,
            "via": "serial",
            "last_seen": time.time() - 120,
            "probe_failures": 99,
        }
        removed = disc.purge_stale_probes()
        self.assertEqual(removed, 0)

    def test_announce_refresh_resets_probe_failures(self):
        disc = PeerDiscovery()
        disc.accept_peers = True
        disc.peers["c" * 32] = {
            "hash": "c" * 32,
            "via": "rns",
            "ip": "10.10.10.3",
            "last_seen": time.time(),
            "probe_failures": 4,
        }
        disc.reset_peer_probe_state("c" * 32)
        self.assertEqual(disc.peers["c" * 32]["probe_failures"], 0)

    def test_update_peer_probe_records_rtt(self):
        disc = PeerDiscovery()
        disc.peers["b" * 32] = {
            "hash": "b" * 32,
            "via": "serial",
            "last_seen": time.time() - 30,
        }
        disc.update_peer_probe("b" * 32, rtt_ms=85, ok=True)
        peer = disc.peers["b" * 32]
        self.assertEqual(peer.get("rtt_ms"), 85)
        self.assertEqual(peer.get("rtt_avg_ms"), 85)


if __name__ == "__main__":
    unittest.main()