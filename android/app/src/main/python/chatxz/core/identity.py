import os
import shutil

import RNS

IDENTITY_DIR = "identities"
IDENTITY_FILE_LAN = "identity_lan"
IDENTITY_FILE_SERIAL = "identity_serial"
IDENTITY_FILE_LEGACY = "identity"


class DualIdentityManager:
    """Independent LAN and Serial RNS identities (v0.5+)."""

    def __init__(self, config_dir):
        self.config_dir = config_dir
        self.identity_dir = os.path.join(config_dir, IDENTITY_DIR)
        self.lan_path = os.path.join(self.identity_dir, IDENTITY_FILE_LAN)
        self.serial_path = os.path.join(self.identity_dir, IDENTITY_FILE_SERIAL)
        self.legacy_path = os.path.join(self.identity_dir, IDENTITY_FILE_LEGACY)
        self.identity_lan = None
        self.identity_serial = None

    def _migrate_legacy(self):
        if os.path.isfile(self.lan_path):
            return
        if os.path.isfile(self.legacy_path):
            os.makedirs(self.identity_dir, exist_ok=True)
            shutil.copy2(self.legacy_path, self.lan_path)
            print("[identity] Migrated legacy identity → identity_lan")

    def _load_file(self, path):
        if os.path.isfile(path):
            return RNS.Identity.from_file(path)
        return None

    def _save_file(self, identity, path):
        os.makedirs(self.identity_dir, exist_ok=True)
        identity.to_file(path)

    def load_or_create(self, serial_enabled=False):
        """Load LAN identity (always) and serial identity when serial transport enabled."""
        self._migrate_legacy()
        os.makedirs(self.identity_dir, exist_ok=True)
        self.identity_lan = self._load_file(self.lan_path)
        if not self.identity_lan:
            self.identity_lan = RNS.Identity()
            self._save_file(self.identity_lan, self.lan_path)
        if serial_enabled:
            self.identity_serial = self._load_file(self.serial_path)
            if not self.identity_serial:
                self.identity_serial = RNS.Identity()
                self._save_file(self.identity_serial, self.serial_path)
                print("[identity] Created new serial identity")
        else:
            self.identity_serial = self._load_file(self.serial_path)
        return self.identity_lan

    @property
    def identity(self):
        """Backward compat: primary LAN identity."""
        return self.identity_lan

    def get_identity(self, role="lan"):
        role = (role or "lan").strip().lower()
        if role == "serial":
            return self.identity_serial
        return self.identity_lan

    def get_hash(self, role="lan"):
        ident = self.get_identity(role)
        return ident.hash if ident else None

    def get_hex_hash(self, role="lan"):
        h = self.get_hash(role)
        if h:
            return RNS.hexrep(h)
        return None

    def get_connect_hash(self, role="lan"):
        ident = self.get_identity(role)
        if not ident:
            return ""
        try:
            from chatxz.core.discovery import message_dest_hash_for_identity
            return message_dest_hash_for_identity(ident) or ""
        except Exception:
            return ""

    def regenerate(self, role="lan"):
        role = (role or "lan").strip().lower()
        if role == "serial":
            if os.path.exists(self.serial_path):
                os.remove(self.serial_path)
            self.identity_serial = RNS.Identity()
            self._save_file(self.identity_serial, self.serial_path)
            return self.identity_serial
        if os.path.exists(self.lan_path):
            os.remove(self.lan_path)
        self.identity_lan = RNS.Identity()
        self._save_file(self.identity_lan, self.lan_path)
        return self.identity_lan

    def identity_payload(self):
        """API shape for GET /api/identity."""
        lan = {
            "connect_hash": self.get_connect_hash("lan"),
            "identity_hash": self.get_hex_hash("lan"),
        }
        serial = None
        if self.identity_serial:
            serial = {
                "connect_hash": self.get_connect_hash("serial"),
                "identity_hash": self.get_hex_hash("serial"),
            }
        return {
            "lan": lan,
            "serial": serial,
            # Legacy single-hash fields (LAN)
            "hash": lan.get("connect_hash") or "",
            "connect_hash": lan.get("connect_hash") or "",
            "identity_hash": lan.get("identity_hash") or "",
        }


# Backward-compatible alias
IdentityManager = DualIdentityManager