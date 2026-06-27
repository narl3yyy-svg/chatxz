"""Dual LAN/serial identity manager tests."""

import os
import tempfile
import unittest

from chatxz.core.identity import DualIdentityManager, IDENTITY_FILE_LAN, IDENTITY_FILE_LEGACY


class DualIdentityTests(unittest.TestCase):
    def test_migrates_legacy_identity_to_lan(self):
        with tempfile.TemporaryDirectory() as tmp:
            ident_dir = os.path.join(tmp, "identities")
            os.makedirs(ident_dir)
            legacy = os.path.join(ident_dir, IDENTITY_FILE_LEGACY)
            with open(legacy, "wb") as fh:
                fh.write(b"legacy-stub")
            mgr = DualIdentityManager(tmp)
            mgr.load_or_create(serial_enabled=False)
            self.assertTrue(os.path.isfile(os.path.join(ident_dir, IDENTITY_FILE_LAN)))

    def test_serial_identity_created_when_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            mgr = DualIdentityManager(tmp)
            mgr.load_or_create(serial_enabled=True)
            self.assertIsNotNone(mgr.identity_lan)
            self.assertIsNotNone(mgr.identity_serial)
            lan_h = mgr.get_connect_hash("lan")
            ser_h = mgr.get_connect_hash("serial")
            self.assertEqual(len(lan_h.replace(":", "")), 32)
            self.assertEqual(len(ser_h.replace(":", "")), 32)
            self.assertNotEqual(lan_h, ser_h)

    def test_identity_payload_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            mgr = DualIdentityManager(tmp)
            mgr.load_or_create(serial_enabled=True)
            payload = mgr.identity_payload()
            self.assertIn("lan", payload)
            self.assertIn("connect_hash", payload["lan"])
            self.assertTrue(payload.get("serial"))


if __name__ == "__main__":
    unittest.main()