"""Tests for dual-transport RNS isolation."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from chatxz.core.transport_isolation import (
    _filter_interfaces,
    apply_transport_isolation,
    dual_transport_isolation_enabled,
    families_compatible,
)


class TransportIsolationTests(unittest.TestCase):
    def test_families_compatible_blocks_serial_lan_bridge(self):
        self.assertFalse(families_compatible("serial", "udp"))
        self.assertFalse(families_compatible("udp", "serial"))
        self.assertTrue(families_compatible("udp", "tcp"))
        self.assertTrue(families_compatible("serial", "serial"))

    def test_dual_transport_requires_serial_and_lan(self):
        serial = MagicMock()
        with patch("chatxz.core.transport_isolation.serial_interface_online", return_value=serial):
            with patch("chatxz.core.transport_isolation.online_interfaces", return_value=[]):
                self.assertFalse(dual_transport_isolation_enabled())
            with patch("chatxz.core.transport_isolation.online_interfaces", return_value=[MagicMock()]):
                self.assertTrue(dual_transport_isolation_enabled())

    def test_filter_interfaces_blocks_cross_zone_forwarding(self):
        serial_iface = MagicMock()
        udp_iface = MagicMock()
        with patch(
            "chatxz.core.transport_isolation.dual_transport_isolation_enabled",
            return_value=True,
        ):
            with patch(
                "chatxz.core.transport_isolation.interface_family",
                side_effect=lambda i: "serial" if i is serial_iface else "udp",
            ):
                filtered = _filter_interfaces(
                    serial_iface, [serial_iface, udp_iface]
                )
        self.assertEqual(filtered, [])

    def test_apply_transport_isolation_patches_path_request(self):
        import RNS.Transport as Transport
        import chatxz.core.transport_isolation as ti

        original = Transport.path_request
        ti._patched = False
        try:
            apply_transport_isolation()
            self.assertTrue(ti._patched)
            self.assertIsNot(Transport.path_request, original)
            apply_transport_isolation()
            self.assertTrue(ti._patched)
        finally:
            Transport.path_request = original
            ti._patched = False


if __name__ == "__main__":
    unittest.main()