# Copyright (c) 2026 Smart Touch Infotech Private Limited. All rights reserved.
# SAM (Smart Analyst for Markets) — Proprietary Software

"""FastAPI server — WebSocket chat + REST endpoints + real-time price streaming."""
import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import agent
import market_data
import portfolio
import live_feed

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


@app.get("/api/quote/{symbol}")
def quote(symbol: str):
    try:
        return market_data.get_live_quote(symbol.upper())
    except Exception as e:
        logger.error(f"Quote error for {symbol}: {e}")
        return JSONResponse(status_code=500, content={"error": f"Failed to fetch quote for {symbol}"})


@app.get("/api/analysis/{symbol}")
def analysis(symbol: str):
    try:
        return market_data.get_technical_analysis(symbol.upper())
    except Exception as e:
        logger.error(f"Analysis error for {symbol}: {e}")
        return JSONResponse(status_code=500, content={"error": f"Failed to fetch analysis for {symbol}"})


@app.get("/api/news")
def news(symbol: str = None, limit: int = 10):
    try:
        return market_data.get_news(symbol=symbol.upper() if symbol else None, limit=limit)
    except Exception as e:
        logger.error(f"News error: {e}")
        return JSONResponse(status_code=500, content={"error": "Failed to fetch news"})


@app.get("/api/sentiment/{symbol}")
def sentiment(symbol: str):
    try:
        return market_data.get_news_sentiment(symbol.upper())
    except Exception as e:
        logger.error(f"Sentiment error for {symbol}: {e}")
        return JSONResponse(status_code=500, content={"error": f"Failed to fetch sentiment for {symbol}"})


@app.get("/api/portfolio")
def get_portfolio():
    try:
        return portfolio.get_portfolio()
    except Exception as e:
        logger.error(f"Portfolio error: {e}")
        return JSONResponse(status_code=500, content={"error": "Failed to fetch portfolio"})


@app.get("/api/watchlist")
def get_watchlist():
    try:
        return portfolio.get_watchlist()
    except Exception as e:
        logger.error(f"Watchlist error: {e}")
        return JSONResponse(status_code=500, content={"error": "Failed to fetch watchlist"})


@app.get("/api/earnings")
def earnings_calendar(from_date: str = None, to_date: str = None):
    try:
        return market_data.get_earnings_calendar(from_date=from_date, to_date=to_date)
    except Exception as e:
        logger.error(f"Earnings calendar error: {e}")
        return JSONResponse(status_code=500, content={"error": "Failed to fetch earnings calendar"})


@app.get("/api/earnings/{symbol}")
def earnings_surprises(symbol: str):
    try:
        return market_data.get_earnings_surprises(symbol.upper())
    except Exception as e:
        logger.error(f"Earnings surprises error for {symbol}: {e}")
        return JSONResponse(status_code=500, content={"error": f"Failed to fetch earnings for {symbol}"})


@app.get("/api/recommendations/{symbol}")
def recommendations(symbol: str):
    try:
        return market_data.get_recommendation_trends(symbol.upper())
    except Exception as e:
        logger.error(f"Recommendations error for {symbol}: {e}")
        return JSONResponse(status_code=500, content={"error": f"Failed to fetch recommendations for {symbol}"})


@app.get("/api/price-target/{symbol}")
def price_target(symbol: str):
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
async def add_holding(req: AddHoldingRequest):
    try:
        result = portfolio.add_holding(req.symbol.upper(), req.qty, req.avg_price)
        # Auto-subscribe to live feed for new symbol
        await live_feed.subscribe(req.symbol.upper())
        return result
    except Exception as e:
        logger.error(f"Add holding error: {e}")
        return JSONResponse(status_code=500, content={"error": f"Failed to add {req.symbol}"})


@app.post("/api/portfolio/remove")
async def remove_holding(req: RemoveHoldingRequest):
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


# ─── Real-time price streaming WebSocket ───────────────────────────
@app.websocket("/ws/prices")
async def websocket_prices(websocket: WebSocket):
    """Stream real-time price updates to frontend dashboard."""
    await websocket.accept()
    live_feed.register_client(websocket)

    try:
        while True:
            # Listen for subscription commands from frontend
            data = await websocket.receive_text()
            msg = json.loads(data)
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
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    messages = []

    try:
        while True:
            data = await websocket.receive_text()
            user_msg = json.loads(data)
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
