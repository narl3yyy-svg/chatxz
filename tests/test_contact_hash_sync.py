"""Discovery-driven contact hash refresh."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from chatxz.core.contacts import find_contact_by_hash, save_contact, sync_contact_from_discovery


class ContactHashSyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_stale_serial_hash_in_lan_slot_updates_from_discovery(self):
        stale_serial = "b9033de66c42b63e98d7a18f74db63aa"
        current_lan = "3428352734b6dcc09472039c449e65b1"
        save_contact(
            self.tmp,
            stale_serial,
            name="330ss",
            via="serial",
            custom_name=True,
        )
        contact = find_contact_by_hash(self.tmp, stale_serial)
        contact["lan_hash"] = stale_serial
        contact["hash"] = stale_serial
        from chatxz.core.contacts import _contact_path, normalize_contact
        import json

        key = stale_serial
        with open(_contact_path(self.tmp, key), "w") as fh:
            json.dump(normalize_contact(contact), fh, indent=2)

        updated = sync_contact_from_discovery(
            self.tmp,
            {
                "hash": current_lan,
                "name": "330s",
                "ip": "10.0.30.101",
                "port": 8742,
                "via": "rns",
            },
        )
        self.assertIsNotNone(updated)
        self.assertEqual(updated.get("lan_hash"), current_lan)
        self.assertEqual(updated.get("hash"), current_lan)
        self.assertEqual(updated.get("serial_hash"), stale_serial)
        self.assertEqual(updated.get("name"), "330ss")
        self.assertEqual(updated.get("ip"), "10.0.30.101")
        self.assertIsNotNone(find_contact_by_hash(self.tmp, current_lan))

    def test_name_match_updates_lan_hash_without_ip_on_contact(self):
        stale = "b9033de66c42b63e98d7a18f74db63aa"
        current_lan = "3428352734b6dcc09472039c449e65b1"
        save_contact(self.tmp, stale, name="330ss", via="lan", custom_name=True)
        updated = sync_contact_from_discovery(
            self.tmp,
            {
                "hash": current_lan,
                "name": "330s",
                "ip": "10.0.30.101",
                "via": "beacon",
            },
        )
        self.assertIsNotNone(updated)
        self.assertEqual(updated.get("lan_hash"), current_lan)
        self.assertEqual(updated.get("ip"), "10.0.30.101")


if __name__ == "__main__":
    unittest.main()