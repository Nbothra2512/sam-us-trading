<!-- Copyright (c) 2026 Smart Touch Infotech Private Limited. All rights reserved. -->
<!-- SAM (Smart Analyst for Markets) — Proprietary Software -->

# SAM — Project Structure

```
trading-agent/
├── .env                      # API keys (gitignored)
├── .env.example              # API keys template
├── .gitignore
├── .dockerignore             # Docker build exclusions
├── docker-compose.yml        # One-command startup with healthcheck
├── PROJECT_OVERVIEW.md       # What SAM is, features, tech stack
├── PROJECT_STRUCTURE.md      # This file
├── SYSTEM_PROMPT.md          # SAM's full system prompt / brain
├── DISCOVERY.md              # How SAM works under the hood
│
├── backend/
│   ├── __init__.py           # Python package marker
│   ├── Dockerfile
│   ├── requirements.txt      # Python dependencies
│   ├── config.py             # Environment variable loader
│   ├── main.py               # FastAPI server, WebSocket endpoints, REST APIs, lifespan events
│   ├── agent.py              # SAM's AI brain — system prompt, 14 tools, Claude API loop, BTST/STBT framework
│   ├── market_data.py        # Finnhub REST API — quotes, technicals, news, sentiment, earnings, recommendations
│   ├── portfolio.py          # Portfolio & watchlist — uEquity 17-point data, JSON storage, market session
│   └── live_feed.py          # Finnhub WebSocket — real-time price streaming, client management, auto-subscribe
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── public/
│   │   └── index.html
│   └── src/
│       ├── index.js          # React entry point
│       ├── App.js            # Split layout — uEquity terminal (top) + SAM chat (bottom)
│       ├── App.css           # Split layout + chat styling
│       ├── Portfolio.js      # uEquity terminal — live WebSocket prices, 17 data points, 5 column groups
│       └── Portfolio.css     # Terminal styling — colored headers, flash animations, spread bars, feed badge
│
├── data/                     # Docker volume mount, created at runtime
│   └── portfolio.json        # Persisted portfolio & watchlist data
│
└── System UI/                # Design specs (reference only)
    └── uEquity-Portfolio-Preview.docx
```

## File Responsibilities

### Backend

| File | Role |
|------|------|
| `config.py` | Loads `FINNHUB_API_KEY` and `ANTHROPIC_API_KEY` from `.env` |
| `main.py` | FastAPI app with REST endpoints, `/ws/chat` for SAM, `/ws/prices` for live streaming, lifespan auto-subscribe |
| `agent.py` | SAM's brain — system prompt with BTST/STBT framework, 14 tool definitions, tool handlers, Claude API tool-use loop |
| `market_data.py` | Finnhub REST API — `get_live_quote()`, `get_technical_analysis()`, `get_news()`, `get_news_sentiment()`, `get_earnings_calendar()`, `get_earnings_surprises()`, `get_recommendation_trends()`, `get_price_target()` |
| `portfolio.py` | uEquity terminal data with all 17 data points per position, JSON storage, bid/ask estimation, market session detection |
| `live_feed.py` | Finnhub WebSocket streaming — connects on startup, manages subscriptions, pushes trade-by-trade prices to frontend clients |

### Frontend

| File | Role |
|------|------|
| `App.js` | Split layout parent — syncs portfolio state between terminal and chat via `refreshKey`/`onPortfolioChange` |
| `Portfolio.js` | uEquity terminal — connects to `/ws/prices` for real-time updates, merges live prices with REST data, recalculates P&L on every tick |
| `App.css` | Split layout + chat styling — dark terminal theme |
| `Portfolio.css` | Bloomberg-style terminal styling — colored group headers, bid/ask colors, flash animations, LIVE FEED badge |
