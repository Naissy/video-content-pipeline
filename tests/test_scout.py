import copy
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_instagram_pipeline import collect_urls, load_selected_links, metadata_to_item
from select_video_candidates import brief_missing, revalidate_selection, select_candidates

NOW = datetime(2026, 11, 10, 12, tzinfo=timezone.utc)


def project():
    config = json.loads((ROOT / "templates/project.template.json").read_text())
    config["account"].update(slug="cooking-demo", positioning="Quick home cooking", audience="Beginner cooks")
    config["modules"]["video_scout"] = True
    config["discovery"].update(brief_confirmed=True, topics=["Cooking"], content_types=["Demonstration"])
    return config


def candidate(now=NOW, **changes):
    item = {
        "source_url": "https://www.instagram.com/reels/EXAMPLE_A/?utm_source=test",
        "creator": "@example_creator",
        "like_count": 10001,
        "likes_source_url": "https://www.instagram.com/p/EXAMPLE_A/",
        "likes_evidence_type": "instagram_page",
        "verified_at": (now - timedelta(hours=1)).isoformat(),
        "published_at": (now - timedelta(days=1)).isoformat(),
        "duration": 20,
        "duration_evidence": "player",
        "subtitle_load": "low",
        "video_reviewed": True,
        "relevant": True,
        "fit_reason": "A short visual cooking demonstration for beginners",
    }
    return {**item, **changes}


class ScoutTests(unittest.TestCase):
    def setUp(self):
        self.config = project()

    def select(self, items, **kwargs):
        return select_candidates(self.config, items, now=NOW, **kwargs)

    def assert_rejected(self, item):
        result = self.select([item])
        self.assertEqual(result["counts"]["selected"], 0)
        self.assertTrue(result["excluded"][0]["reasons"])

    def test_strict_likes_boundary_and_exact_types(self):
        for count in (9999, 10000, 0, -1, "10K", "10001", 10001.0, True, None):
            with self.subTest(count=count):
                self.assert_rejected(candidate(like_count=count))
        self.assertEqual(self.select([candidate()])["counts"]["selected"], 1)

    def test_views_cannot_replace_likes(self):
        item = candidate(view_count=1000000)
        del item["like_count"]
        self.assert_rejected(item)

    def test_missing_or_unconfirmed_brief_blocks_search(self):
        cases = [
            ("account", "positioning", ""), ("account", "audience", " "),
            ("discovery", "topics", []), ("discovery", "content_types", []),
            ("discovery", "brief_confirmed", False),
        ]
        for block, key, value in cases:
            config = project()
            config[block][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "ask the user before searching"):
                select_candidates(config, [candidate()], now=NOW)

    def test_template_is_not_search_ready(self):
        config = json.loads((ROOT / "templates/project.template.json").read_text())
        self.assertIn("account.positioning", brief_missing(config))
        self.assertIn("discovery.brief_confirmed", brief_missing(config))

    def test_generic_non_rehab_profile_and_evidence_preserved(self):
        item = self.select([candidate(evidence_note="observed source context")])["videos"][0]
        self.assertEqual(item["creator"], "example_creator")
        self.assertEqual(item["source_url"], "https://www.instagram.com/reel/EXAMPLE_A/")
        self.assertEqual(item["evidence_note"], "observed source context")

    def test_primary_evidence_and_identity_required(self):
        for changes in (
            {"likes_evidence_type": "search_snippet"}, {"likes_evidence_type": []},
            {"likes_source_url": "https://www.instagram.com/p/OTHER/"},
            {"source_url": "https://example.com/video"}, {"creator": ""},
        ):
            with self.subTest(changes=changes):
                self.assert_rejected(candidate(**changes))

    def test_stale_future_and_naive_evidence_rejected(self):
        for value in ((NOW - timedelta(hours=25)).isoformat(), (NOW + timedelta(seconds=1)).isoformat(), "2026-11-10T12:00:00", None):
            with self.subTest(value=value):
                self.assert_rejected(candidate(verified_at=value))

    def test_old_or_future_publications_rejected(self):
        for value in ((NOW - timedelta(days=8)).isoformat(), (NOW + timedelta(hours=1)).isoformat(), "unknown"):
            self.assert_rejected(candidate(published_at=value))

    def test_actual_review_relevance_and_subtitle_load_required(self):
        for changes in ({"video_reviewed": False}, {"relevant": False}, {"fit_reason": ""}, {"subtitle_load": "high"}, {"subtitle_load": []}):
            self.assert_rejected(candidate(**changes))

    def test_duration_verified_finite_and_within_limit(self):
        for duration in (None, 0, -1, 31, True, float("nan"), float("inf")):
            self.assert_rejected(candidate(duration=duration))
        self.assert_rejected(candidate(duration_evidence="caption_guess"))

    def test_cross_form_and_previously_used_duplicates(self):
        result = self.select([candidate(), candidate(source_url="https://www.instagram.com/p/EXAMPLE_A/")])
        self.assertEqual(result["counts"], {"reviewed": 2, "selected": 1, "excluded": 1})
        result = self.select([candidate()], seen_urls=["https://www.instagram.com/p/EXAMPLE_A/"])
        self.assertFalse(result["videos"])
        unique, duplicates = collect_urls(["https://www.instagram.com/reels/EXAMPLE_A/", "https://www.instagram.com/p/EXAMPLE_A/"])
        self.assertEqual((len(unique), len(duplicates)), (1, 1))

    def test_limit_keeps_input_ranking(self):
        self.config["discovery"]["limit"] = 1
        second = candidate(source_url="https://www.instagram.com/p/EXAMPLE_B/", likes_source_url="https://www.instagram.com/p/EXAMPLE_B/")
        result = self.select([candidate(), second])
        self.assertEqual(result["videos"][0]["shortcode"], "EXAMPLE_A")
        self.assertIn("count already reached", result["excluded"][0]["reasons"][0])

    def test_cannot_lower_likes_gate_or_use_invalid_settings(self):
        for key, value in (("min_likes", 500), ("min_likes_exclusive", 9999), ("limit", 0), ("lookback_days", -1), ("max_duration_seconds", float("nan")), ("source_platform", "tiktok")):
            config = project()
            config["discovery"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                select_candidates(config, [candidate()], now=NOW)

    def test_selection_revalidated_at_intake(self):
        selection = self.select([candidate()])
        self.assertEqual(len(revalidate_selection(self.config, selection, now=NOW)), 1)
        cases = []
        wrong_account = copy.deepcopy(selection)
        wrong_account["account_slug"] = "another-account"
        cases.append(wrong_account)
        low_likes = copy.deepcopy(selection)
        low_likes["videos"][0]["like_count"] = 10000
        cases.append(low_likes)
        empty = copy.deepcopy(selection)
        empty["videos"] = []
        cases.append(empty)
        for value in cases:
            with self.assertRaises(ValueError):
                revalidate_selection(self.config, value, now=NOW)
        with self.assertRaises(ValueError):
            revalidate_selection(self.config, selection, now=NOW + timedelta(days=2))

    def test_changed_positioning_invalidates_previous_selection(self):
        selection = self.select([candidate()])
        self.config["account"]["positioning"] = "Travel"
        with self.assertRaisesRegex(ValueError, "brief has changed"):
            revalidate_selection(self.config, selection, now=NOW)

    def test_empty_results_are_not_filled_with_low_likes(self):
        result = self.select([candidate(like_count=9999)])
        self.assertFalse(result["videos"])
        self.assertEqual(result["counts"]["excluded"], 1)


class ScoutCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.config = project()
        self.config_path = self.folder / "project.json"
        self.write(self.config_path, self.config)
        self.now = datetime.now(timezone.utc)
        self.candidates = self.folder / "candidates.json"
        self.write(self.candidates, {"candidates": [candidate(self.now)]})
        self.selection = self.folder / "selection.json"

    def write(self, path, value):
        path.write_text(json.dumps(value), encoding="utf-8")

    def run_script(self, name, *args):
        return subprocess.run([sys.executable, str(ROOT / "scripts" / name), "--config", str(self.config_path), *map(str, args)], cwd=self.folder, capture_output=True, text=True)

    def create_selection(self):
        self.write(self.selection, select_candidates(self.config, [candidate(self.now)], now=self.now))

    def test_default_dry_run_does_not_write(self):
        result = self.run_script("select_video_candidates.py", "--candidates", self.candidates, "--output", self.selection)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["dry_run"])
        self.assertFalse(self.selection.exists())

    def test_execute_creates_without_overwriting(self):
        args = ("--candidates", self.candidates, "--output", self.selection, "--execute")
        first = self.run_script("select_video_candidates.py", *args)
        self.assertEqual(first.returncode, 0, first.stderr)
        before = self.selection.read_bytes()
        second = self.run_script("select_video_candidates.py", *args)
        self.assertNotEqual(second.returncode, 0)
        self.assertEqual(before, self.selection.read_bytes())

    def test_end_to_end_handoff_dry_run_and_evidence_retention(self):
        self.create_selection()
        result = self.run_script("run_instagram_pipeline.py", "--selection-manifest", self.selection)
        self.assertEqual(result.returncode, 0, result.stderr)
        plan = json.loads(result.stdout)
        self.assertEqual(plan["links"][0]["selection_evidence"]["like_count"], 10001)
        self.assertFalse((self.folder / "videos").exists())
        self.assertFalse((self.folder / "work").exists())
        link = load_selected_links(self.config, self.selection)[0]
        item = metadata_to_item(link, {"uploader": "example_creator", "duration": 20}, self.folder / "example.mp4")
        self.assertEqual(item["selection_evidence"], link["selection_evidence"])

    def test_cannot_mix_or_bypass_selection(self):
        self.create_selection()
        for args in (("--url", candidate()["source_url"]), ("--selection-manifest", self.selection, "--url", candidate()["source_url"])):
            result = self.run_script("run_instagram_pipeline.py", *args)
            self.assertNotEqual(result.returncode, 0)

    def test_existing_direct_intake_remains_valid(self):
        self.config["modules"].pop("video_scout")
        self.config.pop("discovery")
        self.write(self.config_path, self.config)
        result = self.run_script("run_instagram_pipeline.py", "--url", candidate()["source_url"])
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_router_reports_onboarding_then_discovery(self):
        result = self.run_script("run_pipeline.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        plan = json.loads(result.stdout)
        self.assertTrue(plan["scout_search_ready"])
        self.assertLess(plan["stages"].index("account_brief"), plan["stages"].index("instagram_public_download"))
        self.config["account"]["positioning"] = ""
        self.write(self.config_path, self.config)
        plan = json.loads(self.run_script("run_pipeline.py").stdout)
        self.assertFalse(plan["scout_search_ready"])
        self.assertIn("account.positioning", plan["scout_brief_missing"])


if __name__ == "__main__":
    unittest.main()
