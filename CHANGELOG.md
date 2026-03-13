# CHANGELOG — SAM (Smart Analyst for Markets)

> Copyright (c) 2026 Smart Touch Infotech Private Limited. All rights reserved.
> Auto-updated with every release. All dates in IST (UTC+5:30).

---

## [v1.12.0] — 2026-03-14

### Copyright: All Source Files
- Added copyright headers to 7 remaining files: `__init__.py`, `PROJECT_OVERVIEW.md`, `PROJECT_STRUCTURE.md`, `DISCOVERY.md`, `SYSTEM_PROMPT.md`, `.env.example`, `favicon.svg`
- All 28 source files now carry: "Copyright (c) 2026 Smart Touch Infotech Private Limited"

**Commit:** `24f2c32`

---

## [v1.11.0] — 2026-03-14

### Enhancement: Professional Response Formatting
- **SAM system prompt** — Added comprehensive RESPONSE FORMATTING section with strict Markdown rules:
  - `##` headings for sections, `###` for sub-sections
  - Clean tables (2-4 columns, compact, aligned)
  - `> blockquotes` for verdicts and key takeaways
  - `code` backticks for price levels
  - Emoji only as section markers on headings, not scattered in body text
  - Clear verdict block format with conviction level
- **Chat CSS overhaul** — Professional financial terminal styling:
  - Tables: rounded corners, header uppercase, alternating row shading, hover highlight
  - Headings: h1 accent-colored, h2 with border-bottom divider, h3 for sub-sections
  - Blockquotes: left accent border with subtle background
  - Code: accent-tinted background with mono font
  - Lists: accent-colored markers, proper spacing
  - Links: underline on hover
  - Assistant messages: wider max-width (95%), more padding

**Files changed:** `agent.py`, `App.css`

---

## [v1.10.0] — 2026-03-14

### Bug Fixes (Comprehensive Code Review — 10 bugs fixed)
- **FIX: Shared refs between desktop/mobile** — `messagesEndRef` and `inputRef` were shared across desktop and mobile layouts, causing scroll-to-bottom and input focus to target the wrong (hidden) panel. Split into `desktopEndRef`/`mobileEndRef` and `desktopInputRef`/`mobileInputRef`.
- **FIX: fetchPortfolio stale closure** — `portfolio` and `prevPrices` state variables in `useCallback` deps caused stale closures, so flash animations never triggered after mount. Replaced with `portfolioRef`/`prevPricesRef` refs.
- **FIX: 5% alert toast spam** — Toast notification for 5%+ moves fired every 30 seconds on each portfolio refresh. Added `alertedSymbolsRef` (Set) to deduplicate — now fires once per symbol per session.
- **FIX: Earnings check permanently stuck** — `_earningsChecked` flag was mutated onto the API response object and persisted forever via `prevPortfolioRef`. Replaced with `earningsCheckDateRef` that resets daily.
- **FIX: Mobile missing chat tabs** — Mobile layout had no chat tab UI. Extracted shared `ChatPanel` component used by both desktop and mobile, with full tab support on both.
- **FIX: WebSocket resubscribe on symbol swap** — Resubscribe effect only tracked `holdings.length`, so swapping AAPL→MSFT (same count) wouldn't resubscribe. Changed dependency to `holdingSymbols` string.
- **FIX: Message content overflow** — Tables and code blocks in assistant messages could overflow chat bubbles. Added `overflow-x: auto` to `.message-content`.
- **FIX: Mobile chat input not pinned** — `.mobile-chat-panel` missing `height: 100%`, causing chat input to scroll away. Fixed.
- **FIX: DST bug in market session** — `_get_market_session()` used hardcoded `UTC-5` offset, making session labels wrong 8 months/year during daylight saving time. Now uses `zoneinfo.ZoneInfo("America/New_York")`.
- **FIX: WebSocket JSON parse crash** — Malformed JSON in either WebSocket handler (`/ws/prices`, `/ws/chat`) would crash the connection. Added try/catch with graceful handling.

### Code Quality
- Moved `TICKER_INDICES` to module scope (fixes `useCallback` dependency warning)
- Wrapped `handleLogout` in `useCallback`, added to `useEffect` deps
- Added try/catch for WebSocket `onmessage` JSON parse in frontend

**Files changed:** `App.js`, `App.css`, `Portfolio.js`, `main.py`, `portfolio.py`
**Commit:** `592ccaf`

---

## [v1.9.0] — 2026-03-14

### Feature: Symbol Search
- Search bar now resolves company names (e.g., "Apple") to ticker symbols ("AAPL") via Finnhub `symbol_lookup` API
- Direct ticker queries (1-5 chars) go straight to quote API for speed
- New backend endpoint: `GET /api/search/{query}`
- New function: `market_data.search_symbol()` — filters to Common Stock, excludes dotted symbols

**Files changed:** `market_data.py`, `main.py`, `Portfolio.js`
**Commit:** `e07a189`

---

## [v1.8.0] — 2026-03-14

### Feature: Mobile Responsive Layout
- Added mobile tab-based layout with bottom navigation bar (Portfolio / SAM Chat tabs)
- Desktop split layout hidden on mobile (< 768px), replaced with single-panel + nav bar
- Mobile-optimized: compact header, 2-column summary grid, 16px textarea font (prevents iOS zoom)
- Green dot indicator on Chat tab when WebSocket is connected
- Fix: Split panel heights now use `calc()` to subtract divider height (28px)

**Files changed:** `App.js`, `App.css`
**Commit:** `795dcd8`

---

## [v1.7.0] — 2026-03-14

### Feature: 9 UI Enhancements + Fancy Login Page

#### Dashboard Features
1. **Dark/Light theme toggle** — Sun/moon button in terminal header, CSS variables for both themes, persists in localStorage
2. **Watchlist panel** — Collapsible panel below summary bar, add/remove symbols, live prices
3. **Search bar** — Symbol search with popup showing price/change, auto-dismiss after 5s
4. **Market ticker tape** — Scrolling SPY/QQQ/DIA prices at top, 30s refresh, seamless CSS animation
5. **Toast notifications** — Global `showToast()` function, auto-dismiss 5s, types: alert/earnings/info
6. **Mobile responsive** — Breakpoints at 768px and 480px, compact controls on small screens
7. **P&L chart** — recharts AreaChart from localStorage snapshots (saved every 5 min)
8. **Chat history tabs** — localStorage-backed tabs, add/close/switch, persists across sessions
9. **Favicon + page title** — Custom SAM favicon (SVG), updated page title

#### Fancy Login Page
- Animated particle network background (canvas)
- 3 floating gradient orbs (blue, purple, cyan) with float animation
- Sparkline ticker bar with 8 stock prices
- Glassmorphism card with `backdrop-filter: blur(20px)`
- Icon-decorated input fields with show/hide password toggle
- Gradient submit button with hover glow + loading spinner
- Stats bar: "14 AI Tools · 51 US Stocks · Live WebSocket"
- "Markets Live" badge with pulsing green dot
- Smart Touch Infotech footer

**Files changed:** `App.js`, `App.css`, `Portfolio.js`, `Portfolio.css`, `Login.js`, `Toast.js` (new), `favicon.svg` (new), `index.html`, `package.json`
**Commit:** `aa4930a`

---

## [v1.6.0] — 2026-03-14

### Feature: Resizable Split Panels
- Split layout: top panel (uEquity Portfolio) + bottom panel (SAM Chat)
- Drag divider to resize (mouse + touch support)
- Collapse/expand buttons: full-screen portfolio or full-screen chat
- Fixed full-screen sizing: `calc(100vh - 28px)` for proper viewport fill

**Files changed:** `App.js`, `App.css`
**Commits:** `a52be22`, `504b809`

---

## [v1.5.0] — 2026-03-14

### Feature: JWT Authentication
- Custom HMAC-SHA256 JWT tokens (no external JWT library)
- SHA-256 password hashing with random salt
- Login page with SAM branding
- All REST endpoints protected with `Depends(auth.require_auth)`
- WebSocket endpoints verify token via `?token=` query param
- Logout button in terminal header (red border, hover fills red)
- Token auto-verification on page load
- Env vars: `SAM_USERNAME`, `SAM_PASSWORD_HASH`, `SAM_JWT_SECRET`
- New file: `backend/auth.py`
- New endpoints: `POST /api/auth/login`, `GET /api/auth/verify`, `POST /api/auth/hash`

**Files changed:** `auth.py` (new), `main.py`, `App.js`, `App.css`, `Login.js` (new), `Portfolio.js`
**Commits:** `754b02d`, `ee07878`, `e8e0a1f`

---

## [v1.4.0] — 2026-03-14

### Deployment: Railway (Phase 1)
- Dockerfiles updated for Railway monorepo deployment (RAILWAY_DOCKERFILE_PATH)
- Backend: dynamic `PORT` via env var (fixes Railway 502)
- WebSocket reconnect with exponential backoff (2s → 60s max) — fixes Finnhub 429
- Volume mount at `/app/data` for persistent storage
- Backend URL: `https://sam-backend-production-24ed.up.railway.app`
- Frontend URL: `https://sam-frontend-production.up.railway.app`

**Files changed:** `backend/Dockerfile`, `frontend/Dockerfile`, `live_feed.py`
**Commits:** `384db07`, `79b7593`

---

## [v1.3.0] — 2026-03-13

### Feature: 6-Month Historical Data Engine
- SQLite storage at `data/historical.db` for 51 US stocks across all GICS sectors
- 5 new SAM tools (19 total): `get_stock_history`, `compare_stocks`, `get_sector_performance`, `screen_stocks`, `get_market_summary`
- New endpoints: `POST /api/historical/download`, `GET /api/historical/status`, `GET /api/historical/{symbol}`, `GET /api/historical/screen/{criteria}`, `GET /api/market-summary`
- Stock screening by criteria: `top_gainers`, `top_losers`, `most_volatile`, `highest_volume`
- Sector performance analysis and cross-stock comparison
- New file: `backend/historical_data.py`

**Files changed:** `historical_data.py` (new), `agent.py`, `main.py`
**Commit:** `0f3817e`

---

## [v1.2.0] — 2026-03-13

### Legal: Copyright Headers
- Added "Copyright (c) 2026 Smart Touch Infotech Private Limited" to all 15 source files
- Created `WHAT_SAM_CAN_DO.md` — full capabilities document

**Files changed:** All source files, `WHAT_SAM_CAN_DO.md` (new)
**Commit:** `987f54e`

---

## [v1.1.0] — 2026-03-13

### Features
- **uEquity terminal** — Full portfolio tracker with 17 data points per position (Last, Bid, Ask, Mid, Spread, Day Change, Extended Hours, P&L)
- **BTST/STBT earnings analysis** — Buy Today Sell Tomorrow framework using earnings calendar
- **Real-time WebSocket price streaming** — Finnhub WebSocket for zero-delay price updates with flash animations
- **Error handling & production hardening** — Graceful error handling across all endpoints

**Files changed:** `portfolio.py`, `agent.py`, `main.py`, `live_feed.py`, `market_data.py`
**Commits:** `47c32ef`, `1cb8720`, `415eeaf`

---

## [v1.0.0] — 2026-03-13

### Initial Release
- SAM (Smart Analyst for Markets) — Bloomberg-grade AI stock market analyst
- 14 AI tools: live quotes, technical analysis, news, sentiment, earnings, recommendations, price targets, portfolio management, watchlist
- React frontend with chat interface
- FastAPI backend with WebSocket support
- Finnhub API integration for market data
- Docker Compose for local development
- Project documentation: `PROJECT_OVERVIEW.md`, `PROJECT_STRUCTURE.md`, `SYSTEM_PROMPT.md`, `DISCOVERY.md`

**Files changed:** All initial files
**Commit:** `8b25821`
