"""Tests for configuration loading and validation."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from browser_bot import BotConfig


class TestBotConfigExample(unittest.TestCase):
    """Validate the example config file."""

    def setUp(self):
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "bot_config.example.json")
        with open(config_path) as f:
            self.data = json.load(f)

    def test_valid_json(self):
        """Example config is valid JSON with bots array."""
        self.assertIn("bots", self.data)
        self.assertIsInstance(self.data["bots"], list)
        self.assertGreater(len(self.data["bots"]), 0)

    def test_all_bots_parseable(self):
        """All example bots can be parsed into BotConfig."""
        for bot_data in self.data["bots"]:
            cfg = BotConfig.from_dict(bot_data)
            self.assertTrue(cfg.name)
            self.assertTrue(cfg.persona)

    def test_content_types_have_weights(self):
        """Each content type has type, weight, and prompt_hint."""
        for bot_data in self.data["bots"]:
            for ct in bot_data.get("content_types", []):
                self.assertIn("type", ct)
                self.assertIn("weight", ct)
                self.assertIn("prompt_hint", ct)
                self.assertGreater(ct["weight"], 0)

    def test_weights_sum_roughly_one(self):
        """Content type weights should sum to approximately 1.0."""
        for bot_data in self.data["bots"]:
            total = sum(ct["weight"] for ct in bot_data.get("content_types", []))
            self.assertAlmostEqual(total, 1.0, places=1)

    def test_no_secrets_in_example(self):
        """Example config contains no real API keys or tokens."""
        raw = json.dumps(self.data)
        self.assertNotIn("AIzaSy", raw)
        self.assertNotIn("ghp_", raw)
        self.assertNotIn("sk-", raw)
        # Check cookie files don't point to real files
        for bot_data in self.data["bots"]:
            cookies = bot_data.get("cookies_file", "")
            if cookies:
                self.assertIn("bot", cookies.lower())

    def test_sleep_hours_valid(self):
        """Sleep hours are valid UTC hours (0-23)."""
        for bot_data in self.data["bots"]:
            for h in bot_data.get("sleep_hours_utc", []):
                self.assertGreaterEqual(h, 0)
                self.assertLessEqual(h, 23)


class TestBotConfigEdgeCases(unittest.TestCase):
    def test_minimal_config(self):
        """Minimal config with only required fields."""
        cfg = BotConfig(name="minimal", persona="You are minimal.")
        self.assertEqual(cfg.name, "minimal")
        self.assertEqual(cfg.max_posts_per_day, 2)

    def test_all_fields_config(self):
        """Config with all fields set."""
        cfg = BotConfig.from_dict({
            "name": "full",
            "persona": "Full agent",
            "twitter_handle": "FullAgent",
            "api_only": True,
            "cookies_file": "cookies_full.json",
            "max_posts_per_day": 10,
            "max_replies_per_day": 50,
            "max_gql_replies_per_day": 20,
            "min_post_interval_hours": 2,
            "sleep_hours_utc": [0, 1, 2, 3],
            "target_accounts": ["a", "b"],
            "priority_accounts": ["a"],
            "hashtags": ["#test"],
            "search_keywords": ["AI", "test"],
            "content_types": [{"type": "t", "weight": 1.0, "prompt_hint": "p"}],
            "post_image_probability": 0.8,
            "max_video_posts_per_day": 3,
            "video_prompt_template": "{{DYNAMIC}} test",
        })
        self.assertEqual(cfg.max_posts_per_day, 10)
        self.assertEqual(cfg.max_video_posts_per_day, 3)
        self.assertTrue(cfg.api_only)
        self.assertEqual(len(cfg.target_accounts), 2)


if __name__ == "__main__":
    unittest.main()
