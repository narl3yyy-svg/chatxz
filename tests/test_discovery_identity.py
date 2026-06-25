"""Tests for discovery TTL and identity supersession."""

import os
import sys
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from chatxz.core.discovery import PeerDiscovery, discovery_timeout_s


class DiscoveryIdentityTests(unittest.TestCase):
    def test_desktop_discovery_ttl_is_30_seconds(self):
        with patch("chatxz.utils.platform.is_android", return_value=False):
            self.assertEqual(discovery_timeout_s(), 30)

    def test_evict_superseded_peer_on_same_ip_new_hash(self):
        disc = PeerDiscovery()
        disc.accept_peers = True
        disc.peers["oldhash123456789012345678901234"] = {
            "hash": "oldhash123456789012345678901234",
            "name": "ubuntu",
            "ip": "10.0.30.101",
            "port": 8742,
            "last_seen": time.time(),
            "via": "beacon",
        }
        disc._store_peer({
            "hash": "newhash123456789012345678901234",
            "name": "ubuntu",
            "ip": "10.0.30.101",
            "port": 8742,
            "last_seen": time.time(),
            "via": "beacon",
        })
        self.assertEqual(len(disc.peers), 1)
        self.assertIn("newhash123456789012345678901234", disc.peers)

    def test_purge_hashes_removes_matching_entries(self):
        disc = PeerDiscovery()
        disc.peers["deadbeefdeadbeefdeadbeefdeadbeef"] = {
            "hash": "deadbeefdeadbeefdeadbeefdeadbeef",
            "identity_hash": "cafebabecafebabecafebabecafebabe",
            "last_seen": time.time(),
        }
        removed = disc.purge_hashes({
            "deadbeefdeadbeefdeadbeefdeadbeef",
            "cafebabecafebabecafebabecafebabe",
        })
        self.assertEqual(removed, 1)
        self.assertEqual(len(disc.peers), 0)

    def test_stale_peer_pruned_after_ttl(self):
        disc = PeerDiscovery()
        disc.accept_peers = True
        disc.peers["abcdabcdabcdabcdabcdabcdabcdabcd"] = {
            "hash": "abcdabcdabcdabcdabcdabcdabcdabcd",
            "name": "peer",
            "last_seen": time.time() - 45,
            "via": "rns",
        }
        peers = disc.get_peers()
        self.assertEqual(peers, [])


if __name__ == "__main__":
    unittest.main()