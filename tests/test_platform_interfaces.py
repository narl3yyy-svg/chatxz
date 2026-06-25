"""Tests for LAN/VPN network interface enumeration."""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from chatxz.utils import platform as plat


class LinuxInterfaceHelpers(unittest.TestCase):
    def test_skip_container_not_vpn(self):
        self.assertTrue(plat._linux_skip_iface("veth123"))
        self.assertTrue(plat._linux_skip_iface("docker0"))
        self.assertFalse(plat._linux_skip_iface("wg0"))
        self.assertFalse(plat._linux_skip_iface("tun0"))
        self.assertFalse(plat._linux_skip_iface("tailscale0"))
        self.assertFalse(plat._linux_skip_iface("enp2s0"))

    def test_tunnel_detection_by_name(self):
        for name in ("wg0", "tun0", "tap0", "ppp0", "tailscale0", "nordlynx", "zt0"):
            self.assertTrue(plat._linux_is_tunnel_iface(name), name)
        self.assertFalse(plat._linux_is_tunnel_iface("enp2s0"))
        self.assertFalse(plat._linux_is_tunnel_iface("wlo1"))

    def test_auto_priority_prefers_ethernet_over_vpn(self):
        self.assertGreater(
            plat._linux_iface_auto_priority("enp2s0", "10.0.30.112"),
            plat._linux_iface_auto_priority("wg0", "10.0.30.112"),
        )

    def test_enumerate_includes_tunnel_when_present(self):
        with patch.object(plat, "is_android", return_value=False):
            with patch("os.listdir", return_value=["lo", "enp2s0", "wg0", "veth0"]):
                with patch.object(plat, "_linux_iface_entry") as mock_entry:
                    mock_entry.side_effect = lambda n: {
                        "name": n,
                        "kind": "vpn" if n == "wg0" else "ethernet",
                        "ip": "10.0.0.1" if n != "lo" else "disconnected",
                        "broadcast": None,
                        "subnet_broadcast": None,
                        "up": n != "lo",
                    }
                    names = [e["name"] for e in plat.enumerate_lan_interfaces()]
        self.assertIn("enp2s0", names)
        self.assertIn("wg0", names)
        self.assertNotIn("lo", names)
        self.assertNotIn("veth0", names)

    def test_pinned_vpn_ip_resolution(self):
        plat.set_lan_interface_preference("wg0")
        try:
            with patch.object(plat, "is_android", return_value=False):
                with patch.object(plat, "_linux_skip_iface", return_value=False):
                    with patch.object(plat, "_linux_is_tunnel_iface", return_value=True):
                        with patch.object(plat, "_linux_iface_ipv4", return_value="100.64.0.2"):
                            with patch.object(plat, "_linux_iface_link_up", return_value=False):
                                self.assertEqual(plat.lan_ip(), "100.64.0.2")
        finally:
            plat.set_lan_interface_preference(None)


    def test_physical_lan_skips_vpn(self):
        with patch.object(plat, "is_android", return_value=False):
            with patch.object(plat, "_linux_enumerate_interfaces") as mock_enum:
                mock_enum.return_value = [
                    {"name": "wg0", "kind": "vpn", "ip": "10.10.100.12", "up": True},
                    {"name": "enp2s0", "kind": "ethernet", "ip": "disconnected", "up": False},
                ]
                self.assertFalse(plat.physical_lan_reachable())
                mock_enum.return_value[1]["ip"] = "10.0.30.112"
                mock_enum.return_value[1]["up"] = True
                self.assertTrue(plat.physical_lan_reachable())


class LanInterfaceValueParsing(unittest.TestCase):
    def test_parse_name_ip_pair(self):
        name, ip = plat.parse_lan_interface_value("Ethernet 2|10.0.47.37")
        self.assertEqual(name, "Ethernet 2")
        self.assertEqual(ip, "10.0.47.37")

    def test_parse_bare_ip(self):
        name, ip = plat.parse_lan_interface_value("192.168.1.5")
        self.assertEqual(name, "")
        self.assertEqual(ip, "192.168.1.5")

    def test_parse_bare_nic_name(self):
        name, ip = plat.parse_lan_interface_value("wg0")
        self.assertEqual(name, "wg0")
        self.assertEqual(ip, "")

    def test_format_lan_interface_value(self):
        self.assertEqual(
            plat.format_lan_interface_value("Ethernet", "10.0.0.1"),
            "Ethernet|10.0.0.1",
        )


class WindowsInterfaceHelpers(unittest.TestCase):
    def test_windows_enumerate_parses_ipconfig(self):
        ipconfig = (
            "Ethernet adapter Ethernet 2:\r\n"
            "\r\n"
            "   IPv4 Address. . . . . . . . . . . : 10.0.47.37\r\n"
            "   Subnet Mask . . . . . . . . . . . : 255.255.255.0\r\n"
            "\r\n"
            "Ethernet adapter Tailscale:\r\n"
            "\r\n"
            "   IPv4 Address. . . . . . . . . . . : 100.64.0.2\r\n"
        )
        route = "0.0.0.0          10.0.47.1      10.0.47.37     25"

        def fake_run(cmd, *args, **kwargs):
            result = type("R", (), {"stdout": "", "returncode": 0})()
            if cmd and cmd[0] == "ipconfig":
                result.stdout = ipconfig
            elif cmd and cmd[0] == "route" and len(cmd) >= 2 and cmd[1] == "print":
                result.stdout = route
            return result

        with patch.object(plat.subprocess, "run", side_effect=fake_run):
            entries = plat._windows_enumerate_interfaces_ipconfig()
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["ip"], "10.0.47.37")
        self.assertEqual(entries[0]["broadcast"], "10.0.47.255")
        self.assertTrue(entries[0]["gateway_iface"])
        self.assertEqual(entries[1]["kind"], "vpn")

    def test_desktop_interface_cache_reuses_results(self):
        plat.invalidate_desktop_interface_cache()
        calls = {"n": 0}

        def fake_enum():
            calls["n"] += 1
            return [{"name": "eth0", "kind": "ethernet", "ip": "10.0.0.1", "up": True}]

        with patch.object(plat, "_desktop_enumerate_interfaces_uncached", side_effect=fake_enum):
            with patch.object(plat.sys, "platform", "win32"):
                plat._desktop_enumerate_interfaces()
                plat._desktop_enumerate_interfaces()
        self.assertEqual(calls["n"], 1)
        plat.invalidate_desktop_interface_cache()

    def test_desktop_lan_ip_prefers_gateway_interface(self):
        entries = [
            {"name": "Tailscale", "kind": "vpn", "ip": "100.64.0.2", "up": True},
            {
                "name": "Ethernet 2",
                "kind": "ethernet",
                "ip": "10.0.47.37",
                "up": True,
                "gateway_iface": True,
            },
            {
                "name": "Ethernet 2",
                "kind": "ethernet",
                "ip": "192.168.1.37",
                "up": True,
                "gateway_iface": False,
            },
        ]
        with patch.object(plat, "get_lan_interface_preference", return_value=None):
            with patch.object(plat, "_desktop_enumerate_interfaces", return_value=entries):
                self.assertEqual(plat._desktop_lan_ip(), "10.0.47.37")

    def test_windows_merge_keeps_all_ipv4_on_same_adapter(self):
        ipconfig = (
            "Ethernet adapter Ethernet 2:\r\n"
            "\r\n"
            "   IPv4 Address. . . . . . . . . . . : 10.0.47.37\r\n"
            "   IPv4 Address. . . . . . . . . . . : 192.168.1.37\r\n"
        )
        ps_entries = [
            {"name": "Ethernet 2", "ip": "10.0.47.37", "up": True, "gateway_iface": True},
            {"name": "Ethernet 2", "ip": "192.168.1.37", "up": True, "gateway_iface": False},
        ]

        def fake_run(cmd, *args, **kwargs):
            result = type("R", (), {"stdout": "", "returncode": 0})()
            if cmd and cmd[0] == "ipconfig":
                result.stdout = ipconfig
            return result

        with patch.object(plat.subprocess, "run", side_effect=fake_run):
            with patch.object(plat, "_windows_enumerate_interfaces_powershell", return_value=ps_entries):
                entries = plat._windows_enumerate_interfaces()
        ips = sorted(e["ip"] for e in entries)
        self.assertEqual(ips, ["10.0.47.37", "192.168.1.37"])

    def test_pinned_ipv4_resolution(self):
        plat.set_lan_interface_preference("Ethernet 2|192.168.1.37")
        try:
            entries = [
                {
                    "name": "Ethernet 2",
                    "kind": "ethernet",
                    "ip": "10.0.47.37",
                    "up": True,
                    "gateway_iface": True,
                },
                {
                    "name": "Ethernet 2",
                    "kind": "ethernet",
                    "ip": "192.168.1.37",
                    "up": True,
                    "gateway_iface": False,
                },
            ]
            with patch.object(plat, "_desktop_enumerate_interfaces", return_value=entries):
                self.assertEqual(plat._desktop_lan_ip(), "192.168.1.37")
                filtered = plat._filter_interfaces_for_lan(entries)
                self.assertEqual(len(filtered), 1)
                self.assertEqual(filtered[0]["ip"], "192.168.1.37")
        finally:
            plat.set_lan_interface_preference(None)

    def test_physical_lan_true_on_windows_entries(self):
        entries = [
            {
                "name": "Ethernet 2",
                "kind": "ethernet",
                "ip": "10.0.47.37",
                "up": True,
                "gateway_iface": True,
            },
        ]
        with patch.object(plat, "is_android", return_value=False):
            with patch.object(plat.sys, "platform", "win32"):
                with patch.object(plat, "_desktop_enumerate_interfaces", return_value=entries):
                    self.assertTrue(plat.physical_lan_reachable())
                    self.assertTrue(plat.lan_connected())


class DarwinInterfaceHelpers(unittest.TestCase):
    def test_darwin_enumerate_parses_ifconfig(self):
        ifconfig = (
            "en0: flags=8863<UP,BROADCAST,SMART,RUNNING,SIMPLEX,MULTICAST> mtu 1500\n"
            "\toptions=6460<TSO4,TSO6,CHANNEL_IO>\n"
            "\tether aa:bb:cc:dd:ee:ff\n"
            "\tinet 192.168.1.42 netmask 0xffffff00 broadcast 192.168.1.255\n"
            "\tmedia: autoselect\n"
            "\tstatus: active\n"
            "utun4: flags=8051<UP,POINTOPOINT,RUNNING,MULTICAST> mtu 1380\n"
            "\tinet 100.64.0.2 --> 100.64.0.2 netmask 0xffffffff\n"
        )

        def fake_run(cmd, *args, **kwargs):
            result = type("R", (), {"stdout": "", "returncode": 0})()
            if cmd and cmd[0] == "ifconfig":
                result.stdout = ifconfig
            return result

        with patch.object(plat.subprocess, "run", side_effect=fake_run):
            entries = plat._darwin_enumerate_interfaces()
        by_name = {e["name"]: e for e in entries}
        self.assertEqual(by_name["en0"]["ip"], "192.168.1.42")
        self.assertTrue(by_name["en0"]["up"])
        self.assertEqual(by_name["en0"]["broadcast"], "192.168.1.255")
        self.assertEqual(by_name["utun4"]["ip"], "100.64.0.2")
        self.assertTrue(by_name["utun4"]["up"])
        self.assertEqual(by_name["utun4"]["kind"], "vpn")

    def test_physical_lan_true_on_darwin_entries(self):
        entries = [
            {
                "name": "en0",
                "kind": "ethernet",
                "ip": "192.168.1.42",
                "up": True,
                "broadcast": "192.168.1.255",
            },
        ]
        with patch.object(plat, "is_android", return_value=False):
            with patch.object(plat.sys, "platform", "darwin"):
                with patch.object(plat, "_desktop_enumerate_interfaces", return_value=entries):
                    self.assertTrue(plat.physical_lan_reachable())
                    self.assertTrue(plat.lan_connected())
                    self.assertEqual(plat._desktop_lan_ip(), "192.168.1.42")


if __name__ == "__main__":
    unittest.main()