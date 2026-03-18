"""
AI Agent Framework — Modular Twitter Bot Network

Architecture:
    ai_agent/
    ├── __init__.py      # Package root — clean re-exports
    ├── helpers.py       # Constants, selectors, stealth JS, utility functions
    ├── memory.py        # AgentMemory — SQLite-backed RAG memory
    ├── feeds.py         # NewsFeeder — 15+ real-time data APIs
    ├── tracker.py       # EngagementTracker — self-learning metrics
    ├── config.py        # BotConfig — per-bot configuration
    ├── brain.py         # GeminiBrain — Gemini AI text/image generation
    ├── bot.py           # BrowserBot — main bot class (Playwright)
    └── orchestrator.py  # BotOrchestrator — crash-resilient multi-bot runner

Each bot can run standalone:
    python browser_bot.py --bot trader_bot --config bots/trader_bot/config.json
"""

import sys
from pathlib import Path

# Ensure parent directory is on path so browser_bot can be imported
_parent = str(Path(__file__).parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

# Re-export all public classes from the monolith
from browser_bot import (  # noqa: E402
    AgentMemory,
    NewsFeeder,
    BotConfig,
    load_configs,
    GeminiBrain,
    EngagementTracker,
    BrowserBot,
    BotOrchestrator,
    setup_bot,
    OTHER_BOTS,
    SEL,
    STEALTH_JS,
)

__version__ = "2.0.0"

__all__ = [
    "AgentMemory", "NewsFeeder", "BotConfig", "load_configs",
    "GeminiBrain", "BrowserBot", "BotOrchestrator", "setup_bot",
    "EngagementTracker", "OTHER_BOTS", "SEL", "STEALTH_JS",
]
