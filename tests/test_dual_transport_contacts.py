"""Dual-transport contact persistence and discovery eviction."""

import os
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from chatxz.core.contacts import (
    contact_has_hash,
    find_contact_by_hash,
    migrate_contact_hash,
    save_contact,
    update_contact_transport_hash,
)
from chatxz.core.discovery import PeerDiscovery


class DualTransportDiscoveryTests(unittest.TestCase):
    def test_serial_announce_does_not_evict_lan_peer_same_name(self):
        disc = PeerDiscovery()
        disc.accept_peers = True
        lan_hash = "5386ea6054eaaa291518c47732e85127"
        serial_hash = "3e212832f1b629ac1bf1442bace4c472"
        disc.peers[f"{lan_hash}:lan"] = {
            "hash": lan_hash,
            "name": "330s",
            "ip": "10.0.30.101",
            "port": 8742,
            "last_seen": time.time(),
            "via": "rns",
        }
        with patch("chatxz.core.discovery.serial_discovery_active", return_value=True):
            disc._store_peer({
                "hash": serial_hash,
                "name": "330s",
                "last_seen": time.time(),
                "via": "serial",
            })
        self.assertTrue(disc.has_peer_hash(lan_hash))
        self.assertTrue(disc.has_peer_hash(serial_hash))
        self.assertEqual(len(disc.peers), 2)


class DualTransportContactTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        save_contact(
            self.tmp,
            "5386ea6054eaaa291518c47732e85127",
            name="ubuntu",
            ip="10.0.30.101",
            via="lan",
        )
        save_contact(
            self.tmp,
            "3e212832f1b629ac1bf1442bace4c472",
            name="ubuntu",
            via="serial",
        )

    def test_dual_hash_contact_persists_both_transports(self):
        contact = find_contact_by_hash(self.tmp, "5386ea6054eaaa291518c47732e85127")
        self.assertIsNotNone(contact)
        self.assertEqual(contact.get("lan_hash"), "5386ea6054eaaa291518c47732e85127")
        self.assertEqual(contact.get("serial_hash"), "3e212832f1b629ac1bf1442bace4c472")

    def test_migrate_lan_hash_preserves_serial_hash(self):
        migrate_contact_hash(
            self.tmp,
            "5386ea6054eaaa291518c47732e85127",
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            via="rns",
            ip="10.0.30.101",
        )
        contact = find_contact_by_hash(self.tmp, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        self.assertIsNotNone(contact)
        self.assertEqual(contact.get("serial_hash"), "3e212832f1b629ac1bf1442bace4c472")
        self.assertFalse(contact_has_hash(self.tmp, "5386ea6054eaaa291518c47732e85127"))

    def test_update_serial_hash_preserves_lan_hash(self):
        update_contact_transport_hash(
            self.tmp,
            "3e212832f1b629ac1bf1442bace4c472",
            "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            via="serial",
        )
        contact = find_contact_by_hash(self.tmp, "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")
        self.assertIsNotNone(contact)
        self.assertEqual(contact.get("lan_hash"), "5386ea6054eaaa291518c47732e85127")
        self.assertEqual(contact.get("serial_hash"), "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")


if __name__ == "__main__":
    unittest.main()