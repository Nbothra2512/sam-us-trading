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
│   ├── main.py               # FastAPI server, WebSocket endpoint, REST APIs (with error handling)
│   ├── agent.py              # SAM's AI brain — system prompt, tools, Claude API loop
│   ├── market_data.py        # Finnhub API — live quotes, technicals, news, sentiment (with error handling)
│   └── portfolio.py          # Portfolio & watchlist — uEquity 17-point data, JSON storage (with error handling)
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
│       ├── Portfolio.js      # uEquity terminal — Bloomberg-style, 17 data points, 5 column groups
│       └── Portfolio.css     # Terminal styling — colored headers, flash animations, spread bars
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
| `main.py` | FastAPI app with REST endpoints, WebSocket chat at `/ws/chat`, logging, error handling on all routes |
| `agent.py` | SAM's brain — system prompt, 10 tool definitions, tool handlers, Claude API tool-use loop |
| `market_data.py` | Finnhub API calls — `get_live_quote()`, `get_technical_analysis()`, `get_news()`, `get_news_sentiment()` |
| `portfolio.py` | uEquity terminal data with all 17 data points per position, JSON storage, bid/ask estimation, market session detection |

### Frontend

| File | Role |
|------|------|
| `App.js` | Split layout parent — syncs portfolio state between terminal and chat via `refreshKey`/`onPortfolioChange` |
| `Portfolio.js` | uEquity terminal — 5 column groups, price flash, spread indicator, session badge, add/remove modal, auto-refresh |
| `App.css` | Split layout + chat styling — dark terminal theme |
| `Portfolio.css` | Bloomberg-style terminal styling — colored group headers, bid/ask colors, animations |
