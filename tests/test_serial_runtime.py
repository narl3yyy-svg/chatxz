"""Serial runtime identity, announce isolation, and self-hash filtering."""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from chatxz.core.discovery import PeerDiscovery
from chatxz.core.messaging import MessagingBackend


class SerialRuntimeTests(unittest.TestCase):
    def test_ensure_serial_runtime_creates_destination(self):
        tmp = tempfile.mkdtemp()
        backend = MessagingBackend(
            MagicMock(),
            tmp,
            dual_identity_mode=True,
        )
        backend.destination = MagicMock()
        backend.running = True
        with patch.object(
            backend, "_setup_inbound_destination", side_effect=lambda ident, attr: MagicMock(hash=bytes.fromhex("aa" * 16))
        ):
            ok = backend.ensure_serial_runtime()
        self.assertTrue(ok)
        self.assertIsNotNone(backend.identity_serial)
        self.assertIsNotNone(backend.destination_serial)

    def test_announce_on_serial_skips_without_serial_destination(self):
        backend = MessagingBackend(MagicMock(), tempfile.mkdtemp(), dual_identity_mode=True)
        serial_iface = MagicMock()
        with patch("chatxz.core.messaging.is_serial_interface", return_value=True):
            with patch.object(backend, "ensure_serial_runtime", return_value=False):
                self.assertFalse(backend._announce_on_interface(serial_iface))

    def test_discovery_filters_local_serial_hash(self):
        disc = PeerDiscovery()
        disc.accept_peers = True
        local_serial = "d0fdd4b95fbdeabdd68aa2029f38a492"
        local_lan = "1ae22165b22894bfbb211c42a335ab3e"
        disc.set_local_hashes(local_lan, local_serial)
        with patch.object(disc, "_peer_allowed", return_value=True):
            with patch.object(disc, "_sanitize_peer_scope", side_effect=lambda p: p):
                disc._store_peer({
                    "hash": local_serial,
                    "name": "Arch",
                    "via": "serial",
                    "last_seen": 1,
                })
        self.assertFalse(disc.has_peer_hash(local_serial))


if __name__ == "__main__":
    unittest.main()