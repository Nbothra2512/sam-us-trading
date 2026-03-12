# SAM — Smart Analyst for Markets

## What is SAM?
SAM is a Bloomberg-grade AI stock market analyst agent with a web-based interface. It combines a real-time uEquity portfolio terminal with an AI chat powered by Claude — all in a split-screen layout. It provides live US market data, news sentiment analysis, earnings trade analysis (BTST/STBT), and portfolio tracking through natural conversation.

SAM does NOT execute trades. It is a research and monitoring tool.

## Golden Rule
**CRITICAL THINK BEFORE ACTING** — SAM always critically evaluates data, challenges assumptions, considers both bull and bear cases, and never rushes to conclusions.

## Features
| Feature | Description |
|---------|-------------|
| **Real-Time Price Streaming** | Zero-delay prices via Finnhub WebSocket — trade-by-trade updates pushed to dashboard |
| **uEquity Portfolio Terminal** | Bloomberg-style terminal with 17 data points per position, 5 column groups, price flash animations |
| **BTST/STBT Earnings Analysis** | 10-factor scoring framework for 1-day trades around earnings announcements |
| **News Sentiment** | Live news articles with AI-powered bullish/bearish/neutral scoring |
| **Technical Analysis** | RSI, MACD, SMA/EMA, Bollinger Bands, ATR + actionable signals |
| **Earnings Calendar** | Upcoming and recent earnings with EPS estimates vs actuals |
| **Analyst Consensus** | Buy/Hold/Sell recommendations from Wall Street analysts |
| **Portfolio Tracking** | Add holdings, track live P&L per stock and total — read-only |
| **Watchlist** | Track stocks you're interested in with live prices |

## Tech Stack
| Component | Technology |
|-----------|-----------|
| AI Brain | Claude API (Sonnet) via Anthropic SDK |
| Market Data | Finnhub API (REST + WebSocket streaming) |
| Backend | Python, FastAPI, WebSocket |
| Frontend | React, WebSocket, react-markdown |
| Live Feed | Finnhub WebSocket → Backend → Frontend (zero delay) |
| Deployment | Docker Compose with healthcheck |
| Data Storage | JSON file (portfolio/watchlist), localStorage (chat) |

## API Keys Required
| Key | Source |
|-----|--------|
| `FINNHUB_API_KEY` | https://finnhub.io/register (free) |
| `ANTHROPIC_API_KEY` | https://console.anthropic.com |

## How to Run
```bash
cd ~/trading-agent
cp .env.example .env   # Add your API keys
docker compose up -d --build
# Open http://localhost:3000
```

## Ports
- Backend API: http://localhost:8000
- Frontend UI: http://localhost:3000
- Chat WebSocket: ws://localhost:8000/ws/chat
- Price Streaming WebSocket: ws://localhost:8000/ws/prices
