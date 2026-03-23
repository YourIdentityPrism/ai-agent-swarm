"""Patch browser_bot.py: add Grok news integration via cookie-auth REST API."""
import sys

code_path = sys.argv[1] if len(sys.argv) > 1 else "/srv/apps/browser_bot/browser_bot.py"
with open(code_path) as f:
    code = f.read()

changes = 0

# 1. Add _grok_gql_ref storage + setter in NewsFeeder (next to _api_client_ref)
old_api_ref = '''    _api_client_ref = None

    @classmethod
    def set_api_client(cls, api):
        """Set a shared API client for NewsFeeder to use."""
        cls._api_client_ref = api

    @classmethod
    def _get_api_client(cls):
        return cls._api_client_ref'''

new_api_ref = '''    _api_client_ref = None
    _grok_gql_ref = None  # XGraphQLClient for Grok news (bitpredict cookies)

    @classmethod
    def set_api_client(cls, api):
        """Set a shared API client for NewsFeeder to use."""
        cls._api_client_ref = api

    @classmethod
    def _get_api_client(cls):
        return cls._api_client_ref

    @classmethod
    def set_grok_client(cls, gql):
        """Set a shared GQL client for Grok news queries (uses bitpredict cookies)."""
        cls._grok_gql_ref = gql

    @classmethod
    async def get_grok_news(cls, niche: str = "solana") -> str:
        """Ask Grok for fresh news + analytics, optimized for Twitter content.
        Uses bitpredict's GQL client cookies. Cached for 2 hours."""
        cache_key = f"grok_news_{niche}"
        if cache_key in cls._cache and time.time() - cls._cache_ts.get(cache_key, 0) < 7200:
            return cls._cache[cache_key]
        gql = cls._grok_gql_ref
        if not gql or gql.disabled:
            return ""
        try:
            from curl_cffi.requests import Session
            # Ensure ClientTransaction is initialized
            if not gql._client_transaction:
                await gql._fetch_query_ids()

            s = Session(impersonate="chrome131")

            # Step 1: Create conversation
            conv_hdrs = gql._headers("POST", "/i/api/graphql/6cmfJY3d7EPWuCSXWrkOFg/CreateGrokConversation")
            r1 = s.post(
                "https://x.com/i/api/graphql/6cmfJY3d7EPWuCSXWrkOFg/CreateGrokConversation",
                json={"variables": {}, "queryId": "6cmfJY3d7EPWuCSXWrkOFg"},
                headers=conv_hdrs, timeout=15)
            conv_data = json.loads(r1.text)
            conv_id = conv_data["data"]["create_grok_conversation"]["conversation_id"]

            # Step 2: Ask Grok for niche-specific news with Twitter-optimized analysis
            prompts = {
                "solana": (
                    "You are a Solana ecosystem analyst preparing a Twitter content brief. "
                    "Search for the latest Solana news from the past 12 hours. Return EXACTLY this format:\\n\\n"
                    "HEADLINES:\\n"
                    "1. [headline] — [source] — [key number/stat]\\n"
                    "2. ...\\n"
                    "(up to 8 headlines)\\n\\n"
                    "HOT TAKES (tweet-ready, 200 chars max each):\\n"
                    "1. [contrarian or insightful take on headline #X]\\n"
                    "2. [data insight connecting two stories]\\n"
                    "3. [prediction based on the trends]\\n\\n"
                    "KEY NUMBERS: TVL, SOL price, notable protocol changes, any records broken.\\n"
                    "Be specific. Real names, real numbers. No fluff."
                ),
                "bitcoin": (
                    "You are a Bitcoin ecosystem analyst preparing a Twitter content brief. "
                    "Search for the latest Bitcoin/crypto news from the past 12 hours. Return EXACTLY this format:\\n\\n"
                    "HEADLINES:\\n"
                    "1. [headline] — [source] — [key number/stat]\\n"
                    "(up to 8 headlines)\\n\\n"
                    "HOT TAKES (tweet-ready, 200 chars max each):\\n"
                    "1. [contrarian take]\\n"
                    "2. [data insight]\\n"
                    "3. [prediction]\\n\\n"
                    "KEY NUMBERS: BTC price, ETF flows, hashrate, notable moves.\\n"
                    "Be specific. Real names, real numbers."
                ),
                "ai": (
                    "You are an AI/tech analyst preparing a Twitter content brief. "
                    "Search for the latest AI and tech news from the past 12 hours. Return EXACTLY this format:\\n\\n"
                    "HEADLINES:\\n"
                    "1. [headline] — [source] — [key number/stat]\\n"
                    "(up to 8 headlines)\\n\\n"
                    "HOT TAKES (tweet-ready, 200 chars max each):\\n"
                    "1. [contrarian take]\\n"
                    "2. [data insight]\\n"
                    "3. [prediction]\\n\\n"
                    "KEY NUMBERS: funding rounds, user counts, benchmarks."
                ),
            }
            prompt = prompts.get(niche, prompts["solana"])

            grok_hdrs = gql._headers("POST", "/2/grok/add_response.json")
            grok_hdrs["origin"] = "https://x.com"
            grok_hdrs["referer"] = "https://x.com/i/grok"

            r2 = s.post("https://grok.x.com/2/grok/add_response.json", json={
                "responses": [{"message": prompt, "sender": 1}],
                "grokModelOptionId": "grok-3",
                "conversationId": conv_id,
                "returnSearchResults": True,
                "returnCitations": True,
            }, headers=grok_hdrs, timeout=90)

            # Parse streaming JSONL
            import re as _re
            text = ""
            for line in r2.text.split("\\n"):
                if not line.strip():
                    continue
                try:
                    j = json.loads(line)
                    if "result" in j:
                        msg = j["result"].get("message", "")
                        if msg:
                            text += msg
                except Exception:
                    pass
            # Strip Grok tool_usage XML tags
            text = _re.sub(r"<xai:tool_usage_card>.*?</xai:tool_usage_card>", "", text, flags=_re.DOTALL).strip()

            if text and len(text) > 50:
                cls._cache[cache_key] = text
                cls._cache_ts[cache_key] = time.time()
                log.info("Grok news [%s]: got %d chars", niche, len(text))
                return text
            else:
                log.warning("Grok news [%s]: empty response (status %d)", niche, r2.status_code)
                return cls._cache.get(cache_key, "")
        except Exception as e:
            log.warning("Grok news [%s] failed: %s", niche, str(e)[:200])
            return cls._cache.get(cache_key, "")'''

if old_api_ref in code:
    code = code.replace(old_api_ref, new_api_ref, 1)
    changes += 1
    print("1. Added Grok news method + gql ref to NewsFeeder")
else:
    print("WARN: Could not find _api_client_ref block")

# 2. Add Grok news to build_context (top priority, before niche tweets)
old_niche = '''        # ─── PRIORITY: News + Niche tweets (TOP of context) ───────────
        # Niche ecosystem tweets (via X API search) — HIGHEST priority
        niche_tweets = await cls.get_niche_tweets(bot_niche)'''

new_niche = '''        # ─── PRIORITY: News + Niche tweets (TOP of context) ───────────
        # Grok real-time intelligence (HIGHEST priority — freshest data)
        grok_brief = await cls.get_grok_news(bot_niche)
        if grok_brief:
            priority_parts.append(
                ">>> GROK INTELLIGENCE BRIEF (real-time, highest quality) <<<\\n" + grok_brief[:1500])
        # Niche ecosystem tweets (via X API search)
        niche_tweets = await cls.get_niche_tweets(bot_niche)'''

if old_niche in code:
    code = code.replace(old_niche, new_niche, 1)
    changes += 1
    print("2. Added Grok news to build_context (top priority)")
else:
    print("WARN: Could not find niche tweets block in build_context")

# 3. Add Grok to build_digest_context
old_digest = '''        parts = []
        news = await cls.get_all_solana_news()'''

new_digest = '''        parts = []
        # Grok intelligence brief (freshest, highest quality)
        grok = await cls.get_grok_news("solana")
        if grok:
            parts.append("GROK REAL-TIME BRIEF:\\n" + grok[:1200])
        news = await cls.get_all_solana_news()'''

if old_digest in code:
    code = code.replace(old_digest, new_digest, 1)
    changes += 1
    print("3. Added Grok to build_digest_context")
else:
    print("WARN: Could not find build_digest_context insertion")

# 4. Set Grok GQL client in BotOrchestrator (use bitpredict cookies)
old_orch = '''            if not bot.api and not bot.gql:
                log.error("Bot %s: no API and no GQL — skipping", cfg.name)
                continue'''

new_orch = '''            # Share bitpredict's GQL client for Grok news queries
            if cfg.name == "bitpredict" and bot.gql:
                NewsFeeder.set_grok_client(bot.gql)
                log.info("Grok news client set (via bitpredict cookies)")

            if not bot.api and not bot.gql:
                log.error("Bot %s: no API and no GQL — skipping", cfg.name)
                continue'''

if old_orch in code:
    code = code.replace(old_orch, new_orch, 1)
    changes += 1
    print("4. Added Grok GQL client setup in BotOrchestrator")
else:
    print("WARN: Could not find BotOrchestrator insertion")

with open(code_path, "w") as f:
    f.write(code)
print(f"\nDone: {changes} changes applied, {code.count(chr(10)) + 1} lines")
