"""Contact list deduplication for split lan/serial saves."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from chatxz.core.contacts import (
    _contact_path,
    find_contact_by_hash,
    list_contacts,
    save_contact,
)


class ContactDedupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_list_contacts_merges_split_lan_serial_files_by_name(self):
        lan = "3428352734b6dcc09472039c449e65b1"
        serial = "b9033de66c42b63e98d7a18f74db63aa"
        save_contact(self.tmp, lan, name="330ss", ip="10.0.30.101", via="lan", custom_name=True)
        save_contact(self.tmp, serial, name="330ss", via="serial", custom_name=True)
        contacts = list_contacts(self.tmp)
        self.assertEqual(len(contacts), 1)
        merged = contacts[0]
        self.assertEqual(merged.get("lan_hash"), lan)
        self.assertEqual(merged.get("serial_hash"), serial)
        self.assertEqual(merged.get("name"), "330ss")
        self.assertFalse(os.path.isfile(_contact_path(self.tmp, serial)))

    def test_list_contacts_merges_orphan_files_by_related_name(self):
        lan = "3428352734b6dcc09472039c449e65b1"
        serial = "b9033de66c42b63e98d7a18f74db63aa"
        with open(_contact_path(self.tmp, lan), "w") as fh:
            json.dump(
                {"hash": lan, "lan_hash": lan, "name": "330ss", "custom_name": True},
                fh,
            )
        with open(_contact_path(self.tmp, serial), "w") as fh:
            json.dump(
                {"hash": serial, "serial_hash": serial, "name": "330s", "custom_name": True},
                fh,
            )
        contacts = list_contacts(self.tmp)
        self.assertEqual(len(contacts), 1)
        self.assertEqual(contacts[0].get("lan_hash"), lan)
        self.assertEqual(contacts[0].get("serial_hash"), serial)

    def test_list_contacts_merges_duplicate_identity_files(self):
        ident = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        lan = "11111111111111111111111111111111"
        serial = "22222222222222222222222222222222"
        entry_lan = {
            "hash": lan,
            "lan_hash": lan,
            "name": "peer",
            "identity_hash": ident,
        }
        entry_serial = {
            "hash": serial,
            "serial_hash": serial,
            "name": "peer",
            "identity_hash": ident,
        }
        with open(_contact_path(self.tmp, lan), "w") as fh:
            json.dump(entry_lan, fh)
        with open(_contact_path(self.tmp, serial), "w") as fh:
            json.dump(entry_serial, fh)
        contacts = list_contacts(self.tmp)
        self.assertEqual(len(contacts), 1)
        self.assertEqual(contacts[0].get("lan_hash"), lan)
        self.assertEqual(contacts[0].get("serial_hash"), serial)
        self.assertIsNotNone(find_contact_by_hash(self.tmp, lan))
        self.assertIsNotNone(find_contact_by_hash(self.tmp, serial))


if __name__ == "__main__":
    unittest.main()