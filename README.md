# Autonomous AI Agent Swarm for Twitter/X

A production-grade framework for running **multiple autonomous AI agents** that coordinate, learn, and evolve together on Twitter/X. Each agent has its own personality, memory, real-time data feeds, and engagement feedback loops — while cooperating as a swarm to avoid conflicts and amplify reach.

> **4 agents running in production 24/7**, each with distinct personas, posting original content with AI-generated images/videos, replying to trending accounts, and growing followers autonomously.

## Why Multi-Agent?

Single bots are predictable. A **swarm of specialized agents** is exponentially more effective:

| Feature | Single Bot | Agent Swarm |
|---------|-----------|-------------|
| Content diversity | One voice | Multiple distinct personas |
| Niche coverage | One topic | Parallel coverage across niches |
| Reply conflicts | N/A | Coordinated — never double-reply |
| Learning | Self-referential | Cross-pollination of strategies |
| Resilience | Single point of failure | Agents operate independently |

## Architecture

```
                    ┌─────────────────────┐
                    │   BotOrchestrator   │
                    │  (coordination hub) │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
     ┌────────▼──────┐ ┌──────▼───────┐ ┌──────▼───────┐
     │  Agent Alpha  │ │  Agent Beta  │ │  Agent Gamma │
     │  (AI/Tech)    │ │  (Crypto)    │ │  (Builder)   │
     └───────┬───────┘ └──────┬───────┘ └──────┬───────┘
             │                │                │
     ┌───────▼───────────────▼────────────────▼───────┐
     │              Shared Infrastructure              │
     │  ┌──────────┐ ┌──────────┐ ┌─────────────────┐ │
     │  │ GeminiBrain│ │NewsFeeder│ │Action Lock     │ │
     │  │ (AI core)  │ │(15+ APIs)│ │ (no conflicts) │ │
     │  └──────────┘ └──────────┘ └─────────────────┘ │
     └─────────────────────────────────────────────────┘
```

## Key Features

### Per-Agent Intelligence
- **Persona-driven content** — each agent has a unique voice, content strategy, and target audience defined in config
- **Engagement feedback loop** — agents scrape their own tweet metrics and learn what content types perform best
- **Persona evolution** — AI auto-rewrites the agent's personality every 48h based on engagement data
- **RAG memory** — SQLite-backed memory with semantic search; agents remember conversations, learn from interactions
- **Sentiment-aware posting** — checks market mood (BTC price, Fear & Greed Index) before every post

### Swarm Coordination
- **Shared brain** — all agents use the same GeminiBrain instance for consistent quality
- **Action lock** — mutex prevents agents from posting/replying simultaneously
- **Cross-agent dedup** — agents know about each other (OTHER_BOTS) and never reply to the same tweet twice
- **Staggered sessions** — agents start at different times to mimic natural human patterns
- **Shared replied DB** — SQLite tracks all replied tweet IDs across agents

### Content Generation
- **AI text** — Gemini 3 Flash for replies, posts, and engagement analysis
- **AI images** — Gemini image generation with per-agent style templates
- **AI video** — Google Veo 3.1 for 6-second viral video clips with dynamic prompt crafting
- **Real-time data injection** — every prompt includes live BTC price, mempool fees, market sentiment, trending news
- **Anti-repetition** — agents check their recent tweets and never reuse opener, structure, or angle

### Growth Engine
- **Smart follow-back** — follows accounts from notifications with quality gates (min followers, spam filter)
- **Proactive following** — searches niche keywords, targets accounts likely to follow back (friends/followers ratio > 0.3)
- **Mention monitoring** — checks notifications every 30 min, replies to all relevant mentions
- **Niche reply targeting** — finds tweets from target accounts and generates high-quality replies
- **Priority accounts** — configurable VIP list for accounts that always get replies first

### Human Mimicry
- **Realistic timing** — variable session lengths, natural breaks, sleep hours
- **Anti-detection** — WebDriver spoofing, canvas fingerprint randomization, stealth JS injection
- **Rate limiting** — per-account reply limits (3/day per target), daily caps, cooldown periods

## Data Sources (15+)

Real-time data feeds injected into every AI prompt:

| Source | Data |
|--------|------|
| CoinGecko | BTC/ETH/SOL prices, 24h changes, market cap |
| Mempool.space | Bitcoin fee rates, block height, unconfirmed tx count |
| Alternative.me | Fear & Greed Index |
| Polymarket | Prediction market odds for trending events |
| CoinTelegraph RSS | Breaking crypto news |
| Bitcoin Magazine RSS | Bitcoin-specific news |
| Helius API | Solana wallet analysis (balances, NFTs, DeFi positions) |

## Quick Start

### 1. Clone and configure

```bash
git clone https://github.com/user/ai-agent-framework.git
cd ai-agent-framework
cp .env.example .env
cp bot_config.example.json bot_config.json
```

### 2. Set your Gemini API key

```bash
# .env
GEMINI_API_KEY=your-key-here
```

### 3. Add Twitter cookies

Export cookies from your browser (use a cookie export extension) and save as JSON:

```bash
# Each bot needs its own cookies file
# Format: [{"name": "auth_token", "value": "..."}, {"name": "ct0", "value": "..."}, ...]
```

### 4. Configure your agents

Edit `bot_config.json` — see `bot_config.example.json` for the full schema. Each agent needs:
- `name` — unique identifier
- `twitter_handle` — the Twitter account
- `cookies_file` — path to cookies JSON
- `persona` — AI personality prompt
- `content_types` — weighted content categories with prompt hints
- `target_accounts` — accounts to monitor and reply to

### 5. Run

```bash
# Direct
pip install -r requirements.txt
python browser_bot.py

# Docker
docker compose up -d
```

### 6. Run a single agent (for testing)

```bash
python browser_bot.py --bot alpha_agent
```

## Configuration

### Agent Config Schema

```jsonc
{
  "name": "agent_name",
  "twitter_handle": "TwitterHandle",
  "cookies_file": "cookies_agent.json",    // Cookie-based auth (no API keys needed)
  "api_only": true,                         // No browser — pure API/GQL mode

  // Targeting
  "target_accounts": ["account1", "account2"],
  "priority_accounts": ["vip_account"],     // Always reply first
  "search_keywords": ["AI agents", "LLM"],  // For proactive engagement

  // Rate Limits
  "max_posts_per_day": 3,
  "max_replies_per_day": 40,
  "max_gql_replies_per_day": 15,
  "min_post_interval_hours": 4,
  "sleep_hours_utc": [4, 5, 6, 7, 8, 9, 10],

  // Content
  "content_types": [
    {"type": "insight", "weight": 0.4, "prompt_hint": "..."},
    {"type": "commentary", "weight": 0.3, "prompt_hint": "..."}
  ],
  "persona": "You are... (full personality prompt)",

  // Media
  "post_image_probability": 0.5,
  "image_prompt_template": "Style guidelines for AI image generation...",
  "max_video_posts_per_day": 2,
  "video_prompt_template": "{{DYNAMIC}} Guidelines for Veo video generation..."
}
```

### Dynamic Video Prompts

When `video_prompt_template` starts with `{{DYNAMIC}}`, Gemini analyzes the tweet text and crafts an optimal video generation prompt for Veo 3.1, instead of using a static template. This produces contextually relevant, viral-optimized video content.

## Project Structure

```
ai-agent-framework/
├── browser_bot.py              # Core engine (~9800 lines)
│   ├── AgentMemory              # SQLite RAG memory system
│   ├── NewsFeeder               # 15+ real-time data APIs
│   ├── EngagementTracker        # Self-learning metrics
│   ├── BotConfig                # Per-bot configuration
│   ├── XApiClient               # Twitter API v2 (OAuth)
│   ├── XGraphQLClient           # Twitter GraphQL (cookie-based)
│   ├── GeminiBrain              # AI text/image/video generation
│   ├── GrokBrowser              # Grok integration via Playwright
│   ├── BrowserBot               # Main bot class
│   └── BotOrchestrator          # Multi-bot coordination
├── ai_agent/                    # Package facade (clean imports)
├── bot_config.example.json      # Example multi-agent config
├── .env.example                 # Environment variables template
├── Dockerfile                   # Production container
├── docker-compose.yml           # Orchestrated deployment
└── requirements.txt             # Python dependencies
```

## How Agents Cooperate

```
Session Timeline (24h):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
00:00  Agent Alpha wakes up, checks mentions
00:02  Agent Beta wakes up (staggered start)
00:05  Alpha posts insight → acquires action lock
00:06  Beta waits for lock release
00:07  Alpha releases lock → Beta replies to @VitalikButerin
00:15  Alpha finds tweet from @AnthropicAI → replies
00:16  Beta sees same tweet → skips (already in shared replied DB)
00:30  Agent Gamma wakes up, follows back new followers
01:00  All agents enter break (30-60 min randomized)
...
04:00  All agents sleep (configured sleep_hours_utc)
11:00  Agents wake up, new day, counters reset
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Production Stats

Currently running 4 agents in production:
- **3-6 original posts/day** per agent (text + AI images + AI video)
- **10-40 contextual replies/day** per agent to trending accounts
- **50 strategic follows/day** targeting accounts likely to follow back
- **24/7 uptime** with Docker + auto-restart
- **Zero manual intervention** — fully autonomous operation

## Tech Stack

- **Python 3.11+** with asyncio
- **Gemini 3 Flash** — text generation, content analysis, spam detection
- **Gemini Image Gen** — AI-generated images matching agent's visual style
- **Google Veo 3.1** — 6-second AI video clips
- **Playwright** — browser automation (stealth mode)
- **curl_cffi** — TLS fingerprint impersonation for GraphQL
- **SQLite** — agent memory, replied tweets DB
- **Docker** — production deployment

## License

MIT
