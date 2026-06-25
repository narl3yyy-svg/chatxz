"""Tests for received-files directory path normalization."""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from chatxz.web.server import ChatWebServer


class ReceivedDirNormalization(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.server = ChatWebServer(host="127.0.0.1", port=0)
        self.server.config_dir = self.tmp

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_accepts_absolute_path(self):
        sub = os.path.join(self.tmp, "downloads")
        os.makedirs(sub, exist_ok=True)
        path, err = self.server._normalize_received_dir(sub)
        self.assertIsNone(err)
        self.assertEqual(path, os.path.normpath(sub))

    @unittest.skipUnless(sys.platform == "win32", "Windows path normalization")
    def test_accepts_forward_slash_windows_path(self):
        sub = os.path.join(self.tmp, "downloads")
        os.makedirs(sub, exist_ok=True)
        forward = sub.replace("\\", "/")
        path, err = self.server._normalize_received_dir(forward)
        self.assertIsNone(err)
        self.assertEqual(path, os.path.normpath(sub))

    def test_resolves_relative_name_against_config_dir(self):
        sub = os.path.join(self.tmp, "received")
        os.makedirs(sub, exist_ok=True)
        path, err = self.server._normalize_received_dir("received")
        self.assertIsNone(err)
        self.assertEqual(path, sub)

    def test_rejects_unknown_relative_path(self):
        path, err = self.server._normalize_received_dir("not-a-real-folder")
        self.assertIsNone(path)
        self.assertIn("absolute", err.lower())


if __name__ == "__main__":
    unittest.main()