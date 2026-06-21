"""Simple UDP LAN beacon for peer discovery (supplements RNS announces)."""

import json
import socket
import threading
import time

from chatxz.core.discovery import APP_NAME
from chatxz.utils.platform import lan_broadcast, lan_ip

BEACON_PORT = 8743
MAGIC = b"CHATXZ1"
BEACON_INTERVAL = 30


class LanBeacon:
    def __init__(self, discovery, identity_hash, display_name="", ip=None, port=8742):
        self.discovery = discovery
        self.identity_hash = (identity_hash or "").replace(":", "")
        self.display_name = display_name or ""
        self.ip = ip
        self.port = port
        self.running = False
        self._sock = None
        self._listen_thread = None
        self._periodic_thread = None
        self.last_send_targets = []
        self.packets_sent = 0
        self.packets_received = 0

    def start(self):
        if self.running:
            return
        self.running = True
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        except OSError:
            pass
        self._sock.bind(("0.0.0.0", BEACON_PORT))
        self._sock.settimeout(1.0)
        self._listen_thread = threading.Thread(target=self._listen, name="chatxz-beacon-rx", daemon=True)
        self._listen_thread.start()
        self._periodic_thread = threading.Thread(target=self._periodic, name="chatxz-beacon-tx", daemon=True)
        self._periodic_thread.start()
        print(f"[beacon] Listening on UDP {BEACON_PORT}")

    def stop(self):
        self.running = False
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    def _payload(self):
        return json.dumps({
            "app": APP_NAME,
            "v": 1,
            "hash": self.identity_hash,
            "name": self.display_name,
            "ip": self.ip or "",
            "port": self.port,
        }).encode("utf-8")

    def _broadcast_targets(self):
        targets = []
        for candidate in (lan_broadcast(), "255.255.255.255"):
            if candidate and candidate not in targets:
                targets.append(candidate)
        ip = lan_ip() or self.ip
        if ip:
            parts = ip.split(".")
            if len(parts) == 4:
                directed = f"{parts[0]}.{parts[1]}.{parts[2]}.255"
                if directed not in targets:
                    targets.insert(0, directed)
        self.last_send_targets = targets
        return targets

    def send(self, count=3):
        if not self._sock or not self.running:
            return 0
        packet = MAGIC + self._payload()
        sent = 0
        for _ in range(count):
            for addr in self._broadcast_targets():
                try:
                    self._sock.sendto(packet, (addr, BEACON_PORT))
                    sent += 1
                except OSError as exc:
                    print(f"[beacon] send to {addr}:{BEACON_PORT} failed: {exc}")
        self.packets_sent += sent
        if sent:
            print(f"[beacon] Sent {sent} packet(s) to {self.last_send_targets}")
        return sent

    def _listen(self):
        while self.running and self._sock:
            try:
                data, addr = self._sock.recvfrom(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            if len(data) < len(MAGIC) + 2 or not data.startswith(MAGIC):
                continue
            try:
                payload = json.loads(data[len(MAGIC):].decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            if not payload.get("ip"):
                payload["ip"] = addr[0]
            self.packets_received += 1
            self.discovery._on_beacon(payload, self.identity_hash)

    def _periodic(self):
        time.sleep(3)
        while self.running:
            self.send(count=1)
            for _ in range(BEACON_INTERVAL):
                if not self.running:
                    return
                time.sleep(1)