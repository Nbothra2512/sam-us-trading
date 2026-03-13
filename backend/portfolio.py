# Copyright (c) 2026 Smart Touch Infotech Private Limited. All rights reserved.
# SAM (Smart Analyst for Markets) — Proprietary Software

"""Portfolio tracking — full uEquity terminal with all 17 data points per position.

Calculations (from uEquity spec):
  POSITION GROUP:
    Cost Basis = Buy Price x Qty

  LIVE QUOTE GROUP:
    Last = Most recent trade price
    Bid = Highest price buyers will pay (orange)
    Ask = Lowest price sellers will accept (green)
    Mid = (Bid + Ask) / 2 — fair value estimate

  DAY CHANGE GROUP:
    CHG $ = Last - Previous Close
    CHG % = ((Last - Previous Close) / Previous Close) x 100

  EXTENDED HOURS GROUP:
    Pre $ = Pre-market price (4AM-9:30AM ET)
    Pre % = ((Pre $ - Previous Close) / Previous Close) x 100
    AH $ = After-hours price (4PM-8PM ET)
    AH % = ((AH $ - Previous Close) / Previous Close) x 100

  P&L GROUP:
    Market Value = Last Price x Qty
    P&L $ = (Last Price - Buy Price) x Qty
    P&L % = ((Last Price - Buy Price) / Buy Price) x 100

  SUMMARY BAR:
    Total Portfolio Value = sum of all Market Values
    Total Cost = sum of all Cost Bases
    Unrealized P&L = Total Portfolio Value - Total Cost
    Return % = ((Total Portfolio Value - Total Cost) / Total Cost) x 100
    Position Count = number of holdings

  SPREAD:
    Spread $ = Ask - Bid
    Spread % = ((Ask - Bid) / Mid) x 100
"""
import json
import logging
import os
import finnhub
import config
from datetime import datetime

logger = logging.getLogger(__name__)

fc = finnhub.Client(api_key=config.FINNHUB_API_KEY)

PORTFOLIO_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "portfolio.json")
NAMES_CACHE = {}


def _load() -> dict:
    os.makedirs(os.path.dirname(PORTFOLIO_FILE), exist_ok=True)
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE) as f:
            return json.load(f)
    return {"holdings": [], "watchlist": []}


def _save(data: dict):
    os.makedirs(os.path.dirname(PORTFOLIO_FILE), exist_ok=True)
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _get_market_session() -> str:
    """Determine current US market session based on ET."""
    now = datetime.utcnow()
    hour_et = (now.hour - 5) % 24
    minute = now.minute
    t = hour_et * 60 + minute
    weekday = now.weekday()
    if weekday >= 5:
        return "CLOSED"
    if t < 240:
        return "CLOSED"
    elif t < 570:
        return "PRE-MARKET"
    elif t < 960:
        return "OPEN"
    elif t < 1200:
        return "AFTER-HOURS"
    else:
        return "CLOSED"


def _get_company_name(symbol: str) -> str:
    """Get company name with caching."""
    if symbol in NAMES_CACHE:
        return NAMES_CACHE[symbol]
    try:
        profile = fc.company_profile2(symbol=symbol)
        name = profile.get("name", "")
        NAMES_CACHE[symbol] = name
        return name
    except Exception:
        return ""


def _get_full_quote(symbol: str) -> dict:
    """Get quote with bid/ask from Finnhub.
    Quote fields: c=current, o=open, h=high, l=low, pc=prev close, d=change, dp=change%
    Bid/ask estimated from spread around last price for liquid stocks.
    """
    try:
        q = fc.quote(symbol)
        last = q.get("c", 0) or 0
        prev_close = q.get("pc", 0) or 0
        day_chg = q.get("d", 0) or 0
        day_chg_pct = q.get("dp", 0) or 0

        # Estimate bid/ask spread (typical spread ~0.01-0.05 for liquid large caps)
        spread_half = max(round(last * 0.0001, 2), 0.01) if last else 0.01
        bid = round(last - spread_half, 2)
        ask = round(last + spread_half, 2)
        mid = round((bid + ask) / 2, 2)

        # Spread calculation
        spread_dollar = round(ask - bid, 2)
        spread_pct = round((spread_dollar / mid) * 100, 4) if mid else 0

        return {
            "last": last,
            "bid": bid,
            "ask": ask,
            "mid": mid,
            "prev_close": prev_close,
            "day_chg": round(day_chg, 2),
            "day_chg_pct": round(day_chg_pct, 2),
            "spread_dollar": spread_dollar,
            "spread_pct": spread_pct,
            "open": q.get("o", 0),
            "high": q.get("h", 0),
            "low": q.get("l", 0),
        }
    except Exception as e:
        logger.error(f"_get_full_quote({symbol}): {e}")
        return {
            "last": 0, "bid": 0, "ask": 0, "mid": 0, "prev_close": 0,
            "day_chg": 0, "day_chg_pct": 0, "spread_dollar": 0, "spread_pct": 0,
            "open": 0, "high": 0, "low": 0,
        }


def add_holding(symbol: str, qty: float, avg_price: float) -> dict:
    data = _load()
    for h in data["holdings"]:
        if h["symbol"] == symbol:
            total_qty = h["qty"] + qty
            h["avg_price"] = round(
                ((h["avg_price"] * h["qty"]) + (avg_price * qty)) / total_qty, 2
            )
            h["qty"] = total_qty
            _save(data)
            return {"status": "updated", "holding": h}
    holding = {"symbol": symbol, "qty": qty, "avg_price": avg_price}
    data["holdings"].append(holding)
    _save(data)
    return {"status": "added", "holding": holding}


def remove_holding(symbol: str) -> dict:
    data = _load()
    data["holdings"] = [h for h in data["holdings"] if h["symbol"] != symbol]
    _save(data)
    return {"status": "removed", "symbol": symbol}


def get_portfolio() -> dict:
    """Get full uEquity portfolio with all 17 data points per position + spread indicator."""
    data = _load()
    session = _get_market_session()

    if not data["holdings"]:
        return {
            "session": session,
            "holdings": [],
            "total_value": 0,
            "total_cost": 0,
            "total_pl": 0,
            "total_pl_pct": 0,
            "position_count": 0,
        }

    holdings = []
    total_value = 0
    total_cost = 0

    for h in data["holdings"]:
        q = _get_full_quote(h["symbol"])
        name = _get_company_name(h["symbol"])

        # POSITION group
        cost_basis = round(h["avg_price"] * h["qty"], 2)

        # LIVE QUOTE group
        last = q["last"]
        bid = q["bid"]
        ask = q["ask"]
        mid = q["mid"]

        # DAY CHANGE group
        day_chg = q["day_chg"]
        day_chg_pct = q["day_chg_pct"]

        # EXTENDED HOURS group
        # Pre-market and after-hours: only available during those sessions
        pre_price = None
        pre_pct = None
        ah_price = None
        ah_pct = None

        if session == "PRE-MARKET" and q["prev_close"]:
            # During pre-market, current price IS the pre-market price
            pre_price = last
            pre_pct = round(((last - q["prev_close"]) / q["prev_close"]) * 100, 2)
        elif session == "AFTER-HOURS" and q["prev_close"]:
            # During after-hours, current price IS the after-hours price
            ah_price = last
            ah_pct = round(((last - q["prev_close"]) / q["prev_close"]) * 100, 2)

        # P&L group
        # Market Value = Last Price x Qty
        market_value = round(last * h["qty"], 2)
        # P&L $ = (Last Price - Buy Price) x Qty
        pl = round((last - h["avg_price"]) * h["qty"], 2)
        # P&L % = ((Last Price - Buy Price) / Buy Price) x 100
        pl_pct = round(((last - h["avg_price"]) / h["avg_price"]) * 100, 2) if h["avg_price"] else 0

        total_value += market_value
        total_cost += cost_basis

        holdings.append({
            # Position
            "symbol": h["symbol"],
            "name": name,
            "qty": h["qty"],
            "buy_price": h["avg_price"],
            "cost_basis": cost_basis,
            # Live quote
            "last": last,
            "bid": bid,
            "ask": ask,
            "mid": mid,
            # Spread
            "spread_dollar": q["spread_dollar"],
            "spread_pct": q["spread_pct"],
            # Day change
            "day_chg": day_chg,
            "day_chg_pct": day_chg_pct,
            # Extended hours
            "pre_price": pre_price,
            "pre_pct": pre_pct,
            "ah_price": ah_price,
            "ah_pct": ah_pct,
            # P&L
            "market_value": market_value,
            "pl": pl,
            "pl_pct": pl_pct,
        })

    # SUMMARY BAR calculations
    # Total Portfolio Value = sum of all Market Values
    total_value = round(total_value, 2)
    # Total Cost = sum of all Cost Bases
    total_cost = round(total_cost, 2)
    # Unrealized P&L = Total Portfolio Value - Total Cost
    total_pl = round(total_value - total_cost, 2)
    # Return % = ((Total Portfolio Value - Total Cost) / Total Cost) x 100
    total_pl_pct = round((total_pl / total_cost) * 100, 2) if total_cost else 0

    return {
        "session": session,
        "holdings": holdings,
        "total_value": total_value,
        "total_cost": total_cost,
        "total_pl": total_pl,
        "total_pl_pct": total_pl_pct,
        "position_count": len(holdings),
    }


def add_to_watchlist(symbol: str) -> dict:
    data = _load()
    if symbol not in data["watchlist"]:
        data["watchlist"].append(symbol)
        _save(data)
    return {"status": "added", "watchlist": data["watchlist"]}


def remove_from_watchlist(symbol: str) -> dict:
    data = _load()
    data["watchlist"] = [s for s in data["watchlist"] if s != symbol]
    _save(data)
    return {"status": "removed", "watchlist": data["watchlist"]}


def get_watchlist() -> list[dict]:
    data = _load()
    if not data.get("watchlist"):
        return []
    results = []
    for sym in data["watchlist"]:
        try:
            q = _get_full_quote(sym)
            results.append({
                "symbol": sym,
                "price": q["last"],
                "change_pct": q["day_chg_pct"],
            })
        except Exception as e:
            logger.error(f"Watchlist quote for {sym}: {e}")
            results.append({"symbol": sym, "price": 0, "change_pct": 0})
    return results
