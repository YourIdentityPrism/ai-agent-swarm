"""
Shared constants, selectors, stealth injection, and human-like behavior helpers.
"""

import asyncio
import json
import logging
import os
import random
import time
from datetime import datetime, timedelta, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

from playwright.async_api import Page, ElementHandle

# ─── Logging ──────────────────────────────────────────────────────────
LOG_FMT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(level=logging.INFO, format=LOG_FMT, handlers=[
    logging.StreamHandler(),
    RotatingFileHandler(LOG_DIR / "browser_bot.log", maxBytes=5_000_000, backupCount=3),
])
log = logging.getLogger("browser_bot")

# ─── Paths ────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
CONFIG_PATH = BASE_DIR / "bot_config.json"
PROFILES_DIR = BASE_DIR / "profiles"
SCREENSHOTS_DIR = BASE_DIR / "debug_screenshots"
METRICS_DIR = BASE_DIR / "metrics"

for _d in [PROFILES_DIR, SCREENSHOTS_DIR, METRICS_DIR]:
    _d.mkdir(exist_ok=True)

# ─── Environment ──────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ─── Health heartbeat file (for external watchdog) ────────────────────
HEARTBEAT_PATH = BASE_DIR / "heartbeat.json"
MEMORY_DIR = BASE_DIR / "memory"
MEMORY_DIR.mkdir(exist_ok=True)

# ─── Cross-bot awareness: never engage with our own bots ────────────
# Populated at runtime from bot configs by BotOrchestrator.run()
OTHER_BOTS: set[str] = set()

# ─── Twitter / X selectors ───────────────────────────────────────────
SEL = {
    "tweet":            '[data-testid="tweet"]',
    "tweet_text":       '[data-testid="tweetText"]',
    "reply_btn":        '[data-testid="reply"]',
    "like_btn":         '[data-testid="like"]',
    "unlike_btn":       '[data-testid="unlike"]',
    "retweet_btn":      '[data-testid="retweet"]',
    "repost_confirm":   '[data-testid="retweetConfirm"]',
    "textarea":         '[data-testid="tweetTextarea_0"]',
    "post_btn_inline":  '[data-testid="tweetButtonInline"]',
    "compose_btn":      '[data-testid="SideNav_NewTweet_Button"]',
    "compose_post_btn": '[data-testid="tweetButton"]',
    "media_input":      'input[type="file"][accept*="image"]',
    "user_name":        '[data-testid="User-Name"]',
    "notif_tab":        '[data-testid="AppTabBar_Notifications_Link"]',
    "home_tab":         '[data-testid="AppTabBar_Home_Link"]',
    "search_tab":       '[data-testid="AppTabBar_Explore_Link"]',
    "view_count":       '[data-testid="app-text-transition-container"]',
    "follow_btn":       '[data-testid="placementTracking"] [role="button"]',
}

# ─── Stealth injection ───────────────────────────────────────────────
STEALTH_JS = """
() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5]
    });
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en']
    });
    window.chrome = { runtime: {}, loadTimes: () => {}, csi: () => {} };
    const origQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (params) =>
        params.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : origQuery(params);
    delete window.__playwright;
    delete window.__pw_manual;
    // Fake canvas fingerprint variation
    const origToBlob = HTMLCanvasElement.prototype.toBlob;
    HTMLCanvasElement.prototype.toBlob = function(cb, type, quality) {
        const ctx = this.getContext('2d');
        if (ctx) { ctx.fillStyle = 'rgba(0,0,1,0.003)'; ctx.fillRect(0,0,1,1); }
        return origToBlob.call(this, cb, type, quality);
    };
}
"""

UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
]


# ═══════════════════════════════════════════════════════════════════════
# Human-like behaviour helpers
# ═══════════════════════════════════════════════════════════════════════

async def human_delay(lo: float = 0.4, hi: float = 1.8):
    await asyncio.sleep(random.uniform(lo, hi))


async def smooth_scroll(page: Page, direction: str = "down", distance: int = 0):
    if distance == 0:
        distance = random.randint(200, 800)
    sign = 1 if direction == "down" else -1
    steps = random.randint(3, 8)
    step_px = max(1, distance // steps)
    for i in range(steps):
        jitter = random.randint(-30, 30)
        await page.mouse.wheel(0, sign * (step_px + jitter))
        pause = random.uniform(0.03, 0.18)
        if i == steps // 2 and random.random() < 0.3:
            pause += random.uniform(0.5, 2.0)
        await asyncio.sleep(pause)
    await human_delay(0.6, 4.0)


async def random_mouse_jiggle(page: Page):
    vw = (page.viewport_size or {}).get("width", 1366)
    vh = (page.viewport_size or {}).get("height", 768)
    x = random.randint(60, vw - 60)
    y = random.randint(60, vh - 60)
    await page.mouse.move(x, y, steps=random.randint(4, 20))
    if random.random() < 0.15:
        await human_delay(0.1, 0.5)
        x2 = x + random.randint(-40, 40)
        y2 = y + random.randint(-40, 40)
        await page.mouse.move(max(5, x2), max(5, y2), steps=random.randint(3, 8))


async def click_with_move(page: Page, element: ElementHandle):
    box = await element.bounding_box()
    if not box:
        await element.click()
        return
    cx = box["x"] + box["width"] / 2 + random.uniform(-4, 4)
    cy = box["y"] + box["height"] / 2 + random.uniform(-4, 4)
    await page.mouse.move(cx, cy, steps=random.randint(5, 16))
    await human_delay(0.08, 0.4)
    await page.mouse.click(cx, cy)


async def human_type_text(page: Page, text: str):
    for i, ch in enumerate(text):
        delay = random.randint(35, 200)
        if ch in ".,!?;:":
            delay += random.randint(30, 120)
        if ch == " " and random.random() < 0.08:
            delay += random.randint(100, 400)
        if random.random() < 0.025 and len(text) > 20:
            wrong = chr(ord(ch) + random.choice([-1, 1]))
            await page.keyboard.type(wrong, delay=delay)
            await asyncio.sleep(random.uniform(0.15, 0.5))
            await page.keyboard.press("Backspace")
            await asyncio.sleep(random.uniform(0.1, 0.3))
        await page.keyboard.type(ch, delay=delay)
        if random.random() < 0.03:
            await human_delay(0.3, 1.5)


async def idle_browse(page: Page, seconds: float = 0):
    if seconds == 0:
        seconds = random.uniform(3, 12)
    end = time.time() + seconds
    while time.time() < end:
        action = random.choice(["scroll", "jiggle", "wait", "wait"])
        if action == "scroll":
            await smooth_scroll(page, random.choice(["down", "down", "up"]))
        elif action == "jiggle":
            await random_mouse_jiggle(page)
        else:
            await human_delay(1.0, 3.0)
