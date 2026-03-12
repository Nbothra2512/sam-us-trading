# SAM — Smart Analyst for Markets

## What is SAM?
SAM is a Bloomberg-grade AI stock market analyst agent with a web-based chat interface. It provides live US market data, news sentiment analysis, technical analysis, and portfolio tracking — all through natural conversation.

SAM does NOT execute trades. It is a research and monitoring tool.

## Golden Rule
**CRITICAL THINK BEFORE ACTING** — SAM always critically evaluates data, challenges assumptions, considers both bull and bear cases, and never rushes to conclusions.

## Features
| Feature | Description |
|---------|-------------|
| **Live Prices** | Real-time stock prices via Finnhub API (bid/ask/mid, daily change) |
| **News Sentiment** | Live news articles with AI-powered bullish/bearish/neutral scoring |
| **Technical Analysis** | RSI, MACD, SMA/EMA, Bollinger Bands, ATR + actionable signals |
| **Portfolio Tracking** | Add holdings, track live P&L per stock and total — read-only |
| **Watchlist** | Track stocks you're interested in with live prices |

## Tech Stack
| Component | Technology |
|-----------|-----------|
| AI Brain | Claude API (Sonnet) via Anthropic SDK |
| Market Data | Finnhub API (free tier) |
| Backend | Python, FastAPI, WebSocket |
| Frontend | React, WebSocket, react-markdown |
| Deployment | Docker Compose |
| Data Storage | JSON file (portfolio/watchlist) |

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
- WebSocket: ws://localhost:8000/ws/chat
