import json
import time
import RNS

DISCOVERY_TIMEOUT = 45
APP_NAME = "chatxz"

class AnnounceHandler:
    aspect_filter = None

    def __init__(self, discovery):
        self.discovery = discovery

    def received_announce(self, destination_hash, announced_identity, app_data):
        self.discovery._on_announce(destination_hash, app_data)


class PeerDiscovery:
    def __init__(self):
        self.peers = {}
        self.running = False
        self._handler = None

    def start(self):
        self.running = True
        self._handler = AnnounceHandler(self)
        RNS.Transport.register_announce_handler(self._handler)
        print("[discovery] Registered RNS announce handler via AnnounceHandler object")

    def stop(self):
        self.running = False

    def _on_announce(self, destination_hash, app_data):
        if not self.running:
            return
        try:
            hash_hex = RNS.hexrep(destination_hash)
            app_repr = repr(app_data) if app_data else "None"
            print(f"[discovery] Got announce dst={hash_hex[:12]}... app_data={app_repr[:80]}")
        except Exception as e:
            print(f"[discovery] Error in announce header: {e}")
            return

        try:
            name = ""
            app_name = ""

            if app_data:
                try:
                    data = json.loads(app_data.decode("utf-8"))
                    app_name = data.get("app", "")
                    name = data.get("name", "")
                except Exception as e:
                    print(f"[discovery] Failed to decode app_data: {e}")

            if app_name != APP_NAME:
                print(f"[discovery] Skipping {hash_hex[:12]}... app_name={app_name!r} != {APP_NAME!r}")
                return

            self.peers[hash_hex] = {
                "hash": hash_hex,
                "name": name or hash_hex[:8],
                "app": app_name,
                "last_seen": time.time(),
            }
            print(f"[discovery] Peer: {hash_hex[:12]}... ({name or 'unnamed'})")
        except Exception as e:
            print(f"[discovery] Error processing announce: {e}")

    def get_peers(self):
        now = time.time()
        stale = [h for h, p in self.peers.items() if now - p["last_seen"] > DISCOVERY_TIMEOUT]
        for h in stale:
            del self.peers[h]
        return list(self.peers.values())
