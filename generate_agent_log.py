#!/usr/bin/env python3
"""Parse docker logs and generate structured agent_log.json for hackathon submission.
Run: docker logs browser_bot 2>&1 | python3 generate_agent_log.py > agent_log.json
"""
import sys
import json
import re
from datetime import datetime
from collections import defaultdict

lines = sys.stdin.readlines()

decisions = []
guardrails = []
failures = []
compute = defaultdict(int)
outputs = defaultdict(int)
agents_seen = set()
session_start = None
session_end = None

for line in lines:
    line = line.strip()
    if not line:
        continue

    # Parse timestamp
    ts_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
    ts = ts_match.group(1).replace(' ', 'T') + 'Z' if ts_match else None
    if ts:
        if not session_start:
            session_start = ts
        session_end = ts

    # Extract agent name
    agent_match = re.search(r'bot\.(\w+)', line)
    agent = agent_match.group(1) if agent_match else None
    if agent:
        agents_seen.add(agent)

    # === DECISIONS ===

    # Starting bots
    if 'Starting' in line and 'bot(s)' in line:
        bots_match = re.search(r'Starting (\d+) bot\(s\): (.+)', line)
        if bots_match:
            decisions.append({
                "timestamp": ts,
                "agent": "orchestrator",
                "action": "start_swarm",
                "decision": f"Launch {bots_match.group(1)} agents: {bots_match.group(2)}",
                "result": "success"
            })

    # Post generated
    elif 'API posted:' in line or 'GQL posted:' in line:
        text_match = re.search(r'(?:API|GQL) posted(?:\s*\(VIDEO\))?: (.+)', line)
        method = "API" if "API posted" in line else "GQL"
        is_video = "(VIDEO)" in line
        decisions.append({
            "timestamp": ts,
            "agent": agent,
            "action": "generate_and_post",
            "decision": f"Post via {method}" + (" with video" if is_video else " with image"),
            "tool_calls": [f"GeminiBrain.generate_post()", f"GeminiBrain.generate_image()", f"X{'ApiClient' if method == 'API' else 'GraphQLClient'}.post()"],
            "result": "success",
            "output": text_match.group(1)[:120] + "..." if text_match and len(text_match.group(1)) > 120 else (text_match.group(1) if text_match else "")
        })
        outputs["tweets_posted"] += 1
        compute["gemini_text_calls"] += 1
        compute["gemini_image_calls"] += 1
        if is_video:
            compute["gemini_video_calls"] += 1

    # Digest thread
    elif 'GQL thread [' in line:
        thread_match = re.search(r'GQL thread \[(\d+)/(\d+)\]: (.+)', line)
        if thread_match:
            num, total, text = thread_match.groups()
            if num == "1":
                decisions.append({
                    "timestamp": ts,
                    "agent": agent,
                    "action": "daily_digest_thread",
                    "decision": f"Post digest thread ({total} tweets)",
                    "tool_calls": ["NewsFeeder.build_digest_context()", "GeminiBrain.generate_daily_digest()", "XGraphQLClient.post()", "XGraphQLClient.reply() x" + str(int(total)-1)],
                    "result": "success",
                    "output": text[:120]
                })
                outputs["digest_threads_posted"] += 1
                compute["gemini_text_calls"] += 1
            outputs["digest_tweets_total"] += 1
            compute["gql_api_calls"] += 1

    # Daily digest posted
    elif 'Daily digest posted' in line:
        pass  # already captured by thread [1/N]

    # Generating digest
    elif 'Generating daily Solana digest' in line:
        decisions.append({
            "timestamp": ts,
            "agent": agent,
            "action": "fetch_digest_data",
            "decision": "Aggregate data from DeFi Llama + RSS + prices + niche tweets",
            "tool_calls": ["NewsFeeder.get_defi_llama_solana()", "NewsFeeder.get_all_solana_news()", "NewsFeeder.get_crypto_prices()", "NewsFeeder.get_niche_tweets()"],
            "result": "success"
        })
        compute["data_feed_calls"] += 4

    # GQL reply
    elif 'GQL reply to @' in line:
        reply_match = re.search(r'GQL reply to @(\w+): (.+)', line)
        if reply_match:
            target, text = reply_match.groups()
            decisions.append({
                "timestamp": ts,
                "agent": agent,
                "action": "niche_reply",
                "decision": f"Reply to @{target}",
                "tool_calls": ["GeminiBrain.generate_reply()", "GeminiBrain.post_validate_for_bot()", "XGraphQLClient.reply()"],
                "result": "success",
                "output": text[:120]
            })
            outputs["replies_sent"] += 1
            compute["gemini_text_calls"] += 1
            compute["gql_api_calls"] += 1

    # Conv reply
    elif 'Conv reply to @' in line:
        reply_match = re.search(r'Conv reply to @(\w+): (.+)', line)
        if reply_match:
            target, text = reply_match.groups()
            decisions.append({
                "timestamp": ts,
                "agent": agent,
                "action": "conversation_reply",
                "decision": f"Reply to conversation from @{target}",
                "tool_calls": ["XGraphQLClient.get_tweet_detail()", "GeminiBrain.generate_reply()", "XGraphQLClient.reply()"],
                "result": "success",
                "output": text[:120]
            })
            outputs["conversation_replies"] += 1
            compute["gemini_text_calls"] += 1
            compute["gql_api_calls"] += 2

    # Mentions processed
    elif 'GQL mentions:' in line:
        mentions_match = re.search(r'roasted (\d+), replied (\d+) \(skipped: ({.+})\)', line)
        if mentions_match:
            roasted, replied, skipped = mentions_match.groups()
            decisions.append({
                "timestamp": ts,
                "agent": agent,
                "action": "process_mentions",
                "decision": f"Processed mentions: roasted {roasted}, replied {replied}",
                "result": "success",
                "details": f"skipped: {skipped}"
            })
            outputs["mentions_processed"] += int(roasted) + int(replied)
            compute["gql_api_calls"] += 1

    # Niche search
    elif 'GQL niche: found' in line:
        niche_match = re.search(r'found (\d+) tweets \((\d+) from priority\)', line)
        if niche_match:
            total, priority = niche_match.groups()
            compute["gql_api_calls"] += 1

    # Niche results
    elif 'GQL niche: replied' in line:
        niche_match = re.search(r'replied (\d+) this cycle \(skipped: ({.+})\)', line)
        if niche_match:
            replied, skipped = niche_match.groups()
            if int(replied) == 0:
                guardrails.append({
                    "timestamp": ts,
                    "agent": agent,
                    "guardrail": "niche_filters",
                    "action": f"Skipped all niche tweets: {skipped}",
                    "prevented": "Replying to stale/already-replied/rate-limited content"
                })

    # Follow-back
    elif 'GQL follow-back:' in line:
        compute["gql_api_calls"] += 1

    # Image uploaded
    elif 'image uploaded' in line:
        compute["gql_api_calls"] += 1

    # DeFi Llama
    elif 'DeFi Llama Solana:' in line:
        tvl_match = re.search(r'TVL \$(.+?),', line)
        compute["data_feed_calls"] += 1

    # Solana RSS
    elif 'Solana RSS news:' in line:
        compute["data_feed_calls"] += 1

    # Niche tweets fetched
    elif 'Niche tweets' in line and 'got' in line:
        compute["data_feed_calls"] += 1

    # Self-evaluate
    elif 'self_evaluate' in line.lower() or 'SPECIFICITY' in line or 'ANALYST VALUE' in line:
        compute["gemini_text_calls"] += 1

    # Post skipped
    elif 'Post skipped:' in line:
        reason_match = re.search(r'Post skipped: (.+)', line)
        if reason_match:
            guardrails.append({
                "timestamp": ts,
                "agent": agent,
                "guardrail": "post_rate_limit",
                "action": f"Post skipped: {reason_match.group(1)}",
                "prevented": "Exceeding post limits or posting outside peak hours"
            })

    # Errors
    elif '[ERROR]' in line or '[WARNING]' in line and 'failed' in line.lower():
        err_match = re.search(r'\[(?:ERROR|WARNING)\] .+?: (.+)', line)
        if err_match:
            failures.append({
                "timestamp": ts,
                "agent": agent or "system",
                "error": err_match.group(1)[:200]
            })

    # _can_post check
    elif '_can_post:' in line:
        can_match = re.search(r'_can_post: (\w+) \((.+)\)', line)
        if can_match:
            status, details = can_match.groups()
            if status == "True":
                decisions.append({
                    "timestamp": ts,
                    "agent": agent,
                    "action": "post_eligibility_check",
                    "decision": f"Post allowed: {details}",
                    "result": "proceed"
                })

    # API next cycle
    elif 'API next cycle' in line:
        cycle_match = re.search(r'API next cycle in (\d+) min', line)
        if cycle_match:
            compute["session_cycles"] = compute.get("session_cycles", 0) + 1

# Calculate session duration
duration = 0
if session_start and session_end:
    try:
        t1 = datetime.fromisoformat(session_start.rstrip('Z'))
        t2 = datetime.fromisoformat(session_end.rstrip('Z'))
        duration = int((t2 - t1).total_seconds())
    except Exception:
        pass

log = {
    "agent_name": "SwarmMind",
    "agent_id": 33278,
    "log_version": "1.0",
    "generated_at": datetime.utcnow().isoformat() + "Z",
    "session_start": session_start,
    "session_end": session_end,
    "session_duration_seconds": duration,
    "environment": {
        "runtime": "Docker (Python 3.11, 2GB RAM, Ubuntu)",
        "agents_active": len(agents_seen),
        "agents": sorted(agents_seen),
        "ai_model": "gemini-3-flash-preview",
        "image_model": "imagen-4.0-generate-001",
        "video_model": "veo-3.1",
        "erc8004_agent_id": 33278,
        "erc8004_registry": "eip155:8453:0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"
    },
    "decisions": decisions,
    "guardrails_triggered": guardrails,
    "failures": failures[:20],
    "compute_usage": dict(compute),
    "outputs_summary": dict(outputs)
}

print(json.dumps(log, indent=2, ensure_ascii=False))
