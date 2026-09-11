import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from common import load_config
from match_videos import build_manifest


class CoreTests(unittest.TestCase):
    def template(self):
        return json.loads((ROOT / "templates" / "project.template.json").read_text(encoding="utf-8"))

    def write_config(self, directory, data):
        path = Path(directory) / "project.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_disabled_modules_do_not_require_secrets(self):
        with tempfile.TemporaryDirectory() as directory:
            config = load_config(self.write_config(directory, self.template()))
            self.assertFalse(config["modules"]["feishu"])

    def test_enabled_feishu_requires_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            data = self.template()
            data["modules"]["feishu"] = True
            os.environ.pop("FEISHU_BASE_TOKEN", None)
            with self.assertRaisesRegex(RuntimeError, "FEISHU_BASE_TOKEN"):
                load_config(self.write_config(directory, data))

    def test_unique_unmatched_and_ambiguous(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "alice.mp4").touch()
            (root / "bob.mp4").touch()
            (root / "bob.mov").touch()
            fields = {"creator": "creator", "source_url": "url", "video": "video"}
            records = [
                {"id": "1", "creator": "@Alice", "url": "https://example.test/1"},
                {"id": "2", "creator": "Bob", "url": "https://example.test/2"},
                {"id": "3", "creator": "Carol", "url": "https://example.test/3"},
            ]
            result = build_manifest(records, root, fields)
            self.assertEqual(len(result["matched"]), 1)
            self.assertEqual(len(result["ambiguous"]), 1)
            self.assertEqual(len(result["unmatched_records"]), 1)


if __name__ == "__main__":
    unittest.main()

