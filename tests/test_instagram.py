import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_instagram_pipeline import collect_urls, normalize_instagram_url


class InstagramIntakeTests(unittest.TestCase):
    def test_normalizes_tracking_url(self):
        item = normalize_instagram_url("https://www.instagram.com/reel/AbC_123/?utm_source=test")
        self.assertEqual(item["source_url"], "https://www.instagram.com/reel/AbC_123/")
        self.assertEqual(item["stable_id"], "instagram:reel:AbC_123")

    def test_rejects_profile_and_non_instagram_urls(self):
        for value in ("https://www.instagram.com/example/", "https://example.com/reel/abc/"):
            with self.assertRaises(ValueError):
                normalize_instagram_url(value)

    def test_deduplicates_url_and_file_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "urls.txt"
            path.write_text("https://instagram.com/p/xyz/\n# note\n", encoding="utf-8")
            unique, duplicates = collect_urls(["https://www.instagram.com/p/xyz/?x=1"], path)
            self.assertEqual(len(unique), 1)
            self.assertEqual(len(duplicates), 1)


if __name__ == "__main__":
    unittest.main()

