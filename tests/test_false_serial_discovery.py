"""False serial discovery rows must not appear for LAN-only peers."""

import os
import sys
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from chatxz.core.discovery import PeerDiscovery


class FalseSerialDiscoveryTests(unittest.TestCase):
    def test_beacon_drops_unverified_serial_row(self):
        disc = PeerDiscovery()
        disc.running = True
        disc.accept_peers = True
        lan_hash = "6701ddedc5192d61671b9fe645df2079"
        disc.peers[f"{lan_hash}:serial"] = {
            "hash": lan_hash,
            "name": "GZ16",
            "via": "serial",
            "last_seen": time.time(),
        }
        data = {
            "app": "chatxz",
            "hash": lan_hash,
            "identity_hash": "a" * 32,
            "name": "GZ16",
            "ip": "10.0.30.114",
            "port": 8742,
            "pubkey": "dGVzdA==",
        }
        with patch("chatxz.core.discovery.PeerDiscovery._scope_ip", return_value=None):
            with patch("chatxz.core.peer_identity.peer_record_from_beacon") as rec:
                rec.return_value = {
                    "hash": lan_hash,
                    "name": "GZ16",
                    "via": "beacon",
                    "ip": "10.0.30.114",
                }
                with patch("chatxz.core.discovery.register_identity_from_beacon", return_value=True):
                    disc._on_beacon(data, "b" * 32, source_ip="10.0.30.114")
        self.assertNotIn(f"{lan_hash}:serial", disc.peers)
        peers = disc.get_peers()
        serial_rows = [p for p in peers if (p.get("via") or "") == "serial"]
        self.assertEqual(serial_rows, [])

    def test_get_peers_hides_phantom_serial_when_lan_row_exists(self):
        disc = PeerDiscovery()
        disc.accept_peers = True
        lan_hash = "abcabcabcabcabcabcabcabcabcabc"
        now = time.time()
        disc.peers[f"{lan_hash}:lan"] = {
            "hash": lan_hash,
            "name": "GZ16",
            "via": "rns",
            "ip": "10.0.30.114",
            "last_seen": now,
        }
        disc.peers[f"{lan_hash}:serial"] = {
            "hash": lan_hash,
            "name": "GZ16",
            "via": "serial",
            "last_seen": now,
        }
        with patch("chatxz.core.discovery.serial_discovery_active", return_value=True):
            peers = disc.get_peers()
        serial_rows = [p for p in peers if (p.get("via") or "") == "serial"]
        self.assertEqual(serial_rows, [])
        self.assertEqual(len(peers), 1)


if __name__ == "__main__":
    unittest.main()