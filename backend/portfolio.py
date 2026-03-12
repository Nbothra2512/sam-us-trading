"""Portfolio tracking — read-only, no trading."""
import json
import os
import market_data

PORTFOLIO_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "portfolio.json")


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
    data = _load()
    if not data["holdings"]:
        return {"holdings": [], "total_value": 0, "total_cost": 0, "total_pl": 0, "total_pl_pct": 0}

    holdings = []
    total_value = 0
    total_cost = 0
    for h in data["holdings"]:
        quote = market_data.get_live_quote(h["symbol"])
        current_price = quote["price"]
        market_value = round(current_price * h["qty"], 2)
        cost_basis = round(h["avg_price"] * h["qty"], 2)
        pl = round(market_value - cost_basis, 2)
        pl_pct = round((pl / cost_basis) * 100, 2) if cost_basis else 0
        total_value += market_value
        total_cost += cost_basis
        holdings.append({
            "symbol": h["symbol"],
            "qty": h["qty"],
            "avg_price": h["avg_price"],
            "current_price": current_price,
            "market_value": market_value,
            "cost_basis": cost_basis,
            "pl": pl,
            "pl_pct": pl_pct,
        })

    total_pl = round(total_value - total_cost, 2)
    total_pl_pct = round((total_pl / total_cost) * 100, 2) if total_cost else 0
    return {
        "holdings": holdings,
        "total_value": round(total_value, 2),
        "total_cost": round(total_cost, 2),
        "total_pl": total_pl,
        "total_pl_pct": total_pl_pct,
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
    if not data["watchlist"]:
        return []
    results = []
    for sym in data["watchlist"]:
        quote = market_data.get_live_quote(sym)
        results.append({"symbol": sym, "price": quote["price"], "change_pct": quote["change_pct"]})
    return results
