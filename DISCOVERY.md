<!-- Copyright (c) 2026 Smart Touch Infotech Private Limited. All rights reserved. -->
<!-- SAM (Smart Analyst for Markets) — Proprietary Software -->

# SAM — Discovery (How It Works Under the Hood)

## Architecture Flow

```
User types message in browser
        │
        ▼
┌─────────────────┐
│  React Frontend  │  (localhost:3000)
│  /ws/prices      │← Real-time price stream
│  /ws/chat        │← SAM chat
└────────┬────────┘
         │ WebSocket (JSON)
         ▼
┌─────────────────┐
│  FastAPI Backend │  (localhost:8000)
│  /ws/chat        │  SAM agent endpoint
│  /ws/prices      │  Price streaming endpoint
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌──────────────┐
│  SAM   │ │  Live Feed   │
│ Agent  │ │  (live_feed) │
│ Claude │ │  Finnhub WS  │
│ + Tools│ │  Trade stream│
└───┬────┘ └──────────────┘
    │ Tool calls
    ▼
┌─────────────────────────────┐
│  Finnhub REST  │ Portfolio  │
│  - Quotes      │ - JSON    │
│  - News        │ - P&L     │
│  - Earnings    │ - Watch   │
│  - Analysts    │           │
└─────────────────────────────┘
```

## Real-Time Price Streaming

SAM uses **two WebSocket connections** for zero-delay data:

1. **Backend → Finnhub** (`wss://ws.finnhub.io`):
   - Connects on server startup via `live_feed.py`
   - Subscribes to all portfolio + watchlist symbols automatically
   - Receives trade-by-trade data (price, volume, timestamp)
   - Stores latest prices in memory

2. **Backend → Frontend** (`/ws/prices`):
   - Frontend connects on page load
   - Backend pushes every price update instantly
   - Frontend merges live prices with REST data
   - P&L recalculated on every tick
   - Price flash animation on uptick (green) / downtick (red)

Auto-subscription:
- Server startup → subscribes to all existing portfolio/watchlist symbols
- Add position → auto-subscribes to that symbol
- Remove position → unsubscribes if not in watchlist
- SAM chat → syncs subscriptions after every response

## How a Chat Message Flows

1. **User sends message** → Frontend sends JSON over WebSocket to backend
2. **Backend receives** → Appends to conversation history, sends "typing" indicator
3. **Agent processes** → Sends full conversation + system prompt + tools to Claude API
4. **Claude decides** → Either responds with text OR requests tool calls
5. **Tool use loop** → If Claude wants data:
   - Backend executes the tool (e.g., calls Finnhub for a quote)
   - Sends tool result back to Claude
   - Claude may call more tools or generate final response
   - Loop continues until Claude responds with text
6. **Response sent** → Backend sends Claude's text response over WebSocket
7. **Subscription sync** → Backend syncs live feed subscriptions (portfolio may have changed)
8. **Frontend renders** → Markdown rendered in chat bubble, terminal refreshes

## Tool Use Loop (The Brain)

```python
# Simplified flow in agent.py
response = claude.create(messages, tools)

while response.stop_reason == "tool_use":
    # Execute each tool Claude requested
    for tool_call in response.tool_calls:
        result = execute_tool(tool_call)

    # Send results back to Claude
    response = claude.create(messages + tool_results, tools)

# Final text response
return response.text
```

SAM can chain multiple data lookups in a single response. For BTST/STBT analysis, SAM calls 5-6 tools:
1. `get_price` → live quote
2. `technical_analysis` → RSI/MACD/trend
3. `get_news_sentiment` → news flow
4. `get_earnings_surprises` → last 4 quarters
5. `get_recommendation_trends` → analyst consensus
6. `get_price_target` → target vs current (if available)

Then synthesizes all into a 10-factor scorecard with verdict.

## Data Storage

Portfolio and watchlist are stored in `data/portfolio.json`:

```json
{
  "holdings": [
    {"symbol": "NVDA", "qty": 100, "avg_price": 120.50}
  ],
  "watchlist": ["AAPL", "TSLA", "MSFT"]
}
```

- Portfolio data persists across container restarts via Docker volume mount (`./data:/app/data`)
- Chat history persists in the browser via localStorage
- Live prices are held in memory (`live_feed.LIVE_PRICES`) — rebuilt on reconnect
- REST fallback polls every 30s; primary updates come via WebSocket streaming

## API Endpoints

All endpoints return JSON error responses with status 500 on failure instead of crashing.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/quote/{symbol}` | GET | Live price for a stock |
| `/api/analysis/{symbol}` | GET | Technical analysis (RSI, MACD, SMA, Bollinger, ATR) |
| `/api/news?symbol=X&limit=N` | GET | News articles |
| `/api/sentiment/{symbol}` | GET | News sentiment scoring |
| `/api/earnings` | GET | Earnings calendar (from_date, to_date params) |
| `/api/earnings/{symbol}` | GET | Last 4 quarters earnings surprises |
| `/api/recommendations/{symbol}` | GET | Analyst buy/hold/sell consensus |
| `/api/price-target/{symbol}` | GET | Analyst price targets (premium tier) |
| `/api/portfolio` | GET | Portfolio with live P&L (uEquity 17 data points) |
| `/api/portfolio/add` | POST | Add holding `{symbol, qty, avg_price}` + auto-subscribe live feed |
| `/api/portfolio/remove` | POST | Remove holding `{symbol}` + unsubscribe if not in watchlist |
| `/api/watchlist` | GET | Watchlist with prices |
| `/ws/chat` | WebSocket | Chat with SAM |
| `/ws/prices` | WebSocket | Real-time price streaming to frontend |

## Key Design Decisions

1. **Finnhub over Alpaca** — Finnhub provides a simple API key without requiring a brokerage account. Free tier covers quotes, news, earnings, recommendations, and WebSocket streaming.

2. **Claude Sonnet for agent** — Balances speed and intelligence. Fast enough for real-time chat, smart enough for multi-step BTST/STBT analysis.

3. **Dual WebSocket architecture** — `/ws/chat` for AI conversation, `/ws/prices` for real-time price streaming. No polling delay.

4. **JSON file for portfolio** — Simple, no database needed. Portfolio data is small and doesn't need complex queries.

5. **No trading execution** — SAM is deliberately read-only. This eliminates risk of accidental trades and keeps the scope focused on analysis.

6. **Docker Compose** — Single command startup. Backend has healthcheck; frontend waits for backend to be healthy. Data persists via volume mount.

7. **BTST/STBT framework** — 10-factor scoring with conviction levels. SAM must gather ALL data before giving any verdict. Explains contrarian moves.

## Extending SAM

To add new capabilities:
1. Add a function in `market_data.py` or create a new module
2. Add a tool definition in `agent.py` TOOLS list
3. Add a handler in `agent.py` TOOL_HANDLERS dict
4. (Optional) Add a REST endpoint in `main.py`
5. (Optional) Update `live_feed.py` if real-time data is needed
6. Rebuild: `docker compose up -d --build backend`
