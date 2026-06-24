"""Tests for dual-path serial failover helpers."""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from chatxz.core import rns_interfaces as ri


class SerialConfigTests(unittest.TestCase):
    def test_configured_serial_enabled_ignores_stale_enabled_flag(self):
        interfaces = [
            {
                "id": "s1",
                "preset": "serial",
                "type": "SerialInterface",
                "port": "/dev/ttyUSB0",
                "enabled": False,
            }
        ]
        with patch.object(ri, "serial_runtime_active", return_value=True):
            self.assertTrue(ri.configured_serial_enabled(interfaces))

    def test_render_includes_serial_when_port_accessible(self):
        interfaces = [
            {
                "id": "s1",
                "preset": "serial",
                "type": "SerialInterface",
                "port": "/dev/ttyUSB0",
                "speed": 57600,
            }
        ]
        with patch.object(ri, "serial_runtime_active", return_value=True):
            text = ri.render_rns_config(interfaces, broadcast_ip="10.0.30.255", log=None)
        self.assertIn("type = SerialInterface", text)
        self.assertIn("port = /dev/ttyUSB0", text)
        self.assertNotIn("hot-add at runtime", text)

    def test_render_skips_serial_when_port_missing(self):
        interfaces = [
            {
                "id": "s1",
                "preset": "serial",
                "type": "SerialInterface",
                "port": "/dev/ttyUSB0",
            }
        ]
        with patch.object(ri, "serial_runtime_active", return_value=False):
            with patch.object(ri, "serial_skip_reason", return_value=("/dev/ttyUSB0", "not connected")):
                text = ri.render_rns_config(interfaces, broadcast_ip="10.0.30.255", log=None)
        self.assertNotIn("type = SerialInterface", text)


if __name__ == "__main__":
    unittest.main()