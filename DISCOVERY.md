# SAM — Discovery (How It Works Under the Hood)

## Architecture Flow

```
User types message in browser
        │
        ▼
┌─────────────────┐
│  React Frontend  │  (localhost:3000)
│  WebSocket client│
└────────┬────────┘
         │ WebSocket (JSON)
         ▼
┌─────────────────┐
│  FastAPI Backend │  (localhost:8000)
│  /ws/chat        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  SAM Agent       │  (agent.py)
│  Claude API      │
│  + Tool Use Loop │
└────────┬────────┘
         │ Tool calls
         ▼
┌─────────────────────────────┐
│  Finnhub API    │ Portfolio │
│  - Live quotes  │ - JSON   │
│  - News         │ - P&L    │
│  - Candles      │ - Watch  │
└─────────────────────────────┘
```

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
7. **Frontend renders** → Markdown rendered in chat bubble, sidebar refreshes

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

This means SAM can chain multiple data lookups in a single response. For example, when you ask "Analyze NVDA", SAM might:
1. Call `get_price` for live quote
2. Call `technical_analysis` for RSI/MACD/etc
3. Call `get_news_sentiment` for news analysis
4. Synthesize all three into a Bloomberg-style briefing

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

This file persists across restarts. Live prices are fetched on every portfolio/watchlist view to calculate real-time P&L.

## API Endpoints (REST)

These are available for direct access outside the chat:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/quote/{symbol}` | GET | Live price for a stock |
| `/api/analysis/{symbol}` | GET | Technical analysis |
| `/api/news?symbol=X&limit=N` | GET | News articles |
| `/api/sentiment/{symbol}` | GET | News sentiment |
| `/api/portfolio` | GET | Portfolio with live P&L |
| `/api/watchlist` | GET | Watchlist with prices |
| `/ws/chat` | WebSocket | Chat with SAM |

## Key Design Decisions

1. **Finnhub over Alpaca** — Finnhub provides a simple API key without requiring a brokerage account. Free tier covers quotes, candles, and news.

2. **Claude Sonnet for agent** — Balances speed and intelligence. Fast enough for real-time chat, smart enough for multi-step analysis.

3. **WebSocket over REST for chat** — Enables real-time typing indicators and instant responses without polling.

4. **JSON file for portfolio** — Simple, no database needed. Portfolio data is small and doesn't need complex queries.

5. **No trading execution** — SAM is deliberately read-only. This eliminates risk of accidental trades and keeps the scope focused on analysis.

6. **Docker Compose** — Single command startup. Backend and frontend are isolated containers with their own dependencies.

## Extending SAM

To add new capabilities:
1. Add a function in `market_data.py` or create a new module
2. Add a tool definition in `agent.py` TOOLS list
3. Add a handler in `agent.py` TOOL_HANDLERS dict
4. (Optional) Add a REST endpoint in `main.py`
5. Rebuild: `docker compose up -d --build backend`
