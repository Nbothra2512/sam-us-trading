# Copyright (c) 2026 Smart Touch Infotech Private Limited. All rights reserved.
# SAM (Smart Analyst for Markets) — Proprietary Software

"""Live market data and news via Finnhub API."""
import logging
import finnhub
from datetime import datetime, timedelta
import pandas as pd
import ta
import config

logger = logging.getLogger(__name__)
fc = finnhub.Client(api_key=config.FINNHUB_API_KEY)


def get_live_quote(symbol: str) -> dict:
    """Get real-time price for a single stock."""
    try:
        q = fc.quote(symbol)
        if not q or q.get("c", 0) == 0:
            return {"symbol": symbol, "error": f"No data available for {symbol}"}
        return {
            "symbol": symbol,
            "price": q["c"],
            "open": q["o"],
            "high": q["h"],
            "low": q["l"],
            "prev_close": q["pc"],
            "change": round(q.get("d", 0) or 0, 2),
            "change_pct": round(q.get("dp", 0) or 0, 2),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"get_live_quote({symbol}): {e}")
        return {"symbol": symbol, "error": str(e)}


def get_technical_analysis(symbol: str) -> dict:
    """Run technical indicators using historical candles."""
    try:
        now = int(datetime.now().timestamp())
        start = int((datetime.now() - timedelta(days=120)).timestamp())
        candles = fc.stock_candles(symbol, "D", start, now)

        if candles.get("s") != "ok":
            return {"error": "No data available for " + symbol}

        df = pd.DataFrame({
            "close": candles["c"],
            "high": candles["h"],
            "low": candles["l"],
            "volume": candles["v"],
        })

        close = df["close"]
        high = df["high"]
        low = df["low"]

        result = {
            "symbol": symbol,
            "current_price": float(close.iloc[-1]),
            "sma_20": round(float(ta.trend.sma_indicator(close, window=20).iloc[-1]), 2),
            "sma_50": round(float(ta.trend.sma_indicator(close, window=50).iloc[-1]), 2),
            "ema_12": round(float(ta.trend.ema_indicator(close, window=12).iloc[-1]), 2),
            "ema_26": round(float(ta.trend.ema_indicator(close, window=26).iloc[-1]), 2),
            "rsi_14": round(float(ta.momentum.rsi(close, window=14).iloc[-1]), 2),
            "macd": round(float(ta.trend.macd(close).iloc[-1]), 4),
            "macd_signal": round(float(ta.trend.macd_signal(close).iloc[-1]), 4),
            "bollinger_high": round(float(ta.volatility.bollinger_hband(close).iloc[-1]), 2),
            "bollinger_low": round(float(ta.volatility.bollinger_lband(close).iloc[-1]), 2),
            "atr_14": round(float(ta.volatility.average_true_range(high, low, close).iloc[-1]), 2),
        }

        signals = []
        if result["rsi_14"] < 30:
            signals.append("RSI oversold — potential bounce")
        elif result["rsi_14"] > 70:
            signals.append("RSI overbought — potential pullback")
        else:
            signals.append(f"RSI neutral at {result['rsi_14']}")

        if result["current_price"] > result["sma_50"]:
            signals.append("Trading above SMA50 — bullish trend")
        else:
            signals.append("Trading below SMA50 — bearish trend")

        if result["macd"] > result["macd_signal"]:
            signals.append("MACD bullish crossover")
        else:
            signals.append("MACD bearish crossover")

        if result["current_price"] > result["bollinger_high"]:
            signals.append("Above upper Bollinger Band — overbought")
        elif result["current_price"] < result["bollinger_low"]:
            signals.append("Below lower Bollinger Band — oversold")

        result["signals"] = signals
        return result

    except Exception as e:
        logger.error(f"get_technical_analysis({symbol}): {e}")
        return {"error": f"Technical analysis failed for {symbol}: {e}"}


def get_news(symbol: str = None, limit: int = 10) -> list[dict]:
    """Get latest news. If symbol given, get company news. Otherwise general market news."""
    try:
        if symbol:
            today = datetime.now().strftime("%Y-%m-%d")
            week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            articles = fc.company_news(symbol, _from=week_ago, to=today)
        else:
            articles = fc.general_news("general", min_id=0)

        results = []
        for a in articles[:limit]:
            results.append({
                "headline": a.get("headline", ""),
                "summary": a.get("summary", ""),
                "source": a.get("source", ""),
                "url": a.get("url", ""),
                "datetime": datetime.fromtimestamp(a.get("datetime", 0)).isoformat(),
                "related": a.get("related", ""),
            })
        return results
    except Exception as e:
        logger.error(f"get_news({symbol}): {e}")
        return []


def get_news_sentiment(symbol: str) -> dict:
    """Get news for a symbol and analyze sentiment."""
    try:
        articles = get_news(symbol=symbol, limit=15)

        positive_words = {"surge", "jump", "gain", "rally", "rise", "bull", "beat", "record",
                          "upgrade", "buy", "growth", "profit", "high", "boost", "strong",
                          "soar", "breakout", "outperform", "up", "positive", "exceed"}
        negative_words = {"drop", "fall", "crash", "bear", "loss", "sell", "decline", "cut",
                          "downgrade", "miss", "weak", "low", "plunge", "warning", "risk",
                          "down", "negative", "concern", "fear", "layoff", "slash", "fail"}

        scored = []
        for a in articles:
            text = (a["headline"] + " " + a["summary"]).lower()
            pos = sum(1 for w in positive_words if w in text)
            neg = sum(1 for w in negative_words if w in text)
            if pos > neg:
                sentiment = "positive"
            elif neg > pos:
                sentiment = "negative"
            else:
                sentiment = "neutral"
            scored.append({**a, "sentiment": sentiment})

        pos_count = sum(1 for s in scored if s["sentiment"] == "positive")
        neg_count = sum(1 for s in scored if s["sentiment"] == "negative")
        neu_count = sum(1 for s in scored if s["sentiment"] == "neutral")

        if pos_count > neg_count:
            overall = "bullish"
        elif neg_count > pos_count:
            overall = "bearish"
        else:
            overall = "neutral"

        return {
            "symbol": symbol,
            "overall_sentiment": overall,
            "positive": pos_count,
            "negative": neg_count,
            "neutral": neu_count,
            "articles": scored,
        }
    except Exception as e:
        logger.error(f"get_news_sentiment({symbol}): {e}")
        return {"symbol": symbol, "overall_sentiment": "unknown", "error": str(e)}


def get_earnings_calendar(from_date: str = None, to_date: str = None) -> dict:
    """Get upcoming and recent earnings announcements."""
    try:
        if not from_date:
            from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        if not to_date:
            to_date = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
        data = fc.earnings_calendar(_from=from_date, to=to_date, symbol="", international=False)
        earnings = data.get("earningsCalendar", [])
        results = []
        for e in earnings[:50]:
            results.append({
                "symbol": e.get("symbol", ""),
                "date": e.get("date", ""),
                "hour": e.get("hour", ""),  # bmo=before market open, amc=after market close
                "eps_estimate": e.get("epsEstimate"),
                "eps_actual": e.get("epsActual"),
                "revenue_estimate": e.get("revenueEstimate"),
                "revenue_actual": e.get("revenueActual"),
                "quarter": e.get("quarter"),
                "year": e.get("year"),
            })
        return {"from": from_date, "to": to_date, "count": len(results), "earnings": results}
    except Exception as e:
        logger.error(f"get_earnings_calendar: {e}")
        return {"error": str(e), "earnings": []}


def get_earnings_surprises(symbol: str) -> dict:
    """Get historical earnings surprises — actual vs estimate for last 4 quarters."""
    try:
        data = fc.company_earnings(symbol, limit=4)
        results = []
        for e in data:
            eps_actual = e.get("actual")
            eps_estimate = e.get("estimate")
            surprise = e.get("surprise")
            surprise_pct = e.get("surprisePercent")
            results.append({
                "period": e.get("period", ""),
                "quarter": e.get("quarter"),
                "year": e.get("year"),
                "eps_actual": eps_actual,
                "eps_estimate": eps_estimate,
                "surprise": surprise,
                "surprise_pct": surprise_pct,
                "beat": eps_actual > eps_estimate if eps_actual is not None and eps_estimate is not None else None,
            })

        # Calculate beat rate
        beats = sum(1 for r in results if r.get("beat") is True)
        total = sum(1 for r in results if r.get("beat") is not None)
        beat_rate = round((beats / total) * 100, 0) if total > 0 else None

        return {
            "symbol": symbol,
            "beat_rate_pct": beat_rate,
            "quarters": results,
        }
    except Exception as e:
        logger.error(f"get_earnings_surprises({symbol}): {e}")
        return {"symbol": symbol, "error": str(e)}


def get_recommendation_trends(symbol: str) -> dict:
    """Get analyst recommendation trends — buy/hold/sell consensus."""
    try:
        data = fc.recommendation_trends(symbol)
        if not data:
            return {"symbol": symbol, "error": "No recommendation data"}
        latest = data[0] if data else {}
        total = (latest.get("buy", 0) + latest.get("hold", 0) + latest.get("sell", 0) +
                 latest.get("strongBuy", 0) + latest.get("strongSell", 0))
        return {
            "symbol": symbol,
            "period": latest.get("period", ""),
            "strong_buy": latest.get("strongBuy", 0),
            "buy": latest.get("buy", 0),
            "hold": latest.get("hold", 0),
            "sell": latest.get("sell", 0),
            "strong_sell": latest.get("strongSell", 0),
            "total_analysts": total,
            "consensus": _calc_consensus(latest),
        }
    except Exception as e:
        logger.error(f"get_recommendation_trends({symbol}): {e}")
        return {"symbol": symbol, "error": str(e)}


def _calc_consensus(rec: dict) -> str:
    """Calculate consensus from recommendation data."""
    sb = rec.get("strongBuy", 0)
    b = rec.get("buy", 0)
    h = rec.get("hold", 0)
    s = rec.get("sell", 0)
    ss = rec.get("strongSell", 0)
    total = sb + b + h + s + ss
    if total == 0:
        return "unknown"
    score = (sb * 5 + b * 4 + h * 3 + s * 2 + ss * 1) / total
    if score >= 4.0:
        return "Strong Buy"
    elif score >= 3.5:
        return "Buy"
    elif score >= 2.5:
        return "Hold"
    elif score >= 2.0:
        return "Sell"
    else:
        return "Strong Sell"


def get_price_target(symbol: str) -> dict:
    """Get analyst price target consensus."""
    try:
        data = fc.price_target(symbol)
        return {
            "symbol": symbol,
            "target_high": data.get("targetHigh"),
            "target_low": data.get("targetLow"),
            "target_mean": data.get("targetMean"),
            "target_median": data.get("targetMedian"),
            "last_updated": data.get("lastUpdated", ""),
        }
    except Exception as e:
        logger.error(f"get_price_target({symbol}): {e}")
        return {"symbol": symbol, "error": str(e)}
