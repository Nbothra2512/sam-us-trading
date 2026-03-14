# Copyright (c) 2026 Smart Touch Infotech Private Limited. All rights reserved.
# SAM (Smart Analyst for Markets) — Proprietary Software

"""FastAPI server — WebSocket chat + REST endpoints + real-time price streaming."""
import json
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
import agent
import market_data
import portfolio
import live_feed
import historical_data
import auth
import whatsapp
import pattern_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start live price feed on server startup, stop on shutdown."""
    await live_feed.start()
    # Auto-subscribe to all portfolio + watchlist symbols
    data = portfolio._load()
    symbols = [h["symbol"] for h in data.get("holdings", [])] + data.get("watchlist", [])
    if symbols:
        await live_feed.sync_subscriptions(symbols)
        logger.info(f"Auto-subscribed to {len(symbols)} symbols: {symbols}")
    yield
    await live_feed.stop()


app = FastAPI(title="AI Market Agent", lifespan=lifespan)

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# ─── Auth Endpoints ───────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/api/auth/login")
def login(req: LoginRequest):
    return auth.login(req.username, req.password)


@app.get("/api/auth/verify")
def verify_token(user=Depends(auth.require_auth)):
    return {"valid": True, "username": user.get("sub")}


@app.post("/api/auth/hash")
def hash_password(req: LoginRequest):
    """Utility endpoint to generate password hash. Remove in production if desired."""
    return {"hash": auth.generate_password_hash(req.password)}


# ─── Protected API Endpoints ──────────────────────────────────────
@app.get("/api/search/{query}")
def search_symbols(query: str, user=Depends(auth.require_auth)):
    try:
        return market_data.search_symbol(query)
    except Exception as e:
        logger.error(f"Search error for {query}: {e}")
        return JSONResponse(status_code=500, content={"error": f"Search failed for {query}"})


@app.get("/api/quote/{symbol}")
def quote(symbol: str, user=Depends(auth.require_auth)):
    try:
        return market_data.get_live_quote(symbol.upper())
    except Exception as e:
        logger.error(f"Quote error for {symbol}: {e}")
        return JSONResponse(status_code=500, content={"error": f"Failed to fetch quote for {symbol}"})


@app.get("/api/analysis/{symbol}")
def analysis(symbol: str, user=Depends(auth.require_auth)):
    try:
        return market_data.get_technical_analysis(symbol.upper())
    except Exception as e:
        logger.error(f"Analysis error for {symbol}: {e}")
        return JSONResponse(status_code=500, content={"error": f"Failed to fetch analysis for {symbol}"})


@app.get("/api/news")
def news(symbol: str = None, limit: int = 10, user=Depends(auth.require_auth)):
    try:
        return market_data.get_news(symbol=symbol.upper() if symbol else None, limit=limit)
    except Exception as e:
        logger.error(f"News error: {e}")
        return JSONResponse(status_code=500, content={"error": "Failed to fetch news"})


@app.get("/api/sentiment/{symbol}")
def sentiment(symbol: str, user=Depends(auth.require_auth)):
    try:
        return market_data.get_news_sentiment(symbol.upper())
    except Exception as e:
        logger.error(f"Sentiment error for {symbol}: {e}")
        return JSONResponse(status_code=500, content={"error": f"Failed to fetch sentiment for {symbol}"})


@app.get("/api/portfolio")
def get_portfolio(user=Depends(auth.require_auth)):
    try:
        return portfolio.get_portfolio()
    except Exception as e:
        logger.error(f"Portfolio error: {e}")
        return JSONResponse(status_code=500, content={"error": "Failed to fetch portfolio"})


@app.get("/api/watchlist")
def get_watchlist(user=Depends(auth.require_auth)):
    try:
        return portfolio.get_watchlist()
    except Exception as e:
        logger.error(f"Watchlist error: {e}")
        return JSONResponse(status_code=500, content={"error": "Failed to fetch watchlist"})


class WatchlistRequest(BaseModel):
    symbol: str


@app.post("/api/watchlist/add")
async def add_to_watchlist(req: WatchlistRequest, user=Depends(auth.require_auth)):
    try:
        result = portfolio.add_to_watchlist(req.symbol.upper())
        await live_feed.subscribe(req.symbol.upper())
        return result
    except Exception as e:
        logger.error(f"Add to watchlist error: {e}")
        return JSONResponse(status_code=500, content={"error": f"Failed to add {req.symbol} to watchlist"})


@app.post("/api/watchlist/remove")
async def remove_from_watchlist(req: WatchlistRequest, user=Depends(auth.require_auth)):
    try:
        result = portfolio.remove_from_watchlist(req.symbol.upper())
        data = portfolio._load()
        if req.symbol.upper() not in [h["symbol"] for h in data.get("holdings", [])]:
            await live_feed.unsubscribe(req.symbol.upper())
        return result
    except Exception as e:
        logger.error(f"Remove from watchlist error: {e}")
        return JSONResponse(status_code=500, content={"error": f"Failed to remove {req.symbol} from watchlist"})


@app.get("/api/earnings")
def earnings_calendar(from_date: str = None, to_date: str = None, user=Depends(auth.require_auth)):
    try:
        return market_data.get_earnings_calendar(from_date=from_date, to_date=to_date)
    except Exception as e:
        logger.error(f"Earnings calendar error: {e}")
        return JSONResponse(status_code=500, content={"error": "Failed to fetch earnings calendar"})


@app.get("/api/earnings/{symbol}")
def earnings_surprises(symbol: str, user=Depends(auth.require_auth)):
    try:
        return market_data.get_earnings_surprises(symbol.upper())
    except Exception as e:
        logger.error(f"Earnings surprises error for {symbol}: {e}")
        return JSONResponse(status_code=500, content={"error": f"Failed to fetch earnings for {symbol}"})


@app.get("/api/recommendations/{symbol}")
def recommendations(symbol: str, user=Depends(auth.require_auth)):
    try:
        return market_data.get_recommendation_trends(symbol.upper())
    except Exception as e:
        logger.error(f"Recommendations error for {symbol}: {e}")
        return JSONResponse(status_code=500, content={"error": f"Failed to fetch recommendations for {symbol}"})


@app.get("/api/price-target/{symbol}")
def price_target(symbol: str, user=Depends(auth.require_auth)):
    try:
        return market_data.get_price_target(symbol.upper())
    except Exception as e:
        logger.error(f"Price target error for {symbol}: {e}")
        return JSONResponse(status_code=500, content={"error": f"Failed to fetch price target for {symbol}"})


class AddHoldingRequest(BaseModel):
    symbol: str
    qty: float
    avg_price: float


class RemoveHoldingRequest(BaseModel):
    symbol: str


@app.post("/api/portfolio/add")
async def add_holding(req: AddHoldingRequest, user=Depends(auth.require_auth)):
    try:
        if req.qty <= 0 or req.avg_price <= 0:
            return JSONResponse(status_code=400, content={"error": "Quantity and price must be positive"})
        result = portfolio.add_holding(req.symbol.upper(), req.qty, req.avg_price)
        # Auto-subscribe to live feed for new symbol
        await live_feed.subscribe(req.symbol.upper())
        return result
    except Exception as e:
        logger.error(f"Add holding error: {e}")
        return JSONResponse(status_code=500, content={"error": f"Failed to add {req.symbol}"})


@app.post("/api/portfolio/remove")
async def remove_holding(req: RemoveHoldingRequest, user=Depends(auth.require_auth)):
    try:
        result = portfolio.remove_holding(req.symbol.upper())
        # Unsubscribe if not in watchlist
        data = portfolio._load()
        if req.symbol.upper() not in data.get("watchlist", []):
            await live_feed.unsubscribe(req.symbol.upper())
        return result
    except Exception as e:
        logger.error(f"Remove holding error: {e}")
        return JSONResponse(status_code=500, content={"error": f"Failed to remove {req.symbol}"})


# ─── Historical Data Endpoints ─────────────────────────────────────
@app.post("/api/historical/download")
def download_historical(user=Depends(auth.require_auth)):
    """Download 6 months of data for all 50 stocks. Takes ~30 seconds."""
    try:
        result = historical_data.download_all(months=6)
        return result
    except Exception as e:
        logger.error(f"Historical download error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/historical/status")
def historical_status(user=Depends(auth.require_auth)):
    """Check what historical data is stored."""
    try:
        return historical_data.get_download_status()
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/historical/{symbol}")
def stock_history(symbol: str, days: int = 180, user=Depends(auth.require_auth)):
    try:
        return historical_data.get_stock_history(symbol.upper(), days)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/historical/screen/{criteria}")
def stock_screen(criteria: str, days: int = 30, limit: int = 10, user=Depends(auth.require_auth)):
    try:
        return historical_data.screen_stocks(criteria, days, limit)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/market-summary")
def market_summary(days: int = 30, user=Depends(auth.require_auth)):
    try:
        return historical_data.get_market_summary(days)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/earnings-pattern/{symbol}")
def earnings_pattern(symbol: str, quarters: int = 4, user=Depends(auth.require_auth)):
    """Analyze historical price behavior around past earnings announcements."""
    try:
        return historical_data.analyze_earnings_pattern(symbol.upper(), quarters)
    except Exception as e:
        logger.error(f"Earnings pattern error for {symbol}: {e}")
        return JSONResponse(status_code=500, content={"error": f"Failed to analyze earnings pattern for {symbol}"})


# ─── Pattern Recognition Endpoints ────────────────────────────────
# NOTE: Specific routes MUST come before {symbol} wildcard

@app.get("/api/patterns/portfolio")
def portfolio_patterns(user=Depends(auth.require_auth)):
    """Run pattern analysis on all portfolio holdings."""
    try:
        import portfolio as port
        data = port._load()
        symbols = [h["symbol"] for h in data.get("holdings", [])]
        return pattern_engine.analyze_portfolio_patterns(symbols)
    except Exception as e:
        logger.error(f"Portfolio pattern analysis error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/patterns/market/scan")
def market_patterns(limit: int = 20, user=Depends(auth.require_auth)):
    """Scan all S&P 500 stocks for active patterns."""
    try:
        return pattern_engine.scan_market_patterns(limit)
    except Exception as e:
        logger.error(f"Market pattern scan error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/patterns/backtest/{symbol}")
def backtest(symbol: str, user=Depends(auth.require_auth)):
    """Backtest pattern reliability for a stock using 10-year history."""
    try:
        return pattern_engine.backtest_patterns(symbol.upper())
    except Exception as e:
        logger.error(f"Backtest error for {symbol}: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/patterns/{symbol}")
def stock_patterns(symbol: str, days: int = 252, user=Depends(auth.require_auth)):
    """Full pattern recognition scan for a single stock."""
    try:
        return pattern_engine.scan_stock_patterns(symbol.upper(), days)
    except Exception as e:
        logger.error(f"Pattern scan error for {symbol}: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# ─── News Feed ────────────────────────────────────────────────────
@app.get("/api/news-feed")
def news_feed(user=Depends(auth.require_auth)):
    """Combined news feed with sentiment for portfolio holdings + general market."""
    try:
        from datetime import datetime

        # Get portfolio symbols
        port_data = portfolio._load()
        symbols = [h["symbol"] for h in port_data.get("holdings", [])]

        positive_words = {"surge", "jump", "gain", "rally", "rise", "bull", "beat", "record",
                          "upgrade", "buy", "growth", "profit", "high", "boost", "strong",
                          "soar", "breakout", "outperform", "up", "positive", "exceed"}
        negative_words = {"drop", "fall", "crash", "bear", "loss", "sell", "decline", "cut",
                          "downgrade", "miss", "weak", "low", "plunge", "warning", "risk",
                          "down", "negative", "concern", "fear", "layoff", "slash", "fail"}

        def score_sentiment(headline, summary=""):
            text = (headline + " " + summary).lower()
            pos = sum(1 for w in positive_words if w in text)
            neg = sum(1 for w in negative_words if w in text)
            if pos > neg:
                return "positive", min(pos - neg, 5) / 5
            elif neg > pos:
                return "negative", min(neg - pos, 5) / 5
            return "neutral", 0

        all_news = []
        seen_headlines = set()

        # Portfolio stock news
        for sym in symbols[:10]:  # Limit to avoid rate limits
            try:
                articles = market_data.get_news(symbol=sym, limit=5)
                for a in articles:
                    if a["headline"] in seen_headlines:
                        continue
                    seen_headlines.add(a["headline"])
                    sent, score = score_sentiment(a["headline"], a.get("summary", ""))
                    all_news.append({
                        **a,
                        "sentiment": sent,
                        "sentiment_score": round(score, 2),
                        "portfolio_related": True,
                        "symbol": sym,
                    })
            except Exception:
                continue

        # General market news
        try:
            general = market_data.get_news(limit=15)
            for a in general:
                if a["headline"] in seen_headlines:
                    continue
                seen_headlines.add(a["headline"])
                sent, score = score_sentiment(a["headline"], a.get("summary", ""))
                all_news.append({
                    **a,
                    "sentiment": sent,
                    "sentiment_score": round(score, 2),
                    "portfolio_related": False,
                    "symbol": a.get("related", ""),
                })
        except Exception:
            pass

        # Sort by datetime descending
        all_news.sort(key=lambda x: x.get("datetime", ""), reverse=True)

        pos_count = sum(1 for n in all_news if n["sentiment"] == "positive")
        neg_count = sum(1 for n in all_news if n["sentiment"] == "negative")

        return {
            "articles": all_news[:50],
            "total": len(all_news),
            "sentiment_summary": {
                "positive": pos_count,
                "negative": neg_count,
                "neutral": len(all_news) - pos_count - neg_count,
                "overall": "bullish" if pos_count > neg_count else "bearish" if neg_count > pos_count else "neutral",
            },
        }
    except Exception as e:
        logger.error(f"News feed error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# ─── Reports / Export ─────────────────────────────────────────────
@app.get("/api/reports/portfolio-pdf")
def portfolio_pdf(user=Depends(auth.require_auth)):
    """Generate downloadable PDF portfolio analysis report."""
    try:
        from io import BytesIO
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from datetime import datetime

        buf = BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
        styles = getSampleStyleSheet()
        elements = []

        # Custom styles
        title_style = ParagraphStyle("Title2", parent=styles["Title"], fontSize=20, textColor=colors.HexColor("#1e293b"))
        subtitle_style = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#64748b"))
        section_style = ParagraphStyle("Section", parent=styles["Heading2"], fontSize=14, textColor=colors.HexColor("#1e293b"),
                                       spaceBefore=16, spaceAfter=8)
        alert_style = ParagraphStyle("Alert", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#ef4444"))

        # Header
        elements.append(Paragraph("SAM — Portfolio Analysis Report", title_style))
        elements.append(Paragraph(f"Smart Analyst for Markets | Generated {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", subtitle_style))
        elements.append(Paragraph("Copyright Smart Touch Infotech Private Limited", subtitle_style))
        elements.append(Spacer(1, 16))

        # Portfolio summary
        port_data = portfolio.get_portfolio()
        holdings = port_data.get("holdings", [])

        elements.append(Paragraph("Portfolio Summary", section_style))
        summary_data = [
            ["Total Value", "Total Cost", "Unrealized P&L", "Return %", "Positions"],
            [
                f"${port_data.get('total_value', 0):,.2f}",
                f"${port_data.get('total_cost', 0):,.2f}",
                f"${port_data.get('total_pl', 0):,.2f}",
                f"{port_data.get('total_pl_pct', 0):.2f}%",
                str(port_data.get("position_count", 0)),
            ],
        ]
        t = Table(summary_data, colWidths=[1.4*inch]*5)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 12))

        # Holdings table
        if holdings:
            elements.append(Paragraph("Holdings", section_style))
            h_data = [["Symbol", "Qty", "Buy", "Last", "P&L $", "P&L %", "Day %"]]
            for h in holdings:
                pl_str = f"${h.get('pl', 0):,.2f}"
                h_data.append([
                    h["symbol"], str(h.get("qty", 0)), f"${h.get('buy_price', 0):.2f}",
                    f"${h.get('last', 0):.2f}", pl_str,
                    f"{h.get('pl_pct', 0):.2f}%", f"{h.get('day_chg_pct', 0):.2f}%",
                ])
            t2 = Table(h_data, colWidths=[0.8*inch, 0.6*inch, 0.8*inch, 0.8*inch, 0.9*inch, 0.8*inch, 0.7*inch])
            t2.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ]))
            elements.append(t2)
            elements.append(Spacer(1, 12))

        # Pattern analysis
        symbols = [h["symbol"] for h in holdings]
        if symbols:
            pa = pattern_engine.analyze_portfolio_patterns(symbols)

            elements.append(Paragraph("Pattern Analysis", section_style))
            pa_data = [["Symbol", "Signal", "Trend", "RSI", "Support", "Resistance"]]
            for ph in pa.get("holdings", []):
                if ph.get("error"):
                    continue
                pa_data.append([
                    ph["symbol"],
                    ph.get("signal", "—"),
                    ph.get("trend", "—"),
                    f"{ph.get('rsi', 0):.0f}" if ph.get("rsi") else "—",
                    f"${ph.get('nearest_support', 0):.2f}" if ph.get("nearest_support") else "—",
                    f"${ph.get('nearest_resistance', 0):.2f}" if ph.get("nearest_resistance") else "—",
                ])
            t3 = Table(pa_data, colWidths=[0.8*inch, 0.9*inch, 1.2*inch, 0.6*inch, 0.9*inch, 0.9*inch])
            t3.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ]))
            elements.append(t3)
            elements.append(Spacer(1, 12))

            # Alerts
            alerts = pa.get("alerts", [])
            if alerts:
                elements.append(Paragraph("Alerts", section_style))
                for a in alerts[:15]:
                    sev = a.get("severity", "low").upper()
                    style = alert_style if sev == "HIGH" else styles["Normal"]
                    elements.append(Paragraph(f"[{sev}] {a['message']}", ParagraphStyle(
                        "AlertItem", parent=style, fontSize=9, leftIndent=10, spaceBefore=2)))

        doc.build(elements)
        return Response(content=buf.getvalue(), media_type="application/pdf",
                        headers={"Content-Disposition": "attachment; filename=sam-portfolio-report.pdf"})

    except ImportError:
        return JSONResponse(status_code=500, content={"error": "reportlab not installed. Run: pip install reportlab"})
    except Exception as e:
        logger.error(f"PDF report error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/reports/weekly-summary")
def weekly_summary(user=Depends(auth.require_auth)):
    """Generate weekly summary — top movers, alerts, market highlights."""
    try:
        from datetime import datetime, timedelta

        port_data = portfolio.get_portfolio()
        holdings = port_data.get("holdings", [])
        symbols = [h["symbol"] for h in holdings]

        # Top movers by absolute P&L %
        movers = sorted(holdings, key=lambda h: abs(h.get("pl_pct", 0)), reverse=True)
        top_movers = [{"symbol": h["symbol"], "pl_pct": h.get("pl_pct", 0), "pl": h.get("pl", 0),
                       "day_chg_pct": h.get("day_chg_pct", 0)} for h in movers[:10]]

        # Pattern analysis
        pa = pattern_engine.analyze_portfolio_patterns(symbols) if symbols else {}

        # Market scan highlights
        try:
            market = pattern_engine.scan_market_patterns(limit=5)
            market_highlights = {
                "oversold": market.get("oversold", [])[:5],
                "overbought": market.get("overbought", [])[:5],
                "breakouts": market.get("breakouts", [])[:5],
            }
        except Exception:
            market_highlights = {}

        return {
            "generated": datetime.now().isoformat(),
            "portfolio": {
                "total_value": port_data.get("total_value", 0),
                "total_pl": port_data.get("total_pl", 0),
                "total_pl_pct": port_data.get("total_pl_pct", 0),
                "position_count": port_data.get("position_count", 0),
            },
            "top_movers": top_movers,
            "portfolio_signal": pa.get("portfolio_signal", "NEUTRAL"),
            "alerts": pa.get("alerts", [])[:10],
            "market_highlights": market_highlights,
        }
    except Exception as e:
        logger.error(f"Weekly summary error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# ─── WhatsApp Webhook (Twilio) ─────────────────────────────────────
@app.post("/api/whatsapp/webhook")
async def whatsapp_webhook(request: Request):
    """Receive incoming WhatsApp messages from Twilio, route through SAM AI agent."""
    logger.info("WhatsApp webhook hit")

    if not whatsapp.is_enabled():
        logger.warning("WhatsApp not enabled — check TWILIO env vars")
        return JSONResponse(status_code=503, content={"error": "WhatsApp not configured"})

    form = await request.form()
    params = dict(form)
    logger.info(f"WhatsApp webhook params: From={params.get('From')}, Body={params.get('Body', '')[:50]}")

    # Extract message details
    from_number = params.get("From", "").replace("whatsapp:", "")
    body = params.get("Body", "").strip()

    if not body:
        return {"status": "empty"}

    logger.info(f"WhatsApp from {from_number}: {body[:100]}")

    # Empty TwiML response — we reply via the API, not TwiML
    twiml_empty = Response(content="<Response/>", media_type="application/xml")

    if not whatsapp.is_allowed(from_number):
        logger.warning(f"WhatsApp blocked — {from_number} not in allowlist")
        return twiml_empty

    # Handle special commands
    if body.lower() in ("clear", "reset", "new chat"):
        whatsapp.clear_conversation(from_number)
        whatsapp.send_message(from_number, "Chat cleared. How can I help you?")
        return twiml_empty

    # Add user message to conversation history
    whatsapp.add_message(from_number, "user", body)

    # Route through SAM AI agent
    try:
        # Build a fresh messages list — agent.chat() mutates it with Anthropic content blocks
        chat_messages = [{"role": m["role"], "content": m["content"]} for m in whatsapp.get_conversation(from_number)]
        response = await agent.chat(chat_messages)
        whatsapp.add_message(from_number, "assistant", response)
        whatsapp.send_message(from_number, response)
    except Exception as e:
        logger.error(f"WhatsApp agent error: {e}")
        whatsapp.send_message(from_number, "Sorry, I encountered an error. Please try again.")

    return twiml_empty


@app.get("/api/whatsapp/status")
def whatsapp_status(user=Depends(auth.require_auth)):
    """Check if WhatsApp integration is active."""
    return {"enabled": whatsapp.is_enabled(), "number": whatsapp.WHATSAPP_NUMBER}


# ─── Real-time price streaming WebSocket ───────────────────────────
@app.websocket("/ws/prices")
async def websocket_prices(websocket: WebSocket, token: str = ""):
    """Stream real-time price updates to frontend dashboard."""
    if not auth.verify_ws_token(token):
        await websocket.close(code=4001, reason="Unauthorized")
        return
    await websocket.accept()
    live_feed.register_client(websocket)

    try:
        while True:
            # Listen for subscription commands from frontend
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                continue
            if msg.get("type") == "subscribe":
                symbols = msg.get("symbols", [])
                for s in symbols:
                    await live_feed.subscribe(s)
            elif msg.get("type") == "unsubscribe":
                symbols = msg.get("symbols", [])
                for s in symbols:
                    await live_feed.unsubscribe(s)
    except WebSocketDisconnect:
        pass
    finally:
        live_feed.unregister_client(websocket)


# ─── SAM Chat WebSocket ────────────────────────────────────────────
@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket, token: str = ""):
    if not auth.verify_ws_token(token):
        await websocket.close(code=4001, reason="Unauthorized")
        return
    await websocket.accept()
    messages = []
    MAX_MESSAGES = 50  # Keep context manageable

    try:
        while True:
            data = await websocket.receive_text()
            try:
                user_msg = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"type": "error", "content": "Invalid message format"}))
                continue
            user_text = user_msg.get("message", "")

            messages.append({"role": "user", "content": user_text})
            # Trim to prevent unbounded growth
            if len(messages) > MAX_MESSAGES:
                messages = messages[-MAX_MESSAGES:]
            await websocket.send_text(json.dumps({"type": "typing", "status": True}))

            try:
                response = await agent.chat(messages)
                await websocket.send_text(json.dumps({
                    "type": "message",
                    "content": response,
                }))
                # After SAM responds, sync subscriptions in case portfolio changed
                pdata = portfolio._load()
                symbols = [h["symbol"] for h in pdata.get("holdings", [])] + pdata.get("watchlist", [])
                await live_feed.sync_subscriptions(symbols)
            except Exception as e:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "content": f"Error: {str(e)}",
                }))

            await websocket.send_text(json.dumps({"type": "typing", "status": False}))

    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
