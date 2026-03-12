"""FastAPI server — WebSocket chat + REST endpoints."""
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import agent
import market_data
import portfolio

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
    return market_data.get_live_quote(symbol.upper())


@app.get("/api/analysis/{symbol}")
def analysis(symbol: str):
    return market_data.get_technical_analysis(symbol.upper())


@app.get("/api/news")
def news(symbol: str = None, limit: int = 10):
    return market_data.get_news(symbol=symbol.upper() if symbol else None, limit=limit)


@app.get("/api/sentiment/{symbol}")
def sentiment(symbol: str):
    return market_data.get_news_sentiment(symbol.upper())


@app.get("/api/portfolio")
def get_portfolio():
    return portfolio.get_portfolio()


@app.get("/api/watchlist")
def get_watchlist():
    return portfolio.get_watchlist()


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
