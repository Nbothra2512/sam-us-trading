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
    """Connect to Finnhub WebSocket and stream trades.

    Uses exponential backoff with special handling for 429 (rate limit).
    Finnhub allows 1 WebSocket connection per API key — rapid reconnects trigger 429.
    """
    global _finnhub_ws, _running
    url = f"wss://ws.finnhub.io?token={config.FINNHUB_API_KEY}"
    backoff = 5
    _consecutive_failures = 0

    while _running:
        try:
            async with websockets.connect(
                url,
                ping_interval=25,
                ping_timeout=25,
                close_timeout=10,
                max_size=2**20,  # 1MB max message
            ) as ws:
                _finnhub_ws = ws
                backoff = 5  # Reset on successful connection
                _consecutive_failures = 0
                logger.info("Finnhub WebSocket connected")

                # Re-subscribe all symbols with small delay to avoid burst
                for i, sym in enumerate(SUBSCRIBED):
                    await ws.send(json.dumps({"type": "subscribe", "symbol": sym}))
                    if i > 0 and i % 10 == 0:
                        await asyncio.sleep(0.5)  # Pace subscriptions
                logger.info(f"Subscribed to {len(SUBSCRIBED)} symbols")

                async for message in ws:
                    try:
                        data = json.loads(message)
                        if data.get("type") == "trade" and data.get("data"):
                            await _process_trades(data["data"])
                        elif data.get("type") == "ping":
                            await ws.send(json.dumps({"type": "pong"}))
                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        logger.error(f"Trade processing error: {e}")

        except websockets.exceptions.ConnectionClosedOK:
            logger.info("Finnhub WebSocket closed normally")
        except websockets.exceptions.ConnectionClosedError as e:
            _consecutive_failures += 1
            logger.warning(f"Finnhub WebSocket disconnected (code={e.code}), attempt #{_consecutive_failures}")
        except asyncio.TimeoutError:
            _consecutive_failures += 1
            logger.warning(f"Finnhub WebSocket timeout, attempt #{_consecutive_failures}")
        except Exception as e:
            _consecutive_failures += 1
            err_str = str(e)
            if "429" in err_str:
                # Rate limited — back off aggressively
                backoff = max(backoff, 60)
                logger.error(f"Finnhub 429 rate limited — waiting {backoff}s before retry")
            else:
                logger.error(f"Finnhub WebSocket error: {e}")

        _finnhub_ws = None
        if _running:
            await asyncio.sleep(backoff)
            # Exponential backoff: 5 → 10 → 20 → 40 → 60 → 120 (max)
            backoff = min(backoff * 2, 120)


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
