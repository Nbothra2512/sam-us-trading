# SAM — Smart Analyst for Markets

> Copyright (c) 2026 Smart Touch Infotech Private Limited. All rights reserved.
> Proprietary and confidential. Unauthorized copying, distribution, or modification is strictly prohibited.

## What Is SAM?

SAM is a Bloomberg-grade AI stock market analyst with a real-time portfolio terminal. It combines a split-screen web interface — a live portfolio tracker (uEquity) on top and an AI chat on the bottom — powered by Claude Sonnet and Finnhub market data. Zero-delay WebSocket price streaming. Read-only analysis — no trade execution.

---

## Features at a Glance

| Category | Capability |
|----------|-----------|
| Live Quotes | Real-time price, bid, ask, mid, spread for any US stock |
| Technical Analysis | 11 indicators + 4 buy/sell signals (RSI, MACD, SMA, Bollinger, ATR) |
| News & Sentiment | Company/market news with bullish/bearish/neutral scoring |
| Earnings Analysis | Calendar, surprises (last 4 quarters), beat rate tracking |
| BTST/STBT Framework | 10-factor pre-earnings trade scoring with conviction levels |
| Analyst Data | Buy/Hold/Sell consensus, price targets (high/low/mean/median) |
| Portfolio Tracking | 17 data points per position with live P&L |
| Watchlist | Track symbols with live price streaming |
| Real-Time Streaming | Finnhub WebSocket → Backend → Frontend (zero-delay) |
| Market Knowledge | All 11 GICS sectors, macro indicators, earnings season patterns |

---

## 1. Chat Interface (AI Analyst)

- **Real-time WebSocket chat** with SAM — ask anything about the market
- **Persistent chat history** saved in browser (survives refresh)
- **Typing indicator** while SAM processes your question
- **Live/Offline status** with auto-reconnect
- **Markdown-rendered responses** — tables, headers, bullet points
- **Welcome chips** — 5 suggested starter questions to get going
- **Enter to send**, Shift+Enter for multiline

### What You Can Ask SAM

| Query Type | Example |
|-----------|---------|
| Price check | "What's NVDA trading at?" |
| Technical analysis | "Analyze AAPL technicals" / "Is TSLA overbought?" |
| News | "Latest news on META" / "What's happening in the market?" |
| Sentiment | "News sentiment on LEN" / "Is the market bullish?" |
| Earnings | "When does NVDA report?" / "Does AAPL beat earnings often?" |
| Analyst consensus | "What do analysts say about GOOGL?" |
| Price targets | "What's the price target for ADBE?" |
| BTST/STBT trade | "Should I do a BTST on LEN earnings?" |
| Portfolio | "Show my portfolio" / "What's my total P&L?" |
| Add holding | "Add 10 shares of AAPL at $180 to my portfolio" |
| Remove holding | "Remove TSLA from my portfolio" |
| Watchlist | "Add NVDA to my watchlist" / "Show my watchlist" |
| Comparisons | "Compare AAPL to MSFT" |
| Macro | "What's the Fed doing?" / "Is the economy strong?" |

---

## 2. Portfolio Terminal (uEquity)

A real-time portfolio tracker inspired by Bloomberg terminals.

### Summary Bar (5 Metrics)
1. **Total Portfolio Value** — sum of all market values
2. **Total Cost Basis** — sum of all cost bases
3. **Unrealized P&L** — total value minus total cost (green/red)
4. **Return %** — percentage gain or loss
5. **Position Count** — number of holdings

### 17 Data Points Per Position

#### Position Info (entered at trade time)
1. **Symbol** — stock ticker
2. **Company Name** — full legal name (auto-fetched)
3. **Quantity** — shares held
4. **Buy Price** — average purchase price
5. **Cost Basis** — buy price × quantity

#### Live Quote (real-time via WebSocket)
6. **Last** — most recent trade price (flashes green/red on update)
7. **Bid** — highest buyer price
8. **Ask** — lowest seller price
9. **Mid** — (bid + ask) / 2
10. **Spread Indicator** — visual bar showing bid/ask width

#### Day Change
11. **CHG $** — dollar change from previous close
12. **CHG %** — percentage change from previous close

#### Extended Hours (shown during pre-market / after-hours)
13. **PRE $** — pre-market price (4AM–9:30AM ET)
14. **PRE %** — pre-market percentage change
15. **AH $** — after-hours price (4PM–8PM ET)
16. **AH %** — after-hours percentage change

#### Profit & Loss
17. **Market Value** — last price × quantity
- **P&L $** — unrealized gain/loss in dollars
- **P&L %** — unrealized gain/loss percentage

### Terminal Features
- **Price flash animation** — green uptick / red downtick (500ms flash)
- **Market session detection** — PRE-MARKET / OPEN / AFTER-HOURS / CLOSED badge
- **Extended hours toggle** — auto-shows during pre/after-hours sessions
- **Add Position modal** — symbol, quantity, avg price with live cost preview
- **Remove position** — one-click removal with live feed unsubscribe
- **Totals row** — aggregated portfolio value, P&L, and position count

---

## 3. SAM's 14 Tools

### Market Data Tools
| Tool | What It Does |
|------|-------------|
| `get_price` | Current price, open, high, low, previous close, change $, change % |
| `technical_analysis` | 11 indicators (RSI, MACD, SMA-20/50, EMA-12/26, Bollinger, ATR) + 4 signals |
| `get_news` | Up to N articles with headline, summary, source, URL, datetime |
| `get_news_sentiment` | Bullish/bearish/neutral scoring per article + overall sentiment |

### Earnings Tools
| Tool | What It Does |
|------|-------------|
| `get_earnings_calendar` | 50 upcoming/recent earnings with EPS estimates and actuals |
| `get_earnings_surprises` | Last 4 quarters: actual vs estimate, surprise %, beat rate |
| `get_recommendation_trends` | Strong Buy/Buy/Hold/Sell/Strong Sell counts + consensus rating |
| `get_price_target` | Analyst targets: high, low, mean, median vs current price |

### Portfolio Tools
| Tool | What It Does |
|------|-------------|
| `get_portfolio` | Full portfolio with all 17 data points + summary metrics |
| `add_holding` | Add or update position (auto-averages if existing) |
| `remove_holding` | Remove position and unsubscribe from live feed |
| `get_watchlist` | All watchlist symbols with current price and day change |
| `add_to_watchlist` | Add symbol and auto-subscribe to live feed |
| `remove_from_watchlist` | Remove symbol and unsubscribe from live feed |

---

## 4. BTST/STBT Earnings Trade Analysis

SAM's signature feature — a rigorous framework for pre-earnings 1-day trades.

- **BTST** = Buy Today, Sell Tomorrow (bullish bet before earnings)
- **STBT** = Sell Today, Buy Tomorrow (bearish bet before earnings)

### How It Works

**Step 1: Data Collection** — SAM automatically calls 6 tools (price, technicals, sentiment, earnings history, analyst consensus, price targets)

**Step 2: 10-Factor Scoring**

| # | Factor | Bullish Signal | Bearish Signal |
|---|--------|---------------|----------------|
| 1 | Earnings History | Beat 3-4 quarters consistently | Mixed or missed recently |
| 2 | Surprise Magnitude | Beat by >5% avg | Beat by <2% or missed |
| 3 | Pre-Earnings Run | Stock flat/down (room to pop) | Already up 10%+ (priced in) |
| 4 | Technical Setup | RSI 40-60, above SMA50, MACD bullish | RSI >70, below SMA50 |
| 5 | News Sentiment | Positive news flow | Negative news flow |
| 6 | Analyst Consensus | Majority Buy, recent upgrades | Majority Hold/Sell |
| 7 | Price Target Gap | Below mean target | At or above target |
| 8 | Sector Momentum | Sector peers rallying | Sector weakness |
| 9 | Guidance Expectations | Low bar, easy to beat | High expectations |
| 10 | Macro Environment | Dovish Fed, low VIX | Hawkish Fed, high VIX |

**Step 3: Factor Scorecard** — Clean table with signal (Bull/Caution/Bear), weight (+2 to -2), and data-backed notes

**Step 4: Verdict**
| Score | Verdict |
|-------|---------|
| +5 or higher | BTST — High Conviction |
| +3 to +4 | BTST — Moderate Conviction |
| +1 to +2 | NEUTRAL — Skip |
| -1 to -2 | NEUTRAL — Skip |
| -3 to -4 | STBT — Moderate Conviction |
| -5 or lower | STBT — High Conviction |

**Step 5: Contrarian Risks** — SAM always explains what could go wrong (stock drops after beating, stock rallies after missing, and why)

---

## 5. SAM's Market Knowledge

### Sectors (All 11 GICS with Top Holdings)
Technology (XLK), Healthcare (XLV), Financials (XLF), Consumer Discretionary (XLY), Communication Services (XLC), Industrials (XLI), Consumer Staples (XLP), Energy (XLE), Utilities (XLU), Real Estate (XLRE), Materials (XLB)

### Fundamental Analysis
- Valuation: P/E, Forward P/E, PEG, P/S, P/B, EV/EBITDA, FCF Yield, Dividend Yield
- Profitability: Gross Margin, Operating Margin, Net Margin, ROE, ROIC
- Growth: Revenue Growth, EPS Growth, Same-Store Sales, Net Revenue Retention
- Balance Sheet: Debt-to-Equity, Current Ratio, Interest Coverage, Net Debt/EBITDA

### Technical Analysis
- Trend: SMA (20/50/200), EMA (12/26), Golden Cross, Death Cross
- Momentum: RSI, RSI Divergence, MACD, Stochastic
- Volatility: Bollinger Bands, ATR, Band Squeeze
- Volume: OBV, Volume Spikes, Volume Profile
- Patterns: Head & Shoulders, Double Top/Bottom, Cup & Handle, Flags, Triangles

### Macro & Economic Indicators
Fed Funds Rate, CPI, PCE, Non-Farm Payrolls, Unemployment, GDP, ISM PMI, Consumer Confidence, 10-Year Treasury Yield, Yield Curve

### Current Market Themes
AI/ML, Cloud Computing, EVs, Semiconductors, Cybersecurity, GLP-1/Weight Loss, Interest Rate Sensitive stocks

---

## 6. Real-Time Price Streaming

### Architecture
```
Finnhub WebSocket → Backend (FastAPI) → Frontend (React)
       ↓                    ↓                   ↓
  Trade-by-trade      Stores in memory     Updates UI instantly
  price data          Tracks direction      Flashes green/red
```

- **Zero-delay**: Prices stream directly from Finnhub through backend to frontend
- **Auto-subscribe**: New portfolio/watchlist symbols automatically start streaming
- **Auto-unsubscribe**: Removed symbols stop streaming
- **Fallback**: REST polling every 30 seconds if WebSocket disconnects
- **Feed status**: LIVE FEED / CONNECTING / RECONNECTING / FEED ERROR badge

---

## 7. SAM's Analysis Framework

When you ask SAM to analyze a stock, it follows a 6-step Bloomberg-style process:

1. **PRICE ACTION** — Current price, daily change, 52-week context
2. **TECHNICAL SETUP** — Trend direction, RSI, MACD, support/resistance
3. **FUNDAMENTAL VIEW** — Valuation vs sector/peers, growth trajectory
4. **SENTIMENT** — News flow, analyst ratings, institutional changes
5. **RISK FACTORS** — What could go wrong (sector, competitive, macro risks)
6. **VERDICT** — Clear bullish/bearish/neutral with conviction level

### Core Rules
- **Golden Rule**: CRITICAL THINK BEFORE ACTING — every response is evaluated for accuracy and balance
- Always fetches live data before making price claims — never guesses
- Combines technical + fundamental + sentiment for complete analysis
- Always mentions risks alongside opportunities — presents both bull and bear cases
- Challenges user bias with data — doesn't just tell you what you want to hear
- Disclaimer: "This is NOT investment advice"

---

## 8. API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/quote/{symbol}` | GET | Live stock quote |
| `/api/analysis/{symbol}` | GET | Technical analysis (11 indicators) |
| `/api/news` | GET | Market/company news |
| `/api/sentiment/{symbol}` | GET | News sentiment analysis |
| `/api/earnings` | GET | Earnings calendar |
| `/api/earnings/{symbol}` | GET | Earnings surprises (last 4 quarters) |
| `/api/recommendations/{symbol}` | GET | Analyst consensus |
| `/api/price-target/{symbol}` | GET | Analyst price targets |
| `/api/portfolio` | GET | Full portfolio with live data |
| `/api/portfolio/add` | POST | Add/update holding |
| `/api/portfolio/remove` | POST | Remove holding |
| `/api/watchlist` | GET | Watchlist with prices |
| `/ws/chat` | WebSocket | AI chat with SAM |
| `/ws/prices` | WebSocket | Real-time price streaming |

---

## 9. Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python, FastAPI, Uvicorn |
| Frontend | React 18, react-markdown |
| AI Brain | Claude Sonnet (Anthropic API) |
| Market Data | Finnhub (REST + WebSocket) |
| Technical Indicators | TA library (pandas-based) |
| Data Storage | JSON file (portfolio/watchlist), localStorage (chat) |
| Deployment | Docker Compose |
| Ports | Frontend :3000, Backend :8000 |

---

## 10. Known Limitations

1. **Finnhub Free Tier** — Stock candles (403) and price targets (403) are blocked; technical analysis and price targets require paid upgrade
2. **Read-Only** — SAM analyzes but does not execute trades (by design, for safety)
3. **News Sentiment** — Keyword-based scoring, not deep NLP
4. **Bid/Ask** — Estimated from last price on free tier (not real order book data)
5. **Extended Hours** — Pre-market/after-hours data only available during those windows
6. **60 API calls/min** — Finnhub free tier rate limit

---

## Summary

SAM is a **personal Bloomberg terminal + AI stock analyst** that provides:

- **14 specialized tools** for market data, earnings, analyst consensus, and portfolio management
- **Real-time portfolio tracking** with 17 data points per position and zero-delay streaming
- **BTST/STBT earnings trade framework** with 10-factor scoring and conviction levels
- **Bloomberg-style analysis** combining fundamental, technical, and sentiment data
- **Professional chat interface** — ask anything about the market in natural language
- **Critical thinking** — SAM challenges bias, presents both sides, and backs claims with data
