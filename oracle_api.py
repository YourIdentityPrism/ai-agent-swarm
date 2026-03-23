#!/usr/bin/env python3
"""Sentiment Oracle + Reputation API — lightweight HTTP server.
Runs alongside browser_bot, exposes /api/sentiment and /api/reputation endpoints.
"""
import asyncio
import json
import time
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

log = logging.getLogger("oracle")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# Import NewsFeeder from browser_bot (same process or import)
_sentiment_cache = {"data": None, "ts": 0}
_CACHE_TTL = 300  # 5 min

async def _fetch_sentiment_direct():
    import urllib.request
    result = {}

    # 1. DeFi Llama Solana TVL
    try:
        req = urllib.request.Request("https://api.llama.fi/v2/chains", headers={"User-Agent": "Mozilla/5.0"})
        resp = await asyncio.to_thread(lambda: urllib.request.urlopen(req, timeout=15).read())
        chains = json.loads(resp)
        sol = next((c for c in chains if c.get("name") == "Solana"), None)
        if sol:
            result["tvl_total"] = sol.get("tvl", 0)
    except: pass

    # 2. TVL change
    try:
        req = urllib.request.Request("https://api.llama.fi/v2/historicalChainTvl/Solana", headers={"User-Agent": "Mozilla/5.0"})
        resp = await asyncio.to_thread(lambda: urllib.request.urlopen(req, timeout=15).read())
        hist = json.loads(resp)
        if len(hist) >= 2:
            today = hist[-1].get("tvl", 0)
            yesterday = hist[-2].get("tvl", 1)
            result["tvl_change_1d"] = ((today - yesterday) / yesterday * 100) if yesterday else 0
    except: pass

    # 3. Prices
    try:
        req = urllib.request.Request("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,solana&vs_currencies=usd&include_24hr_change=true", headers={"User-Agent": "Mozilla/5.0"})
        resp = await asyncio.to_thread(lambda: urllib.request.urlopen(req, timeout=10).read())
        prices = json.loads(resp)
        result["sol_price"] = prices.get("solana", {}).get("usd", 0)
        result["sol_price_24h_change"] = prices.get("solana", {}).get("usd_24h_change", 0)
        result["btc_price"] = prices.get("bitcoin", {}).get("usd", 0)
    except: pass

    # 4. Fear & Greed
    try:
        req = urllib.request.Request("https://api.alternative.me/fng/?limit=1", headers={"User-Agent": "Mozilla/5.0"})
        resp = await asyncio.to_thread(lambda: urllib.request.urlopen(req, timeout=10).read())
        fng_data = json.loads(resp).get("data", [{}])[0]
        result["fear_greed"] = {"value": int(fng_data.get("value", 50)), "label": fng_data.get("value_classification", "Neutral")}
    except:
        result["fear_greed"] = {"value": 50, "label": "Neutral"}

    # 5. Solana sentiment
    try:
        req = urllib.request.Request("https://api.coingecko.com/api/v3/coins/solana?localization=false&tickers=false&community_data=true&developer_data=false&sparkline=false", headers={"User-Agent": "Mozilla/5.0"})
        resp = await asyncio.to_thread(lambda: urllib.request.urlopen(req, timeout=10).read())
        data = json.loads(resp)
        result["sol_sentiment_up"] = data.get("sentiment_votes_up_percentage", 50)
    except:
        result["sol_sentiment_up"] = 50

    # 6. Top protocols
    try:
        req = urllib.request.Request("https://api.llama.fi/protocols", headers={"User-Agent": "Mozilla/5.0"})
        resp = await asyncio.to_thread(lambda: urllib.request.urlopen(req, timeout=15).read())
        protocols = json.loads(resp)
        sol_protos = []
        for p in protocols:
            sol_tvl = (p.get("chainTvls") or {}).get("Solana", 0)
            if sol_tvl > 0:
                sol_protos.append({"name": p.get("name", "?"), "tvl": sol_tvl, "change_1d": p.get("change_1d", 0) or 0})
        sol_protos.sort(key=lambda x: x["tvl"], reverse=True)
        result["top_protocols"] = sol_protos[:10]
        result["top_movers"] = [p for p in sol_protos[:10] if abs(p.get("change_1d", 0)) > 2]
    except: pass

    # Composite score
    score = 50
    sol_change = result.get("sol_price_24h_change", 0)
    if sol_change > 5: score += 15
    elif sol_change > 2: score += 8
    elif sol_change < -5: score -= 15
    elif sol_change < -2: score -= 8
    tvl_change = result.get("tvl_change_1d", 0)
    if tvl_change > 3: score += 10
    elif tvl_change > 0: score += 3
    elif tvl_change < -3: score -= 10
    elif tvl_change < 0: score -= 3
    fng_val = result.get("fear_greed", {}).get("value", 50)
    score += (fng_val - 50) // 5
    sent_up = result.get("sol_sentiment_up", 50)
    score += int((sent_up - 50) * 0.2)
    score = max(0, min(100, score))

    if score >= 70: mood = "very_bullish"
    elif score >= 55: mood = "bullish"
    elif score >= 45: mood = "neutral"
    elif score >= 30: mood = "bearish"
    else: mood = "very_bearish"

    result["score"] = score
    result["mood"] = mood
    result["timestamp"] = time.time()
    return result

def get_sentiment_sync():
    """Get cached sentiment or fetch fresh."""
    if _sentiment_cache["data"] and time.time() - _sentiment_cache["ts"] < _CACHE_TTL:
        return _sentiment_cache["data"]
    # Trigger async fetch in background thread
    import threading
    def _bg():
        try:
            loop = asyncio.new_event_loop()
            data = loop.run_until_complete(_fetch_sentiment_direct())
            loop.close()
            if data:
                _sentiment_cache["data"] = data
                _sentiment_cache["ts"] = time.time()
                log.info("Sentiment oracle updated: score=%s mood=%s", data.get("score"), data.get("mood"))
        except Exception as e:
            log.error("BG sentiment error: %s", e)
    if not _sentiment_cache.get("_fetching"):
        _sentiment_cache["_fetching"] = True
        t = threading.Thread(target=_bg, daemon=True)
        t.start()
        t.join(timeout=25)  # Wait up to 25s for first fetch
        _sentiment_cache["_fetching"] = False
    return _sentiment_cache.get("data") or {"error": "loading, retry in 30s"}

# Wallet reputation (calls Identity Prism API)
async def _fetch_reputation(address: str):
    """Analyze wallet via Identity Prism's existing analysis."""
    try:
        from browser_bot import NewsFeeder
        result = await NewsFeeder.analyze_solana_wallet(address)
        if result:
            # Build trust score
            score = 50  # base
            age_days = result.get("account_age_days", 0)
            if age_days > 365: score += 15
            elif age_days > 90: score += 8
            elif age_days < 7: score -= 20

            sol_balance = result.get("sol_balance", 0)
            if sol_balance > 10: score += 10
            elif sol_balance > 1: score += 5

            token_count = result.get("token_accounts", 0)
            if token_count > 20: score += 8
            elif token_count > 5: score += 3

            nft_count = result.get("nft_count", 0)
            if nft_count > 10: score += 5

            tx_count = result.get("transaction_count", 0)
            if tx_count > 500: score += 10
            elif tx_count > 100: score += 5
            elif tx_count < 10: score -= 10

            score = max(0, min(100, score))
            if score >= 75: tier = "high_trust"
            elif score >= 50: tier = "medium_trust"
            elif score >= 25: tier = "low_trust"
            else: tier = "suspicious"

            return {
                "address": address,
                "trust_score": score,
                "tier": tier,
                "sol_balance": sol_balance,
                "token_accounts": token_count,
                "nft_count": nft_count,
                "transaction_count": tx_count,
                "account_age_days": age_days,
                "timestamp": time.time(),
            }
    except Exception as e:
        log.error("Reputation fetch error: %s", e)
    return {"error": "analysis failed", "address": address}


def get_reputation_sync(address: str):
    try:
        loop = asyncio.new_event_loop()
        data = loop.run_until_complete(_fetch_reputation(address))
        loop.close()
        return data
    except Exception as e:
        log.error("Sync reputation error: %s", e)
        return {"error": str(e), "address": address}


class OracleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/sentiment" or self.path == "/api/sentiment/":
            data = get_sentiment_sync()
            self._json_response(200, data)

        elif self.path.startswith("/api/reputation/"):
            address = self.path.split("/api/reputation/")[1].strip("/")
            if not address or len(address) < 32:
                self._json_response(400, {"error": "invalid address"})
                return
            data = get_reputation_sync(address)
            self._json_response(200, data)

        elif self.path == "/api/health":
            self._json_response(200, {
                "status": "ok",
                "agent_id": 33278,
                "uptime": time.time(),
                "endpoints": ["/api/sentiment", "/api/reputation/<solana_address>", "/api/health"]
            })

        else:
            self._json_response(404, {"error": "not found",
                                       "endpoints": ["/api/sentiment", "/api/reputation/<address>", "/api/health"]})

    def _json_response(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())

    def log_message(self, format, *args):
        log.info(format % args)


def run_oracle(port=8080):
    server = HTTPServer(("0.0.0.0", port), OracleHandler)
    log.info("Oracle API running on port %d", port)
    server.serve_forever()


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_oracle(port)
