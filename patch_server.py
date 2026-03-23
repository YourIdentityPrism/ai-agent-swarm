"""Patch server browser_bot.py: add data sources + sentiment oracle + fear&greed."""
import sys

code_path = sys.argv[1] if len(sys.argv) > 1 else "/srv/apps/browser_bot/browser_bot.py"
with open(code_path) as f:
    code = f.read()

changes = 0

# 1. Add DL News + Blockworks RSS feeds
old_feeds = '''        feeds = [
            ("https://cointelegraph.com/rss/tag/solana", True),
            ("https://www.theblock.co/rss.xml", False),
            ("https://decrypt.co/feed", False),
        ]'''
new_feeds = '''        feeds = [
            ("https://cointelegraph.com/rss/tag/solana", True),
            ("https://www.theblock.co/rss.xml", False),
            ("https://decrypt.co/feed", False),
            ("https://www.dlnews.com/arc/outboundfeeds/rss/", False),
            ("https://blockworks.co/feed", False),
        ]'''
if old_feeds in code:
    code = code.replace(old_feeds, new_feeds, 1)
    changes += 1
    print("1. Added DL News + Blockworks RSS feeds")

# 2. Add Fear&Greed + Solana sentiment + Sentiment Oracle methods
insert_marker = "    _api_client_ref = None"
new_methods = '''    @classmethod
    async def get_fear_greed(cls) -> dict:
        """Fetch Crypto Fear & Greed Index."""
        if "fng" in cls._cache and time.time() - cls._cache_ts.get("fng", 0) < cls.CACHE_TTL:
            return cls._cache["fng"]
        try:
            import urllib.request
            req = urllib.request.Request("https://api.alternative.me/fng/?limit=1",
                                        headers={"User-Agent": "Mozilla/5.0"})
            resp = await asyncio.to_thread(
                lambda: urllib.request.urlopen(req, timeout=10).read())
            data = json.loads(resp)
            result = data.get("data", [{}])[0]
            fng = {"value": int(result.get("value", 50)),
                   "label": result.get("value_classification", "Neutral")}
            cls._cache["fng"] = fng
            cls._cache_ts["fng"] = time.time()
            return fng
        except Exception as e:
            log.debug("Fear & Greed fetch failed: %s", e)
            return cls._cache.get("fng", {"value": 50, "label": "Neutral"})

    @classmethod
    async def get_solana_sentiment(cls) -> dict:
        """Fetch Solana community sentiment from CoinGecko."""
        if "sol_sentiment" in cls._cache and time.time() - cls._cache_ts.get("sol_sentiment", 0) < cls.CACHE_TTL:
            return cls._cache["sol_sentiment"]
        try:
            import urllib.request
            url = ("https://api.coingecko.com/api/v3/coins/solana"
                   "?localization=false&tickers=false&community_data=true"
                   "&developer_data=false&sparkline=false")
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            resp = await asyncio.to_thread(
                lambda: urllib.request.urlopen(req, timeout=10).read())
            data = json.loads(resp)
            sent_up = data.get("sentiment_votes_up_percentage", 50)
            result = {
                "sentiment_up": sent_up,
                "sentiment_down": 100 - sent_up,
                "market_cap_rank": data.get("market_cap_rank", 0),
                "coingecko_score": data.get("coingecko_score", 0),
            }
            cls._cache["sol_sentiment"] = result
            cls._cache_ts["sol_sentiment"] = time.time()
            return result
        except Exception as e:
            log.debug("Solana sentiment fetch failed: %s", e)
            return cls._cache.get("sol_sentiment", {"sentiment_up": 50})

    @classmethod
    async def build_sentiment_oracle(cls) -> dict:
        """Build comprehensive sentiment oracle data from all sources."""
        prices = await cls.get_crypto_prices()
        defi = await cls.get_defi_llama_solana()
        fng = await cls.get_fear_greed()
        sol_sent = await cls.get_solana_sentiment()
        news = await cls.get_all_solana_news()
        niche = await cls.get_niche_tweets("solana")
        sentiment = await cls.get_market_sentiment()

        # Composite score (0-100)
        score = 50
        sol_change = 0
        if prices.get("solana"):
            sol_change = prices["solana"].get("usd_24h_change", 0)
            if sol_change > 5: score += 15
            elif sol_change > 2: score += 8
            elif sol_change < -5: score -= 15
            elif sol_change < -2: score -= 8
        tvl_change = defi.get("tvl_change_1d", 0)
        if tvl_change > 3: score += 10
        elif tvl_change > 0: score += 3
        elif tvl_change < -3: score -= 10
        elif tvl_change < 0: score -= 3
        fng_val = fng.get("value", 50)
        score += (fng_val - 50) // 5
        sent_up = sol_sent.get("sentiment_up", 50)
        score += int((sent_up - 50) * 0.2)
        score = max(0, min(100, score))

        if score >= 70: mood = "very_bullish"
        elif score >= 55: mood = "bullish"
        elif score >= 45: mood = "neutral"
        elif score >= 30: mood = "bearish"
        else: mood = "very_bearish"

        top_movers = []
        for p in defi.get("top_protocols", [])[:5]:
            if abs(p.get("change_1d", 0)) > 2:
                top_movers.append({"name": p["name"], "change": p["change_1d"],
                                   "direction": "up" if p["change_1d"] > 0 else "down"})

        return {
            "score": score, "mood": mood, "fear_greed": fng,
            "sol_price_24h_change": sol_change,
            "tvl_total": defi.get("total_tvl", 0),
            "tvl_change_1d": tvl_change,
            "sol_sentiment_up": sent_up,
            "top_narratives": news[:5],
            "top_movers": top_movers,
            "niche_tweet_count": len(niche),
            "news_count": len(news),
            "timestamp": time.time(),
        }

'''
if insert_marker in code:
    code = code.replace(insert_marker, new_methods + "    " + insert_marker, 1)
    changes += 1
    print("2. Added Fear&Greed + Solana sentiment + Sentiment Oracle")

# 3. Add Fear & Greed to build_context
old_fng = '        # Trending coins\n        trending = await cls.get_trending_coins()'
new_fng = '        # Fear & Greed Index\n        fng = await cls.get_fear_greed()\n        if fng:\n            priority_parts.append(f"FEAR & GREED INDEX: {fng[\'value\']}/100 ({fng[\'label\']})")\n        # Trending coins\n        trending = await cls.get_trending_coins()'
if old_fng in code:
    code = code.replace(old_fng, new_fng, 1)
    changes += 1
    print("3. Added Fear & Greed to build_context")

# 4. Add Solana sentiment to build_context (Solana section)
old_sol_sent = '            sol = await cls.get_solana_data()'
new_sol_sent = '''            # Solana community sentiment
            sol_sent = await cls.get_solana_sentiment()
            if sol_sent.get("sentiment_up"):
                priority_parts.append(f"SOLANA COMMUNITY: {sol_sent['sentiment_up']:.0f}% bullish (CoinGecko)")
            sol = await cls.get_solana_data()'''
if old_sol_sent in code:
    code = code.replace(old_sol_sent, new_sol_sent, 1)
    changes += 1
    print("4. Added Solana sentiment to build_context")

with open(code_path, "w") as f:
    f.write(code)
print(f"\nDone: {changes} changes applied, {code.count(chr(10)) + 1} lines")
