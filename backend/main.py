# Copyright (c) 2026 Smart Touch Infotech Private Limited. All rights reserved.
# SAM (Smart Analyst for Markets) — Proprietary Software

"""FastAPI server — WebSocket chat + REST endpoints + real-time price streaming."""
import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import agent
import market_data
import portfolio
import live_feed
import historical_data
import auth

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
