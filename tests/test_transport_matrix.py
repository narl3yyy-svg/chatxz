"""Broad transport/discovery matrix — sender/receiver, RTT, scope, identity, 3-device."""

import itertools
import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from chatxz.core.discovery import PeerDiscovery, normalize_hash
from chatxz.core.messaging import MessagingBackend
from chatxz.utils.lan_scope import peer_in_scope, same_lan_scope

ARCH = "436ce5fd79d0932dc10b24da54a180f8"
UBUNTU = "f1c2ac9061239f7c096701f02969729c"
WINDOWS = "87a012c46dc2274afccae6fe597b8675"

DEVICE_IPS = {
    "arch": ("10.10.10.37", "10.0.30.112"),
    "ubuntu": ("10.0.5.10", "10.0.30.101"),
    "windows": ("10.10.10.2",),
}

SCOPE_IPS = ("10.10.10.37", "10.0.30.112", "10.0.5.10", "10.10.10.2")
RTT_MS = (1, 5, 12, 45, 120, 500, 2000, 8000)


class _FakeIdentity:
    def __init__(self, ident_hex):
        self.hash = bytes.fromhex(ident_hex)


def _messaging(resolver=None):
    backend = MessagingBackend(
        identity=_FakeIdentity("a" * 32),
        config_dir="/tmp/chatxz-matrix",
        peer_transport_resolver=resolver,
    )
    backend.running = True
    backend.my_dest_hash = "b" * 32
    return backend


class SerialOfflineDiscoveryTests(unittest.TestCase):
    def test_get_peers_hides_serial_when_usb_offline(self):
        disc = PeerDiscovery()
        disc.accept_peers = True
        disc.peers[UBUNTU] = {
            "hash": UBUNTU,
            "name": "ubuntu",
            "via": "serial",
            "last_seen": time.time(),
        }
        disc.peers[WINDOWS] = {
            "hash": WINDOWS,
            "name": "13600k",
            "via": "rns",
            "ip": "10.10.10.2",
            "last_seen": time.time(),
        }
        with patch("chatxz.core.discovery.serial_discovery_active", return_value=False):
            peers = disc.get_peers(scope_ip="10.10.10.37")
        hashes = {p.get("hash") for p in peers}
        self.assertNotIn(UBUNTU, hashes)
        self.assertIn(WINDOWS, hashes)

    def test_beacon_upgrades_serial_peer_when_usb_offline(self):
        disc = PeerDiscovery()
        disc.running = True
        disc.accept_peers = True
        disc.peers[UBUNTU] = {
            "hash": UBUNTU,
            "name": "ubuntu",
            "via": "serial",
            "last_seen": time.time(),
        }
        beacon = {
            "app": "chatxz",
            "hash": UBUNTU,
            "name": "ubuntu",
            "ip": "10.0.30.101",
            "port": 8742,
            "identity_hash": "c" * 32,
            "pubkey": "dGVzdA==",
        }
        with patch("chatxz.core.discovery.serial_discovery_active", return_value=False):
            with patch("chatxz.utils.platform.discovery_scope_ip", return_value="10.0.30.112"):
                with patch("chatxz.core.peer_identity.peer_record_from_beacon") as rec:
                    rec.return_value = {
                        "hash": UBUNTU,
                        "name": "ubuntu",
                        "via": "beacon",
                        "ip": "10.0.30.101",
                    }
                    ok = disc._on_beacon(
                        beacon, my_dest_hash=ARCH, source_ip="10.0.30.101",
                    )
        self.assertTrue(ok)
        lan_key = PeerDiscovery._peer_storage_key({
            "hash": UBUNTU,
            "via": "rns",
        })
        peer = disc.peers.get(lan_key)
        self.assertIsNotNone(peer)
        self.assertIn(peer.get("via"), ("rns", "beacon"))
        self.assertEqual(peer.get("ip"), "10.0.30.101")

    def test_purge_offline_serial_peers(self):
        disc = PeerDiscovery()
        disc.peers[UBUNTU] = {"hash": UBUNTU, "via": "serial", "last_seen": time.time()}
        with patch("chatxz.core.discovery.serial_discovery_active", return_value=False):
            removed = disc.purge_offline_serial_peers()
        self.assertEqual(removed, 1)
        self.assertNotIn(UBUNTU, disc.peers)


class TransportFamilyMatrixTests(unittest.TestCase):
    def test_expected_transport_matrix(self):
        cases = []
        for usb_up, via, ip, scope, has_serial_path in itertools.product(
            (True, False),
            ("serial", "rns", "beacon"),
            ("", "10.10.10.2", "10.0.5.10", "10.0.30.101"),
            ("10.10.10.37", "10.0.30.112"),
            (True, False),
        ):
            cases.append((usb_up, via, ip, scope, has_serial_path))

        for usb_up, via, ip, scope, has_serial_path in cases:
            with self.subTest(usb=usb_up, via=via, ip=ip, scope=scope, path=has_serial_path):
                resolver = lambda _h, v=via, i=ip: {
                    "hash": UBUNTU,
                    "via": v,
                    "ip": i,
                }
                backend = _messaging(resolver)
                with patch(
                    "chatxz.core.messaging.serial_interface_online",
                    return_value=MagicMock() if usb_up else None,
                ):
                    with patch.object(
                        backend,
                        "_peer_has_path_on_family",
                        side_effect=lambda _p, fam: fam == "serial" and has_serial_path,
                    ):
                        with patch.object(
                            backend,
                            "_peer_lan_ip_usable",
                            side_effect=lambda candidate: bool(
                                candidate and peer_in_scope(candidate, scope)
                            ),
                        ):
                            with patch.object(backend, "_lan_transport_ready", return_value=True):
                                expected = backend._peer_expected_transport_families(UBUNTU)

                if via == "serial" and not usb_up:
                    self.assertNotEqual(expected, {"serial"})
                elif via == "serial" and usb_up:
                    self.assertEqual(expected, {"serial"})
                elif ip and peer_in_scope(ip, scope):
                    self.assertTrue(expected & {"udp", "lan", "tcp"})


class LanScopeMatrixTests(unittest.TestCase):
    def test_scope_pairs(self):
        for local, remote in itertools.product(SCOPE_IPS, SCOPE_IPS):
            with self.subTest(local=local, remote=remote):
                in_scope = same_lan_scope(local, remote)
                disc = PeerDiscovery()
                disc.accept_peers = True
                peer_hash = normalize_hash(f"{local}{remote}"[:32].ljust(32, "a"))
                with patch("chatxz.core.discovery.serial_discovery_active", return_value=False):
                    with patch.object(disc, "_scope_ip", return_value=local):
                        ok = disc._store_peer({
                            "hash": peer_hash,
                            "ip": remote,
                            "name": "peer",
                            "via": "rns",
                            "last_seen": time.time(),
                        })
                if in_scope:
                    self.assertTrue(ok or peer_hash in disc.peers)
                else:
                    self.assertFalse(ok)
                    self.assertNotIn(peer_hash, disc.peers)


class RttProbeMatrixTests(unittest.TestCase):
    def test_rtt_rolling_average(self):
        from chatxz.core.peer_probe import avg_ms, rolling_avg_ms

        disc = PeerDiscovery()
        disc.accept_peers = True
        for start_rtt in RTT_MS:
            for burst in (1, 3, 5, 10):
                with self.subTest(start=start_rtt, burst=burst):
                    disc.peers.clear()
                    entry = {
                        "hash": UBUNTU,
                        "via": "rns",
                        "ip": "10.10.10.2",
                        "last_seen": time.time(),
                        "rtt_samples": [],
                    }
                    key = PeerDiscovery._peer_storage_key(entry)
                    disc.peers[key] = dict(entry)
                    samples = []
                    for i in range(burst):
                        rtt = start_rtt + i * 3
                        samples = rolling_avg_ms(samples, rtt)
                        disc.update_peer_probe(UBUNTU, rtt_ms=rtt, ok=True)
                    peer = disc.peers[key]
                    self.assertEqual(peer["rtt_samples"], samples)
                    self.assertEqual(peer["rtt_avg_ms"], avg_ms(samples))
                    self.assertGreaterEqual(peer["rtt_avg_ms"], start_rtt)


class ThreeDeviceMatrixTests(unittest.TestCase):
    """3-device connect/disconnect permutations (Arch, Ubuntu, Windows)."""

    def test_discovery_dedup_three_devices(self):
        disc = PeerDiscovery()
        disc.accept_peers = True
        now = time.time()
        devices = [
            (ARCH, "arch", "10.10.10.37", "rns"),
            (UBUNTU, "ubuntu", "", "serial"),
            (WINDOWS, "13600k", "10.10.10.2", "rns"),
        ]
        for order in itertools.permutations(range(3)):
            with self.subTest(order=order):
                disc.peers.clear()
                for idx in order:
                    h, name, ip, via = devices[idx]
                    entry = {
                        "hash": h,
                        "name": name,
                        "via": via,
                        "last_seen": now + idx,
                    }
                    if ip:
                        entry["ip"] = ip
                    disc.peers[h] = entry
                with patch("chatxz.core.discovery.serial_discovery_active", return_value=True):
                    peers = disc.get_peers(scope_ip="10.10.10.37")
                names = {p.get("name") for p in peers}
                self.assertIn("arch", names)
                self.assertIn("13600k", names)
                self.assertIn("ubuntu", names)

    def test_three_device_transport_isolation(self):
        resolver = lambda h: {
            "hash": h,
            "via": "serial" if h == UBUNTU else "rns",
            "ip": "10.10.10.2" if h == WINDOWS else "",
        }
        backend = _messaging(resolver)
        serial_link = MagicMock()
        serial_link.attached_interface = MagicMock()
        udp_link = MagicMock()
        udp_link.attached_interface = MagicMock()

        for target, link, fam in (
            (UBUNTU, serial_link, "serial"),
            (WINDOWS, udp_link, "udp"),
            (UBUNTU, udp_link, "udp"),
            (WINDOWS, serial_link, "serial"),
        ):
            with self.subTest(target=target[:8], fam=fam):
                with patch("chatxz.core.messaging.serial_interface_online", return_value=MagicMock()):
                    with patch.object(backend, "_peer_lan_ip_usable", return_value=True):
                        with patch(
                            "chatxz.core.messaging.interface_family",
                            side_effect=lambda i: fam if i else "",
                        ):
                            ok = backend._link_acceptable_for_peer(link, target)
                if target == UBUNTU and fam == "serial":
                    self.assertTrue(ok)
                if target == UBUNTU and fam == "udp":
                    self.assertFalse(ok)
                if target == WINDOWS and fam == "udp":
                    self.assertTrue(ok)
                if target == WINDOWS and fam == "serial":
                    self.assertFalse(ok)


class SenderReceiverMatrixTests(unittest.TestCase):
    """Bidirectional sender (S) / receiver (R) transport expectations."""

    def test_bidirectional_transport_expectations(self):
        transports = ("serial", "lan")
        usb_states = (True, False)
        for s_transport, r_usb, r_transport in itertools.product(
            transports, usb_states, transports
        ):
            with self.subTest(s=s_transport, r_usb=r_usb, r=r_transport):
                via = "serial" if r_transport == "serial" else "rns"
                ip = "" if r_transport == "serial" else "10.0.30.101"
                resolver = lambda _h, v=via, i=ip: {
                    "hash": UBUNTU,
                    "via": v,
                    "ip": i,
                }
                backend = _messaging(resolver)
                with patch(
                    "chatxz.core.messaging.serial_interface_online",
                    return_value=MagicMock() if r_usb else None,
                ):
                    with patch.object(backend, "_lan_transport_ready", return_value=True):
                        expected = backend._peer_expected_transport_families(UBUNTU)
                if r_transport == "serial" and r_usb:
                    self.assertEqual(expected, {"serial"})
                elif r_transport == "serial" and not r_usb:
                    self.assertNotEqual(expected, {"serial"})
                elif r_transport == "lan":
                    self.assertTrue(
                        not expected
                        or bool(expected & {"udp", "lan", "tcp"})
                    )


class IdentityDisplayMatrixTests(unittest.TestCase):
    def test_identity_hash_preserved_across_via_changes(self):
        disc = PeerDiscovery()
        disc.accept_peers = True
        ident = "deadbeef" * 4
        for via in ("serial", "rns", "beacon"):
            with self.subTest(via=via):
                disc.peers.clear()
                entry = {
                    "hash": UBUNTU,
                    "identity_hash": ident,
                    "name": "ubuntu",
                    "via": via,
                    "last_seen": time.time(),
                }
                if via != "serial":
                    entry["ip"] = "10.0.30.101"
                with patch("chatxz.core.discovery.serial_discovery_active", return_value=True):
                    disc._store_peer(dict(entry))
                stored = disc.peers.get(PeerDiscovery._peer_storage_key(entry))
                self.assertIsNotNone(stored)
                self.assertEqual(normalize_hash(stored.get("identity_hash")), ident)
                self.assertEqual(stored.get("name"), "ubuntu")


class BruteForceEdgeMatrixTests(unittest.TestCase):
    """Hundreds of edge combinations to catch regressions in scope/serial logic."""

    def test_store_peer_edge_combinations(self):
        vias = ("serial", "rns", "beacon")
        ips = ("", "10.10.10.2", "10.0.5.10", "10.0.30.101", "172.17.1.1")
        scopes = ("10.10.10.37", "10.0.30.112", "10.0.5.10", None)
        usb = (True, False)
        n = 0
        for via, ip, scope, usb_up in itertools.product(vias, ips, scopes, usb):
            n += 1
            with self.subTest(case=n, via=via, ip=ip, scope=scope, usb=usb_up):
                disc = PeerDiscovery()
                peer_hash = normalize_hash(f"{n:032x}")
                entry = {
                    "hash": peer_hash,
                    "name": f"peer{n}",
                    "via": via,
                    "last_seen": time.time(),
                }
                if ip:
                    entry["ip"] = ip
                with patch("chatxz.core.discovery.serial_discovery_active", return_value=usb_up):
                    with patch.object(disc, "_scope_ip", return_value=scope):
                        ok = disc._store_peer(entry)
                if via == "serial":
                    if usb_up:
                        self.assertTrue(ok)
                        if ok:
                            self.assertNotIn("ip", disc.peers.get(peer_hash, {}))
                    else:
                        self.assertFalse(ok)
                        self.assertNotIn(peer_hash, disc.peers)
                elif ip and scope and not peer_in_scope(ip, scope) and usb_up:
                    self.assertFalse(ok)
        self.assertGreaterEqual(n, 120)

    def test_messaging_scope_checker_simulation(self):
        from chatxz.web.server import ChatWebServer

        server = ChatWebServer.__new__(ChatWebServer)
        server.config_dir = "/tmp/chatxz-matrix"
        server.discovery = PeerDiscovery()
        server.discovery.accept_peers = True
        server.messaging = _messaging()
        n = 0
        for scope, peer_ip, via, usb_up in itertools.product(
            SCOPE_IPS,
            ("", "10.10.10.2", "10.0.30.101", "10.0.5.10"),
            ("serial", "rns"),
            (True, False),
        ):
            n += 1
            with self.subTest(case=n, scope=scope, ip=peer_ip, via=via, usb=usb_up):
                server.discovery.peers.clear()
                server.discovery.peers[UBUNTU] = {
                    "hash": UBUNTU,
                    "via": via,
                    "last_seen": time.time(),
                }
                if peer_ip:
                    server.discovery.peers[UBUNTU]["ip"] = peer_ip
                with patch.object(server, "_discovery_scope_ip", return_value=scope):
                    with patch(
                        "chatxz.core.discovery.serial_discovery_active",
                        return_value=usb_up,
                    ):
                        with patch(
                            "chatxz.web.server.serial_interface_online",
                            return_value=MagicMock() if usb_up else None,
                        ):
                            allowed = server._peer_in_discovery_scope(UBUNTU)
                if via == "serial" and usb_up:
                    self.assertTrue(allowed)
                elif via == "serial" and not usb_up:
                    if peer_ip and peer_in_scope(peer_ip, scope):
                        self.assertTrue(allowed)
                    else:
                        self.assertFalse(allowed)
                elif peer_ip and peer_in_scope(peer_ip, scope):
                    self.assertTrue(allowed)
                elif peer_ip and not peer_in_scope(peer_ip, scope):
                    self.assertFalse(allowed)
        self.assertGreaterEqual(n, 64)


if __name__ == "__main__":
    unittest.main()