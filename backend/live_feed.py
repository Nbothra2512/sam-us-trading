# Copyright (c) 2026 Smart Touch Infotech Private Limited. All rights reserved.
# SAM (Smart Analyst for Markets) — Proprietary Software

"""Real-time price streaming via Finnhub WebSocket.

Connects to Finnhub's WebSocket API for trade-by-trade data.
Maintains latest prices in memory and pushes to connected frontend clients.
"""
import asyncio
import json
import logging
import time
from typing import Dict, Set
import websockets
import config

logger = logging.getLogger(__name__)

# In-memory latest prices: {symbol: {price, timestamp, volume}}
LIVE_PRICES: Dict[str, dict] = {}

# Connected frontend WebSocket clients
CLIENTS: Set = set()

# Subscribed symbols
SUBSCRIBED: Set[str] = set()

# Finnhub WebSocket reference
_finnhub_ws = None
_running = False


async def _connect_finnhub():
    """Connect to Finnhub WebSocket and stream trades."""
    global _finnhub_ws, _running
    url = f"wss://ws.finnhub.io?token={config.FINNHUB_API_KEY}"
    backoff = 2

    while _running:
        try:
            async with websockets.connect(url, ping_interval=30, ping_timeout=10) as ws:
                _finnhub_ws = ws
                backoff = 2  # Reset on successful connection
                logger.info("Finnhub WebSocket connected")

                # Re-subscribe all symbols
                for sym in SUBSCRIBED:
                    await ws.send(json.dumps({"type": "subscribe", "symbol": sym}))
                    logger.info(f"Subscribed to {sym}")

                async for message in ws:
                    try:
                        data = json.loads(message)
                        if data.get("type") == "trade" and data.get("data"):
                            await _process_trades(data["data"])
                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        logger.error(f"Trade processing error: {e}")

        except websockets.exceptions.ConnectionClosed:
            logger.warning(f"Finnhub WebSocket disconnected, reconnecting in {backoff}s...")
        except Exception as e:
            logger.error(f"Finnhub WebSocket error: {e}")

        _finnhub_ws = None
        if _running:
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)  # Exponential backoff, max 60s


async def _process_trades(trades: list):
    """Process incoming trades and push to clients."""
    updates = {}

    for trade in trades:
        symbol = trade.get("s", "")
        price = trade.get("p", 0)
        volume = trade.get("v", 0)
        ts = trade.get("t", 0)

        if symbol and price:
            prev = LIVE_PRICES.get(symbol, {}).get("price")
            LIVE_PRICES[symbol] = {
                "price": price,
                "volume": volume,
                "timestamp": ts,
                "direction": "up" if prev is None or price >= prev else "down",
            }
            updates[symbol] = LIVE_PRICES[symbol]

    # Push to all connected frontend clients
    if updates and CLIENTS:
        msg = json.dumps({"type": "price_update", "prices": updates})
        dead = set()
        for client in CLIENTS:
            try:
                await client.send_text(msg)
            except Exception:
                dead.add(client)
        CLIENTS -= dead


async def subscribe(symbol: str):
    """Subscribe to real-time trades for a symbol."""
    symbol = symbol.upper()
    if symbol in SUBSCRIBED:
        return
    SUBSCRIBED.add(symbol)
    if _finnhub_ws:
        try:
            await _finnhub_ws.send(json.dumps({"type": "subscribe", "symbol": symbol}))
            logger.info(f"Subscribed to {symbol}")
        except Exception as e:
            logger.error(f"Subscribe error for {symbol}: {e}")


async def unsubscribe(symbol: str):
    """Unsubscribe from real-time trades for a symbol."""
    symbol = symbol.upper()
    SUBSCRIBED.discard(symbol)
    if _finnhub_ws:
        try:
            await _finnhub_ws.send(json.dumps({"type": "unsubscribe", "symbol": symbol}))
        except Exception:
            pass


async def sync_subscriptions(symbols: list):
    """Sync subscriptions to match the given symbol list."""
    target = {s.upper() for s in symbols}
    to_add = target - SUBSCRIBED
    to_remove = SUBSCRIBED - target

    for s in to_add:
        await subscribe(s)
    for s in to_remove:
        await unsubscribe(s)


def register_client(ws):
    """Register a frontend WebSocket client for price updates."""
    CLIENTS.add(ws)
    logger.info(f"Price feed client connected ({len(CLIENTS)} total)")


def unregister_client(ws):
    """Unregister a frontend WebSocket client."""
    CLIENTS.discard(ws)
    logger.info(f"Price feed client disconnected ({len(CLIENTS)} total)")


def get_live_price(symbol: str) -> dict | None:
    """Get latest streamed price for a symbol (from memory, no API call)."""
    return LIVE_PRICES.get(symbol.upper())


async def start():
    """Start the Finnhub WebSocket connection."""
    global _running
    _running = True
    asyncio.create_task(_connect_finnhub())
    logger.info("Live feed started")


async def stop():
    """Stop the Finnhub WebSocket connection."""
    global _running
    _running = False
    if _finnhub_ws:
        await _finnhub_ws.close()
