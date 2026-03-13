# Copyright (c) 2026 Smart Touch Infotech Private Limited. All rights reserved.
# SAM (Smart Analyst for Markets) — Proprietary Software

"""Historical market data — download, store, and analyze 6 months of US stock data."""
import logging
import sqlite3
import os
import time
from datetime import datetime, timedelta
import finnhub
import pandas as pd
import ta
import config

logger = logging.getLogger(__name__)
fc = finnhub.Client(api_key=config.FINNHUB_API_KEY)

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "historical.db")

# Top 50 US stocks across sectors
STOCK_UNIVERSE = {
    "Technology": ["AAPL", "MSFT", "NVDA", "AVGO", "CRM", "ORCL", "AMD", "INTC", "ADBE", "CSCO"],
    "Communication": ["META", "GOOGL", "NFLX", "DIS", "TMUS"],
    "Consumer Discretionary": ["AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX", "COST"],
    "Financials": ["JPM", "BAC", "WFC", "GS", "MS", "V", "MA"],
    "Healthcare": ["UNH", "JNJ", "LLY", "ABBV", "MRK", "PFE"],
    "Industrials": ["GE", "CAT", "BA", "HON", "UPS"],
    "Energy": ["XOM", "CVX", "COP"],
    "Consumer Staples": ["WMT", "KO", "PEP", "PG"],
    "Other": ["UBER", "CRWD", "PANW", "PYPL"],
}

ALL_SYMBOLS = sorted(set(s for syms in STOCK_UNIVERSE.values() for s in syms))

SYMBOL_SECTOR = {}
for sector, symbols in STOCK_UNIVERSE.items():
    for s in symbols:
        SYMBOL_SECTOR[s] = sector


def _get_db():
    """Get SQLite connection, creating tables if needed."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS candles (
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            PRIMARY KEY (symbol, date)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS download_log (
            symbol TEXT PRIMARY KEY,
            last_download TEXT,
            rows_count INTEGER
        )
    """)
    conn.commit()
    return conn


def download_all(months: int = 6) -> dict:
    """Download historical candles for all stocks in universe."""
    conn = _get_db()
    now = int(datetime.now().timestamp())
    start = int((datetime.now() - timedelta(days=months * 30)).timestamp())

    results = {"success": [], "failed": [], "skipped": []}

    for symbol in ALL_SYMBOLS:
        # Check if already downloaded today
        row = conn.execute(
            "SELECT last_download FROM download_log WHERE symbol = ?", (symbol,)
        ).fetchone()
        if row and row[0] == datetime.now().strftime("%Y-%m-%d"):
            results["skipped"].append(symbol)
            continue

        try:
            candles = fc.stock_candles(symbol, "D", start, now)
            if candles.get("s") != "ok":
                results["failed"].append({"symbol": symbol, "reason": "no data"})
                continue

            rows = []
            for i in range(len(candles["t"])):
                date = datetime.fromtimestamp(candles["t"][i]).strftime("%Y-%m-%d")
                rows.append((
                    symbol, date,
                    candles["o"][i], candles["h"][i], candles["l"][i], candles["c"][i], candles["v"][i]
                ))

            conn.executemany(
                "INSERT OR REPLACE INTO candles (symbol, date, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?)",
                rows
            )
            conn.execute(
                "INSERT OR REPLACE INTO download_log (symbol, last_download, rows_count) VALUES (?,?,?)",
                (symbol, datetime.now().strftime("%Y-%m-%d"), len(rows))
            )
            conn.commit()
            results["success"].append({"symbol": symbol, "rows": len(rows)})
            logger.info(f"Downloaded {len(rows)} candles for {symbol}")

            # Small delay to respect rate limits
            time.sleep(0.1)

        except Exception as e:
            results["failed"].append({"symbol": symbol, "reason": str(e)})
            logger.error(f"Failed to download {symbol}: {e}")

    conn.close()
    return {
        "total_symbols": len(ALL_SYMBOLS),
        "success": len(results["success"]),
        "failed": len(results["failed"]),
        "skipped": len(results["skipped"]),
        "details": results,
    }


def get_stock_history(symbol: str, days: int = 180) -> dict:
    """Get stored historical data for a symbol with computed metrics."""
    conn = _get_db()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT date, open, high, low, close, volume FROM candles WHERE symbol = ? AND date >= ? ORDER BY date",
        (symbol.upper(), cutoff)
    ).fetchall()
    conn.close()

    if not rows:
        return {"symbol": symbol, "error": f"No historical data for {symbol}. Run download first."}

    df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])

    first_close = df["close"].iloc[0]
    last_close = df["close"].iloc[-1]
    high_price = df["high"].max()
    low_price = df["low"].min()
    avg_volume = int(df["volume"].mean())
    total_return = round(((last_close - first_close) / first_close) * 100, 2)

    # Monthly returns
    df["month"] = pd.to_datetime(df["date"]).dt.to_period("M")
    monthly = df.groupby("month").agg({"close": ["first", "last"]})
    monthly.columns = ["open", "close"]
    monthly["return_pct"] = round(((monthly["close"] - monthly["open"]) / monthly["open"]) * 100, 2)
    monthly_returns = {str(k): float(v) for k, v in monthly["return_pct"].items()}

    # Volatility (annualized)
    daily_returns = df["close"].pct_change().dropna()
    volatility = round(float(daily_returns.std() * (252 ** 0.5) * 100), 2)

    # Drawdown
    cummax = df["close"].cummax()
    drawdown = ((df["close"] - cummax) / cummax) * 100
    max_drawdown = round(float(drawdown.min()), 2)

    return {
        "symbol": symbol.upper(),
        "sector": SYMBOL_SECTOR.get(symbol.upper(), "Unknown"),
        "period": f"{df['date'].iloc[0]} to {df['date'].iloc[-1]}",
        "trading_days": len(df),
        "first_close": round(first_close, 2),
        "last_close": round(last_close, 2),
        "total_return_pct": total_return,
        "high": round(high_price, 2),
        "low": round(low_price, 2),
        "avg_daily_volume": avg_volume,
        "volatility_annualized_pct": volatility,
        "max_drawdown_pct": max_drawdown,
        "monthly_returns": monthly_returns,
    }


def compare_stocks(symbols: list[str], days: int = 180) -> dict:
    """Compare performance of multiple stocks side by side."""
    results = []
    for symbol in symbols:
        data = get_stock_history(symbol.upper(), days)
        if "error" not in data:
            results.append(data)
        else:
            results.append({"symbol": symbol.upper(), "error": data["error"]})

    # Sort by total return
    valid = [r for r in results if "total_return_pct" in r]
    valid.sort(key=lambda x: x["total_return_pct"], reverse=True)

    return {
        "comparison_period_days": days,
        "stocks_compared": len(symbols),
        "ranked_by_return": [
            {
                "rank": i + 1,
                "symbol": r["symbol"],
                "sector": r.get("sector", ""),
                "total_return_pct": r["total_return_pct"],
                "volatility_pct": r["volatility_annualized_pct"],
                "max_drawdown_pct": r["max_drawdown_pct"],
                "avg_daily_volume": r["avg_daily_volume"],
            }
            for i, r in enumerate(valid)
        ],
        "best_performer": valid[0]["symbol"] if valid else None,
        "worst_performer": valid[-1]["symbol"] if valid else None,
    }


def get_sector_performance(days: int = 180) -> dict:
    """Get performance summary by sector."""
    conn = _get_db()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    sector_data = {}
    for sector, symbols in STOCK_UNIVERSE.items():
        returns = []
        for symbol in symbols:
            rows = conn.execute(
                "SELECT close FROM candles WHERE symbol = ? AND date >= ? ORDER BY date",
                (symbol, cutoff)
            ).fetchall()
            if len(rows) >= 2:
                ret = ((rows[-1][0] - rows[0][0]) / rows[0][0]) * 100
                returns.append({"symbol": symbol, "return_pct": round(ret, 2)})

        if returns:
            avg_return = round(sum(r["return_pct"] for r in returns) / len(returns), 2)
            best = max(returns, key=lambda x: x["return_pct"])
            worst = min(returns, key=lambda x: x["return_pct"])
            sector_data[sector] = {
                "avg_return_pct": avg_return,
                "best": best,
                "worst": worst,
                "stocks_tracked": len(returns),
            }

    conn.close()

    # Sort sectors by performance
    ranked = sorted(sector_data.items(), key=lambda x: x[1]["avg_return_pct"], reverse=True)

    return {
        "period_days": days,
        "sectors": {k: v for k, v in ranked},
    }


def screen_stocks(criteria: str = "top_gainers", days: int = 30, limit: int = 10) -> dict:
    """Screen stocks by various criteria over a period.

    Criteria options:
    - top_gainers: Best performing stocks
    - top_losers: Worst performing stocks
    - most_volatile: Highest volatility
    - high_volume: Highest average volume
    - oversold: RSI < 30 (potential bounce)
    - overbought: RSI > 70 (potential pullback)
    """
    conn = _get_db()
    cutoff = (datetime.now() - timedelta(days=max(days, 60))).strftime("%Y-%m-%d")

    stocks = []
    for symbol in ALL_SYMBOLS:
        rows = conn.execute(
            "SELECT date, open, high, low, close, volume FROM candles WHERE symbol = ? AND date >= ? ORDER BY date",
            (symbol, cutoff)
        ).fetchall()
        if len(rows) < 14:
            continue

        df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
        close = df["close"]
        first = close.iloc[0]
        last = close.iloc[-1]
        ret = ((last - first) / first) * 100
        daily_ret = close.pct_change().dropna()
        vol = float(daily_ret.std() * (252 ** 0.5) * 100)
        avg_vol = int(df["volume"].mean())

        # RSI
        rsi_val = float(ta.momentum.rsi(close, window=14).iloc[-1]) if len(close) >= 15 else 50

        stocks.append({
            "symbol": symbol,
            "sector": SYMBOL_SECTOR.get(symbol, ""),
            "return_pct": round(ret, 2),
            "volatility_pct": round(vol, 2),
            "avg_volume": avg_vol,
            "rsi": round(rsi_val, 1),
            "last_price": round(last, 2),
        })

    conn.close()

    if criteria == "top_gainers":
        stocks.sort(key=lambda x: x["return_pct"], reverse=True)
    elif criteria == "top_losers":
        stocks.sort(key=lambda x: x["return_pct"])
    elif criteria == "most_volatile":
        stocks.sort(key=lambda x: x["volatility_pct"], reverse=True)
    elif criteria == "high_volume":
        stocks.sort(key=lambda x: x["avg_volume"], reverse=True)
    elif criteria == "oversold":
        stocks = [s for s in stocks if s["rsi"] < 30]
        stocks.sort(key=lambda x: x["rsi"])
    elif criteria == "overbought":
        stocks = [s for s in stocks if s["rsi"] > 70]
        stocks.sort(key=lambda x: x["rsi"], reverse=True)

    return {
        "criteria": criteria,
        "period_days": days,
        "results": stocks[:limit],
        "total_matched": len(stocks[:limit]),
    }


def get_market_summary(days: int = 30) -> dict:
    """Overall market summary from stored data."""
    conn = _get_db()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    gainers = 0
    losers = 0
    total_return = 0
    count = 0

    for symbol in ALL_SYMBOLS:
        rows = conn.execute(
            "SELECT close FROM candles WHERE symbol = ? AND date >= ? ORDER BY date",
            (symbol, cutoff)
        ).fetchall()
        if len(rows) >= 2:
            ret = ((rows[-1][0] - rows[0][0]) / rows[0][0]) * 100
            total_return += ret
            count += 1
            if ret > 0:
                gainers += 1
            else:
                losers += 1

    conn.close()

    avg_return = round(total_return / count, 2) if count else 0

    # Get sector performance too
    sector_perf = get_sector_performance(days)

    return {
        "period_days": days,
        "stocks_tracked": count,
        "gainers": gainers,
        "losers": losers,
        "avg_return_pct": avg_return,
        "market_breadth": f"{round(gainers/count*100)}% advancing" if count else "N/A",
        "sector_performance": sector_perf["sectors"],
    }


def get_download_status() -> dict:
    """Check what data we have stored."""
    conn = _get_db()
    rows = conn.execute("SELECT symbol, last_download, rows_count FROM download_log ORDER BY symbol").fetchall()
    total_candles = conn.execute("SELECT COUNT(*) FROM candles").fetchone()[0]
    symbols_stored = conn.execute("SELECT COUNT(DISTINCT symbol) FROM candles").fetchone()[0]
    date_range = conn.execute("SELECT MIN(date), MAX(date) FROM candles").fetchone()
    conn.close()

    return {
        "symbols_stored": symbols_stored,
        "total_candles": total_candles,
        "date_range": {"from": date_range[0], "to": date_range[1]} if date_range[0] else None,
        "universe_size": len(ALL_SYMBOLS),
        "downloads": [{"symbol": r[0], "last_download": r[1], "rows": r[2]} for r in rows],
    }
