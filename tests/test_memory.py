"""Tests for AgentMemory — SQLite-backed RAG memory system."""
import os
import sys
import time
import tempfile
import unittest

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Patch MEMORY_DIR before importing
import browser_bot
_tmpdir = tempfile.mkdtemp()
browser_bot.MEMORY_DIR = type(browser_bot.MEMORY_DIR)(_tmpdir)

from browser_bot import AgentMemory


class TestAgentMemory(unittest.TestCase):
    def setUp(self):
        self.mem = AgentMemory("test_bot")

    def tearDown(self):
        try:
            os.remove(self.mem.db_path)
        except OSError:
            pass

    def test_remember_and_recall(self):
        """Memories are stored and retrievable."""
        self.mem.remember("post", "Hello world!", author="test_bot")
        self.mem.remember("reply", "Great point!", author="test_bot")
        recent = self.mem.recall_recent(5)
        self.assertEqual(len(recent), 2)
        self.assertEqual(recent[-1]["content"], "Great point!")

    def test_short_term_limit(self):
        """Short-term memory respects maxlen (25)."""
        for i in range(30):
            self.mem.remember("post", f"Message {i}")
        recent = self.mem.recall_recent(50)
        self.assertEqual(len(recent), 25)  # maxlen=25

    def test_remember_interaction(self):
        """User interactions are stored and searchable."""
        self.mem.remember_interaction("alice", "Nice take!", "Thanks!")
        self.mem.remember_interaction("alice", "Interesting", "Indeed")
        self.mem.remember_interaction("bob", "Hello", "Hi")
        alice_history = self.mem.recall_about_user("alice")
        self.assertEqual(len(alice_history), 2)
        bob_history = self.mem.recall_about_user("bob")
        self.assertEqual(len(bob_history), 1)

    def test_tweet_dedup(self):
        """Reply deduplication works correctly."""
        url = "https://x.com/user/status/12345"
        self.assertFalse(self.mem.is_tweet_replied(url))
        self.mem.mark_tweet_replied(url, author="someone")
        self.assertTrue(self.mem.is_tweet_replied(url))
        # Duplicate insert doesn't crash
        self.mem.mark_tweet_replied(url, author="someone")
        self.assertTrue(self.mem.is_tweet_replied(url))

    def test_load_replied_urls(self):
        """Bulk load of replied URLs works."""
        for i in range(10):
            self.mem.mark_tweet_replied(f"https://x.com/u/status/{i}")
        urls = self.mem.load_replied_urls(days=1)
        self.assertEqual(len(urls), 10)

    def test_cleanup_old_replies(self):
        """Old replies are cleaned up correctly."""
        # Insert an old reply
        self.mem._exec(
            "INSERT INTO replied_tweets (tweet_url, author, ts) VALUES (?, ?, ?)",
            ("https://old.tweet", "old", time.time() - 40 * 86400))
        # Insert a recent reply
        self.mem.mark_tweet_replied("https://new.tweet")
        self.mem.cleanup_old_replies(days=30)
        urls = self.mem.load_replied_urls(days=365)
        self.assertEqual(len(urls), 1)
        self.assertIn("https://new.tweet", urls)

    def test_state_persistence(self):
        """Bot state (key-value) persists across get/set."""
        self.assertFalse(self.mem.get_state("counter"))  # empty or None
        self.mem.set_state("counter", "42")
        self.assertEqual(self.mem.get_state("counter"), "42")
        self.mem.set_state("counter", "43")
        self.assertEqual(self.mem.get_state("counter"), "43")

    def test_user_reply_count(self):
        """Reply count per user is tracked."""
        self.mem.remember_interaction("alice", "Reply 1", "Tweet 1")
        self.mem.remember_interaction("alice", "Reply 2", "Tweet 2")
        self.mem.remember_interaction("bob", "Reply 1", "Tweet 1")
        self.assertEqual(self.mem.user_reply_count_recent("alice", days=1), 2)
        self.assertEqual(self.mem.user_reply_count_recent("bob", days=1), 1)
        self.assertEqual(self.mem.user_reply_count_recent("charlie", days=1), 0)

    def test_search(self):
        """Text search across memories works."""
        self.mem.remember("post", "Bitcoin price hit $100k today")
        self.mem.remember("post", "AI agents are the future")
        self.mem.remember("post", "Bitcoin L1 smart contracts are live")
        results = self.mem.search("bitcoin")
        self.assertGreaterEqual(len(results), 2)

    def test_empty_tweet_url(self):
        """Empty URLs are handled gracefully."""
        self.mem.mark_tweet_replied("")
        self.assertFalse(self.mem.is_tweet_replied(""))


class TestBotConfig(unittest.TestCase):
    def test_from_dict(self):
        """BotConfig.from_dict creates config from dict, ignoring unknown keys."""
        from browser_bot import BotConfig
        d = {
            "name": "test_bot",
            "persona": "You are a test bot.",
            "twitter_handle": "TestBot",
            "max_posts_per_day": 5,
            "unknown_field": "should be ignored",
        }
        cfg = BotConfig.from_dict(d)
        self.assertEqual(cfg.name, "test_bot")
        self.assertEqual(cfg.twitter_handle, "TestBot")
        self.assertEqual(cfg.max_posts_per_day, 5)

    def test_defaults(self):
        """BotConfig has sensible defaults."""
        from browser_bot import BotConfig
        cfg = BotConfig(name="test", persona="test")
        self.assertEqual(cfg.api_only, False)
        self.assertEqual(cfg.max_replies_per_day, 15)
        self.assertEqual(cfg.sleep_hours_utc, [])
        self.assertEqual(cfg.cookies_file, "")


class TestOtherBots(unittest.TestCase):
    def test_other_bots_auto_populated(self):
        """OTHER_BOTS set is initially empty (populated at runtime)."""
        self.assertIsInstance(browser_bot.OTHER_BOTS, set)


if __name__ == "__main__":
    unittest.main()
