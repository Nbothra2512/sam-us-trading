# SAM — Project Structure

```
trading-agent/
├── .env                      # API keys (gitignored)
├── .env.example              # API keys template
├── .gitignore
├── docker-compose.yml        # One-command startup
├── PROJECT_OVERVIEW.md       # What SAM is, features, tech stack
├── PROJECT_STRUCTURE.md      # This file
├── SYSTEM_PROMPT.md          # SAM's full system prompt / brain
├── DISCOVERY.md              # How SAM works under the hood
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt      # Python dependencies
│   ├── config.py             # Environment variable loader
│   ├── main.py               # FastAPI server, WebSocket endpoint, REST APIs
│   ├── agent.py              # SAM's AI brain — system prompt, tools, Claude API loop
│   ├── market_data.py        # Finnhub API — live quotes, technicals, news, sentiment
│   └── portfolio.py          # Portfolio & watchlist — JSON file storage, live P&L
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── public/
│   │   └── index.html
│   └── src/
│       ├── index.js          # React entry point
│       ├── App.js            # Chat UI, sidebar (portfolio/watchlist), WebSocket client
│       └── App.css           # Dark terminal theme styling
│
└── data/                     # Created at runtime
    └── portfolio.json        # Persisted portfolio & watchlist data
```

## File Responsibilities

### Backend

| File | Role |
|------|------|
| `config.py` | Loads `FINNHUB_API_KEY` and `ANTHROPIC_API_KEY` from `.env` |
| `main.py` | FastAPI app with REST endpoints (`/api/quote/{symbol}`, `/api/portfolio`, etc.) and WebSocket chat at `/ws/chat` |
| `agent.py` | SAM's brain — contains the full system prompt, 10 tool definitions, tool handlers, and the Claude API tool-use loop |
| `market_data.py` | All Finnhub API calls — `get_live_quote()`, `get_technical_analysis()`, `get_news()`, `get_news_sentiment()` |
| `portfolio.py` | JSON-based storage for holdings and watchlist. Fetches live prices for P&L calculation |

### Frontend

| File | Role |
|------|------|
| `App.js` | Main React component — WebSocket connection, chat messages, sidebar with portfolio/watchlist, quick commands |
| `App.css` | Dark theme inspired by Bloomberg terminal — responsive, professional |
