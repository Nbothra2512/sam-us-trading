"""FastAPI server — WebSocket chat + REST endpoints."""
import json
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import agent
import market_data
import portfolio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Market Agent")

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
def add_holding(req: AddHoldingRequest):
    try:
        return portfolio.add_holding(req.symbol.upper(), req.qty, req.avg_price)
    except Exception as e:
        logger.error(f"Add holding error: {e}")
        return JSONResponse(status_code=500, content={"error": f"Failed to add {req.symbol}"})


@app.post("/api/portfolio/remove")
def remove_holding(req: RemoveHoldingRequest):
    try:
        return portfolio.remove_holding(req.symbol.upper())
    except Exception as e:
        logger.error(f"Remove holding error: {e}")
        return JSONResponse(status_code=500, content={"error": f"Failed to remove {req.symbol}"})


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
