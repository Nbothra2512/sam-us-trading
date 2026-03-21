# Copyright (c) 2026 Smart Touch Infotech Private Limited. All rights reserved.
# SAM (Smart Analyst for Markets) — Proprietary Software

"""
Pattern Recognition Engine — trained on 10 years of S&P 500 daily data.
Detects candlestick patterns, chart patterns, support/resistance levels,
trend analysis, volume anomalies, and generates trading signals.
"""

import os
import csv
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import numpy as np
from cache import cache_get, cache_set

logger = logging.getLogger(__name__)


def _safe_float(val, default=0.0):
    """Convert to a JSON-safe float. Replace NaN/Inf with default."""
    if val is None:
        return default
    try:
        f = float(val)
        if np.isnan(f) or np.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default

# Data directories
DATA_DIR = Path(__file__).parent.parent / "US Market Data"
DAILY_DIR = DATA_DIR / "daily"
INTRADAY_DIR = DATA_DIR / "intraday_1min"
_DATA_DIR = Path(os.environ.get("DATA_DIR", str(Path(__file__).parent.parent / "data")))
PATTERN_DB = _DATA_DIR / "patterns.db"

# SQLite fallback (Railway has historical.db with 51 stocks × 6 months)
HISTORICAL_DB = _DATA_DIR / "historical.db"


# ─── Data Loading ─────────────────────────────────────────────────

def _load_from_sqlite(symbol: str, days: int = 0) -> pd.DataFrame:
    """Fallback: load daily data from historical.db SQLite (used on Railway)."""
    if not HISTORICAL_DB.exists():
        return pd.DataFrame()
    try:
        conn = sqlite3.connect(str(HISTORICAL_DB))
        if days > 0:
            query = f"SELECT date, open, high, low, close, volume FROM candles WHERE symbol = ? ORDER BY date DESC LIMIT ?"
            df = pd.read_sql_query(query, conn, params=(symbol, days))
        else:
            query = f"SELECT date, open, high, low, close, volume FROM candles WHERE symbol = ? ORDER BY date"
            df = pd.read_sql_query(query, conn, params=(symbol,))
        conn.close()
        if df.empty:
            return df
        df["date"] = pd.to_datetime(df["date"])
        df.sort_values("date", inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df
    except Exception as e:
        logger.warning(f"SQLite load for {symbol}: {e}")
        return pd.DataFrame()


def load_daily(symbol: str, days: int = 0) -> pd.DataFrame:
    """Load daily OHLCV data — tries CSV first, falls back to SQLite (Railway)."""
    # Try CSV files first (local dev with full 10-year data)
    safe = symbol.replace(".", "_")
    filepath = DAILY_DIR / f"{safe}.csv"
    if filepath.exists():
        df = pd.read_csv(filepath, parse_dates=["date"])
        df.sort_values("date", inplace=True)
        df.reset_index(drop=True, inplace=True)
        if days > 0:
            df = df.tail(days).reset_index(drop=True)
        return df

    # Fallback to SQLite (Railway deployment)
    return _load_from_sqlite(symbol, days)


def load_intraday(symbol: str) -> pd.DataFrame:
    """Load 1-min OHLCV data for a symbol from CSV."""
    safe = symbol.replace(".", "_")
    filepath = INTRADAY_DIR / f"{safe}.csv"
    if not filepath.exists():
        return pd.DataFrame()
    df = pd.read_csv(filepath, parse_dates=["datetime"])
    df.sort_values("datetime", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def _get_sqlite_symbols() -> list:
    """Get symbols available in historical.db."""
    if not HISTORICAL_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(HISTORICAL_DB))
        rows = conn.execute("SELECT DISTINCT symbol FROM candles").fetchall()
        conn.close()
        return sorted([r[0] for r in rows])
    except Exception:
        return []


def get_available_symbols() -> list:
    """List all symbols with daily data — CSV files or SQLite."""
    csv_symbols = []
    if DAILY_DIR.exists():
        csv_symbols = [f.stem.replace("_", ".") for f in DAILY_DIR.glob("*.csv")]
    sqlite_symbols = _get_sqlite_symbols()
    # Merge both sources, deduplicate
    all_symbols = sorted(set(csv_symbols + sqlite_symbols))
    return all_symbols if all_symbols else sqlite_symbols


# ─── Candlestick Pattern Detection ───────────────────────────────

def detect_candlestick_patterns(df: pd.DataFrame) -> list:
    """Detect Japanese candlestick patterns in OHLCV data.
    Returns list of {date, pattern, signal, strength} dicts.
    """
    if len(df) < 5:
        return []

    patterns = []
    o, h, l, c = df["open"].values, df["high"].values, df["low"].values, df["close"].values
    vol = df["volume"].values
    dates = df["date"].values

    for i in range(2, len(df)):
        body = abs(c[i] - o[i])
        upper_shadow = h[i] - max(o[i], c[i])
        lower_shadow = min(o[i], c[i]) - l[i]
        total_range = h[i] - l[i]
        if total_range == 0:
            continue

        bullish = c[i] > o[i]
        body_pct = body / total_range

        # Previous candles
        prev_body = abs(c[i-1] - o[i-1])
        prev_bullish = c[i-1] > o[i-1]
        prev_range = h[i-1] - l[i-1] if h[i-1] != l[i-1] else 0.01

        # Average body for context
        avg_body = np.mean([abs(c[j] - o[j]) for j in range(max(0, i-10), i)])
        if avg_body == 0:
            avg_body = 0.01

        dt = str(dates[i])[:10]

        # ── DOJI ──
        if body_pct < 0.1 and total_range > 0:
            patterns.append({"date": dt, "pattern": "Doji", "signal": "neutral", "strength": "medium",
                             "description": "Indecision — open ≈ close, market uncertain"})

        # ── HAMMER (bullish reversal) ──
        if lower_shadow > body * 2 and upper_shadow < body * 0.5 and body_pct < 0.4:
            if i >= 5 and c[i] < np.mean(c[i-5:i]):  # In downtrend
                patterns.append({"date": dt, "pattern": "Hammer", "signal": "bullish", "strength": "strong",
                                 "description": "Long lower shadow after decline — buyers stepping in"})

        # ── INVERTED HAMMER ──
        if upper_shadow > body * 2 and lower_shadow < body * 0.5 and body_pct < 0.4:
            if i >= 5 and c[i] < np.mean(c[i-5:i]):
                patterns.append({"date": dt, "pattern": "Inverted Hammer", "signal": "bullish", "strength": "medium",
                                 "description": "Long upper shadow after decline — potential reversal"})

        # ── SHOOTING STAR (bearish reversal) ──
        if upper_shadow > body * 2 and lower_shadow < body * 0.5 and body_pct < 0.4:
            if i >= 5 and c[i] > np.mean(c[i-5:i]):
                patterns.append({"date": dt, "pattern": "Shooting Star", "signal": "bearish", "strength": "strong",
                                 "description": "Long upper shadow after rally — sellers emerging"})

        # ── HANGING MAN ──
        if lower_shadow > body * 2 and upper_shadow < body * 0.5 and body_pct < 0.4:
            if i >= 5 and c[i] > np.mean(c[i-5:i]):
                patterns.append({"date": dt, "pattern": "Hanging Man", "signal": "bearish", "strength": "medium",
                                 "description": "Hammer shape at top — potential reversal down"})

        # ── BULLISH ENGULFING ──
        if bullish and not prev_bullish and body > prev_body * 1.2:
            if o[i] <= c[i-1] and c[i] >= o[i-1]:
                patterns.append({"date": dt, "pattern": "Bullish Engulfing", "signal": "bullish", "strength": "strong",
                                 "description": "Green candle fully engulfs prior red — strong buying"})

        # ── BEARISH ENGULFING ──
        if not bullish and prev_bullish and body > prev_body * 1.2:
            if o[i] >= c[i-1] and c[i] <= o[i-1]:
                patterns.append({"date": dt, "pattern": "Bearish Engulfing", "signal": "bearish", "strength": "strong",
                                 "description": "Red candle fully engulfs prior green — strong selling"})

        # ── MORNING STAR (3-candle bullish reversal) ──
        if i >= 2:
            body_2ago = abs(c[i-2] - o[i-2])
            if (c[i-2] < o[i-2] and body_2ago > avg_body  # Big red
                and abs(c[i-1] - o[i-1]) < avg_body * 0.3  # Small body (star)
                and bullish and body > avg_body):  # Big green
                patterns.append({"date": dt, "pattern": "Morning Star", "signal": "bullish", "strength": "very strong",
                                 "description": "3-candle reversal — big red, small star, big green"})

        # ── EVENING STAR (3-candle bearish reversal) ──
        if i >= 2:
            body_2ago = abs(c[i-2] - o[i-2])
            if (c[i-2] > o[i-2] and body_2ago > avg_body  # Big green
                and abs(c[i-1] - o[i-1]) < avg_body * 0.3  # Small body (star)
                and not bullish and body > avg_body):  # Big red
                patterns.append({"date": dt, "pattern": "Evening Star", "signal": "bearish", "strength": "very strong",
                                 "description": "3-candle reversal — big green, small star, big red"})

        # ── MARUBOZU (strong momentum) ──
        if body_pct > 0.9:
            signal = "bullish" if bullish else "bearish"
            patterns.append({"date": dt, "pattern": f"{'Bullish' if bullish else 'Bearish'} Marubozu",
                             "signal": signal, "strength": "strong",
                             "description": f"Full-body candle — no shadows, pure {'buying' if bullish else 'selling'} pressure"})

        # ── THREE WHITE SOLDIERS ──
        if i >= 2:
            if (c[i] > o[i] and c[i-1] > o[i-1] and c[i-2] > o[i-2]  # 3 green
                and c[i] > c[i-1] > c[i-2]  # Higher closes
                and o[i] > o[i-1] > o[i-2]  # Higher opens
                and abs(c[i]-o[i]) > avg_body * 0.7
                and abs(c[i-1]-o[i-1]) > avg_body * 0.7
                and abs(c[i-2]-o[i-2]) > avg_body * 0.7):
                patterns.append({"date": dt, "pattern": "Three White Soldiers", "signal": "bullish", "strength": "very strong",
                                 "description": "3 consecutive strong green candles — powerful uptrend"})

        # ── THREE BLACK CROWS ──
        if i >= 2:
            if (c[i] < o[i] and c[i-1] < o[i-1] and c[i-2] < o[i-2]  # 3 red
                and c[i] < c[i-1] < c[i-2]  # Lower closes
                and o[i] < o[i-1] < o[i-2]  # Lower opens
                and abs(c[i]-o[i]) > avg_body * 0.7
                and abs(c[i-1]-o[i-1]) > avg_body * 0.7
                and abs(c[i-2]-o[i-2]) > avg_body * 0.7):
                patterns.append({"date": dt, "pattern": "Three Black Crows", "signal": "bearish", "strength": "very strong",
                                 "description": "3 consecutive strong red candles — powerful downtrend"})

        # ── VOLUME SPIKE ──
        if i >= 20:
            avg_vol = np.mean(vol[i-20:i])
            if avg_vol > 0 and vol[i] > avg_vol * 2.5:
                signal = "bullish" if bullish else "bearish"
                patterns.append({"date": dt, "pattern": "Volume Spike", "signal": signal, "strength": "strong",
                                 "description": f"Volume {vol[i]/avg_vol:.1f}x above 20-day average — institutional activity"})

    return patterns


# ─── Support & Resistance Detection (Multi-Method) ───────────────

def find_support_resistance(df: pd.DataFrame, window: int = 20, num_levels: int = 5) -> dict:
    """Advanced S/R detection using 4 methods combined:
    1. Pivot points (local maxima/minima)
    2. Volume-weighted price levels (high-volume = strong S/R)
    3. Round number psychology ($50, $100, $150, etc.)
    4. Moving average confluence (where MAs cluster = dynamic S/R)
    Returns scored, ranked levels with zone ranges.
    """
    if len(df) < window * 2:
        return {"support": [], "resistance": [], "current_price": 0, "zones": []}

    highs = df["high"].values
    lows = df["low"].values
    closes = df["close"].values
    volumes = df["volume"].values
    current = closes[-1]
    dates = df["date"].values

    # ── Method 1: Pivot Points (classic) ──
    pivot_levels = []
    for w in [10, 20, 40]:  # Multiple timeframes
        for i in range(w, len(df) - min(w, 5)):
            left = max(0, i - w)
            right = min(len(df), i + w + 1)
            if highs[i] == max(highs[left:right]):
                pivot_levels.append({"price": highs[i], "type": "resistance", "method": "pivot",
                                     "date": str(dates[i])[:10], "timeframe": w})
            if lows[i] == min(lows[left:right]):
                pivot_levels.append({"price": lows[i], "type": "support", "method": "pivot",
                                     "date": str(dates[i])[:10], "timeframe": w})

    # ── Method 2: Volume Profile (high-volume price levels) ──
    # Bin prices into ranges and find where most volume concentrated
    if len(df) > 50:
        price_min, price_max = lows.min(), highs.max()
        num_bins = 50
        bin_size = (price_max - price_min) / num_bins if price_max > price_min else 1
        vol_profile = {}
        for i in range(len(df)):
            mid_price = (highs[i] + lows[i]) / 2
            bin_idx = int((mid_price - price_min) / bin_size)
            bin_idx = min(bin_idx, num_bins - 1)
            bin_price = price_min + (bin_idx + 0.5) * bin_size
            vol_profile[round(bin_price, 2)] = vol_profile.get(round(bin_price, 2), 0) + volumes[i]

        # Top volume levels become S/R
        avg_vol = np.mean(list(vol_profile.values()))
        for price, vol in sorted(vol_profile.items(), key=lambda x: -x[1])[:10]:
            if vol > avg_vol * 1.5:
                sr_type = "support" if price < current else "resistance"
                pivot_levels.append({"price": price, "type": sr_type, "method": "volume_profile",
                                     "volume_score": round(vol / avg_vol, 1)})

    # ── Method 3: Round Numbers (psychological levels) ──
    price_range = highs.max() - lows.min()
    if price_range > 0:
        # Determine round number spacing based on price
        if current > 500:
            round_step = 50
        elif current > 100:
            round_step = 25
        elif current > 50:
            round_step = 10
        elif current > 10:
            round_step = 5
        else:
            round_step = 1

        round_low = int(lows.min() / round_step) * round_step
        round_high = int(highs.max() / round_step + 1) * round_step
        for rn in range(round_low, round_high + 1, round_step):
            if abs(rn - current) / current < 0.15:  # Within 15% of current
                sr_type = "support" if rn < current else "resistance"
                # Count how many times price touched this round number
                touches = sum(1 for i in range(len(df)) if lows[i] <= rn <= highs[i])
                if touches >= 2:
                    pivot_levels.append({"price": float(rn), "type": sr_type, "method": "round_number",
                                         "touches": touches})

    # ── Method 4: Moving Average Confluence ──
    ma_periods = [20, 50, 100, 200]
    ma_values = {}
    for p in ma_periods:
        if len(df) >= p:
            ma_val = pd.Series(closes).rolling(p).mean().values[-1]
            if not np.isnan(ma_val):
                ma_values[f"MA{p}"] = round(ma_val, 2)
                sr_type = "support" if ma_val < current else "resistance"
                pivot_levels.append({"price": ma_val, "type": sr_type, "method": "moving_average",
                                     "ma_period": p})

    # ── Cluster all levels (within 1.5% of each other) ──
    def cluster_and_score(levels, threshold=0.015):
        if not levels:
            return []
        levels.sort(key=lambda x: x["price"])
        clusters = [[levels[0]]]
        for lev in levels[1:]:
            if clusters[-1] and abs(lev["price"] - clusters[-1][-1]["price"]) / max(clusters[-1][-1]["price"], 0.01) < threshold:
                clusters[-1].append(lev)
            else:
                clusters.append([lev])

        scored = []
        for cluster in clusters:
            avg_price = round(np.mean([l["price"] for l in cluster]), 2)
            methods = list(set(l["method"] for l in cluster))
            touches = len(cluster)

            # Score: more methods + more touches + volume = stronger
            score = touches * 10
            if "volume_profile" in methods:
                score += 20
            if "moving_average" in methods:
                score += 15
            if "round_number" in methods:
                score += 10
            if len(methods) >= 3:
                score += 25  # Multi-method confluence bonus

            strength = "very strong" if score >= 50 else "strong" if score >= 30 else "moderate" if score >= 15 else "weak"

            entry = {
                "level": avg_price,
                "zone_low": round(min(l["price"] for l in cluster), 2),
                "zone_high": round(max(l["price"] for l in cluster), 2),
                "touches": touches,
                "methods": methods,
                "score": score,
                "strength": strength,
            }

            # Add MA info if present
            for l in cluster:
                if l["method"] == "moving_average":
                    entry["ma_period"] = l.get("ma_period")

            scored.append(entry)

        return scored

    supports_raw = [l for l in pivot_levels if l["type"] == "support"]
    resistances_raw = [l for l in pivot_levels if l["type"] == "resistance"]

    all_supports = cluster_and_score(supports_raw)
    all_resistances = cluster_and_score(resistances_raw)

    # Sort by score, then proximity
    supports = sorted(all_supports, key=lambda x: (-x["score"], current - x["level"]))[:num_levels]
    resistances = sorted(all_resistances, key=lambda x: (-x["score"], x["level"] - current))[:num_levels]

    for s in supports:
        s["distance_pct"] = round((current - s["level"]) / current * 100, 2)
    for r in resistances:
        r["distance_pct"] = round((r["level"] - current) / current * 100, 2)

    # ── Price Position Analysis ──
    nearest_support = supports[0]["level"] if supports else None
    nearest_resistance = resistances[0]["level"] if resistances else None
    position = "neutral"
    if nearest_support and nearest_resistance:
        total_range = nearest_resistance - nearest_support
        if total_range > 0:
            pos_in_range = (current - nearest_support) / total_range
            if pos_in_range < 0.2:
                position = "near_support"
            elif pos_in_range > 0.8:
                position = "near_resistance"
            else:
                position = "mid_range"

    return {
        "current_price": round(current, 2),
        "support": supports,
        "resistance": resistances,
        "moving_averages": ma_values,
        "price_position": position,
        "nearest_support": nearest_support,
        "nearest_resistance": nearest_resistance,
    }


# ─── Trend Detection ──────────────────────────────────────────────

def detect_trend(df: pd.DataFrame) -> dict:
    """Detect current trend using multiple methods — MA crossovers, ADX, price action."""
    if len(df) < 200:
        return {"error": "Need at least 200 days of data"}

    c = df["close"].values
    h = df["high"].values
    l = df["low"].values

    # Moving averages
    sma_20 = pd.Series(c).rolling(20).mean().values
    sma_50 = pd.Series(c).rolling(50).mean().values
    sma_200 = pd.Series(c).rolling(200).mean().values
    ema_12 = pd.Series(c).ewm(span=12).mean().values
    ema_26 = pd.Series(c).ewm(span=26).mean().values

    current = c[-1]
    macd_line = ema_12[-1] - ema_26[-1]

    # Trend determination
    above_20 = current > sma_20[-1]
    above_50 = current > sma_50[-1]
    above_200 = current > sma_200[-1]
    golden_cross = sma_50[-1] > sma_200[-1] and sma_50[-5] <= sma_200[-5] if len(c) > 205 else False
    death_cross = sma_50[-1] < sma_200[-1] and sma_50[-5] >= sma_200[-5] if len(c) > 205 else False

    # ADX (Average Directional Index)
    atr_period = 14
    df_calc = df.copy()
    df_calc["tr"] = np.maximum(h - l, np.maximum(abs(h - np.roll(c, 1)), abs(l - np.roll(c, 1))))
    df_calc["dm_plus"] = np.where((h - np.roll(h, 1)) > (np.roll(l, 1) - l), np.maximum(h - np.roll(h, 1), 0), 0)
    df_calc["dm_minus"] = np.where((np.roll(l, 1) - l) > (h - np.roll(h, 1)), np.maximum(np.roll(l, 1) - l, 0), 0)

    atr = pd.Series(df_calc["tr"]).rolling(atr_period).mean().values
    di_plus = 100 * pd.Series(df_calc["dm_plus"]).rolling(atr_period).mean().values / np.where(atr > 0, atr, 1)
    di_minus = 100 * pd.Series(df_calc["dm_minus"]).rolling(atr_period).mean().values / np.where(atr > 0, atr, 1)
    dx = 100 * abs(di_plus - di_minus) / np.where((di_plus + di_minus) > 0, di_plus + di_minus, 1)
    adx = pd.Series(dx).rolling(atr_period).mean().values[-1]

    # Overall trend score (-100 to +100)
    score = 0
    score += 25 if above_20 else -25
    score += 25 if above_50 else -25
    score += 25 if above_200 else -25
    score += 15 if macd_line > 0 else -15
    score += 10 if di_plus[-1] > di_minus[-1] else -10

    if score > 50:
        trend = "Strong Uptrend"
    elif score > 20:
        trend = "Uptrend"
    elif score > -20:
        trend = "Sideways / Consolidation"
    elif score > -50:
        trend = "Downtrend"
    else:
        trend = "Strong Downtrend"

    # Recent momentum (10-day, 30-day returns)
    ret_10d = round((c[-1] / c[-10] - 1) * 100, 2) if len(c) >= 10 else 0
    ret_30d = round((c[-1] / c[-30] - 1) * 100, 2) if len(c) >= 30 else 0
    ret_90d = round((c[-1] / c[-90] - 1) * 100, 2) if len(c) >= 90 else 0

    signals = []
    if golden_cross:
        signals.append("GOLDEN CROSS — 50-day MA crossed above 200-day MA (major bullish signal)")
    if death_cross:
        signals.append("DEATH CROSS — 50-day MA crossed below 200-day MA (major bearish signal)")
    if above_200 and not above_50:
        signals.append("Pullback within uptrend — price below 50-MA but above 200-MA")
    if not above_200 and above_50:
        signals.append("Bear rally — price above 50-MA but below 200-MA")

    return {
        "trend": trend,
        "trend_score": score,
        "adx": round(adx, 1),
        "trend_strength": "Strong" if adx > 25 else "Weak" if adx < 20 else "Moderate",
        "current_price": round(current, 2),
        "sma_20": round(sma_20[-1], 2),
        "sma_50": round(sma_50[-1], 2),
        "sma_200": round(sma_200[-1], 2),
        "macd": round(macd_line, 2),
        "above_20_ma": above_20,
        "above_50_ma": above_50,
        "above_200_ma": above_200,
        "return_10d": ret_10d,
        "return_30d": ret_30d,
        "return_90d": ret_90d,
        "signals": signals,
    }


# ─── Chart Pattern Detection ─────────────────────────────────────

def detect_chart_patterns(df: pd.DataFrame) -> list:
    """Detect chart patterns — double top/bottom, head & shoulders, triangles, channels."""
    if len(df) < 60:
        return []

    patterns = []
    c = df["close"].values
    h = df["high"].values
    l = df["low"].values
    dates = df["date"].values

    # Find swing highs and lows (20-bar pivots)
    swing_highs = []
    swing_lows = []
    window = 10
    for i in range(window, len(df) - window):
        if h[i] == max(h[i-window:i+window+1]):
            swing_highs.append((i, h[i]))
        if l[i] == min(l[i-window:i+window+1]):
            swing_lows.append((i, l[i]))

    # ── DOUBLE TOP ──
    for j in range(1, len(swing_highs)):
        idx1, val1 = swing_highs[j-1]
        idx2, val2 = swing_highs[j]
        if abs(val1 - val2) / val1 < 0.02 and 15 < (idx2 - idx1) < 80:
            # Find neckline (lowest low between the two peaks)
            neckline = min(l[idx1:idx2+1])
            if c[-1] < neckline:
                patterns.append({
                    "pattern": "Double Top (confirmed)",
                    "signal": "bearish",
                    "strength": "very strong",
                    "peak1": {"date": str(dates[idx1])[:10], "price": round(val1, 2)},
                    "peak2": {"date": str(dates[idx2])[:10], "price": round(val2, 2)},
                    "neckline": round(neckline, 2),
                    "target": round(neckline - (val1 - neckline), 2),
                    "description": "Two peaks at same level with neckline break — bearish reversal",
                })
            elif c[-1] > neckline and c[-1] < val2:
                patterns.append({
                    "pattern": "Double Top (forming)",
                    "signal": "bearish_watch",
                    "strength": "moderate",
                    "peak1": {"date": str(dates[idx1])[:10], "price": round(val1, 2)},
                    "peak2": {"date": str(dates[idx2])[:10], "price": round(val2, 2)},
                    "neckline": round(neckline, 2),
                    "description": "Two equal peaks — watch for neckline break below",
                })

    # ── DOUBLE BOTTOM ──
    for j in range(1, len(swing_lows)):
        idx1, val1 = swing_lows[j-1]
        idx2, val2 = swing_lows[j]
        if abs(val1 - val2) / val1 < 0.02 and 15 < (idx2 - idx1) < 80:
            neckline = max(h[idx1:idx2+1])
            if c[-1] > neckline:
                patterns.append({
                    "pattern": "Double Bottom (confirmed)",
                    "signal": "bullish",
                    "strength": "very strong",
                    "trough1": {"date": str(dates[idx1])[:10], "price": round(val1, 2)},
                    "trough2": {"date": str(dates[idx2])[:10], "price": round(val2, 2)},
                    "neckline": round(neckline, 2),
                    "target": round(neckline + (neckline - val1), 2),
                    "description": "Two lows at same level with neckline break — bullish reversal",
                })
            elif c[-1] < neckline and c[-1] > val2:
                patterns.append({
                    "pattern": "Double Bottom (forming)",
                    "signal": "bullish_watch",
                    "strength": "moderate",
                    "trough1": {"date": str(dates[idx1])[:10], "price": round(val1, 2)},
                    "trough2": {"date": str(dates[idx2])[:10], "price": round(val2, 2)},
                    "neckline": round(neckline, 2),
                    "description": "Two equal lows — watch for neckline break above",
                })

    # ── HEAD & SHOULDERS ──
    for j in range(2, len(swing_highs)):
        left_idx, left_val = swing_highs[j-2]
        head_idx, head_val = swing_highs[j-1]
        right_idx, right_val = swing_highs[j]
        if (head_val > left_val and head_val > right_val  # Head is highest
            and abs(left_val - right_val) / left_val < 0.03  # Shoulders similar
            and 10 < (head_idx - left_idx) < 60
            and 10 < (right_idx - head_idx) < 60):
            neckline = min(l[left_idx:right_idx+1])
            patterns.append({
                "pattern": "Head & Shoulders" + (" (confirmed)" if c[-1] < neckline else " (forming)"),
                "signal": "bearish" if c[-1] < neckline else "bearish_watch",
                "strength": "very strong" if c[-1] < neckline else "strong",
                "left_shoulder": {"date": str(dates[left_idx])[:10], "price": round(left_val, 2)},
                "head": {"date": str(dates[head_idx])[:10], "price": round(head_val, 2)},
                "right_shoulder": {"date": str(dates[right_idx])[:10], "price": round(right_val, 2)},
                "neckline": round(neckline, 2),
                "description": "Classic reversal — head above two shoulders, neckline break confirms",
            })

    # ── INVERSE HEAD & SHOULDERS ──
    for j in range(2, len(swing_lows)):
        left_idx, left_val = swing_lows[j-2]
        head_idx, head_val = swing_lows[j-1]
        right_idx, right_val = swing_lows[j]
        if (head_val < left_val and head_val < right_val
            and abs(left_val - right_val) / left_val < 0.03
            and 10 < (head_idx - left_idx) < 60
            and 10 < (right_idx - head_idx) < 60):
            neckline = max(h[left_idx:right_idx+1])
            patterns.append({
                "pattern": "Inverse Head & Shoulders" + (" (confirmed)" if c[-1] > neckline else " (forming)"),
                "signal": "bullish" if c[-1] > neckline else "bullish_watch",
                "strength": "very strong" if c[-1] > neckline else "strong",
                "left_shoulder": {"date": str(dates[left_idx])[:10], "price": round(left_val, 2)},
                "head": {"date": str(dates[head_idx])[:10], "price": round(head_val, 2)},
                "right_shoulder": {"date": str(dates[right_idx])[:10], "price": round(right_val, 2)},
                "neckline": round(neckline, 2),
                "description": "Bullish reversal — inverse head below two shoulders",
            })

    # ── ASCENDING/DESCENDING TRIANGLE ──
    if len(swing_highs) >= 3 and len(swing_lows) >= 3:
        recent_highs = swing_highs[-3:]
        recent_lows = swing_lows[-3:]

        # Check if highs are flat and lows are rising (ascending triangle)
        high_vals = [v for _, v in recent_highs]
        low_vals = [v for _, v in recent_lows]
        high_range = (max(high_vals) - min(high_vals)) / max(high_vals)
        low_slope = (low_vals[-1] - low_vals[0]) / low_vals[0] if low_vals[0] > 0 else 0

        if high_range < 0.02 and low_slope > 0.02:
            patterns.append({
                "pattern": "Ascending Triangle",
                "signal": "bullish",
                "strength": "strong",
                "resistance": round(np.mean(high_vals), 2),
                "rising_support": f"{round(low_vals[0], 2)} → {round(low_vals[-1], 2)}",
                "description": "Flat resistance + rising lows — breakout above resistance likely",
            })

        # Check if lows are flat and highs are falling (descending triangle)
        low_range = (max(low_vals) - min(low_vals)) / max(low_vals) if max(low_vals) > 0 else 0
        high_slope = (high_vals[-1] - high_vals[0]) / high_vals[0] if high_vals[0] > 0 else 0

        if low_range < 0.02 and high_slope < -0.02:
            patterns.append({
                "pattern": "Descending Triangle",
                "signal": "bearish",
                "strength": "strong",
                "support": round(np.mean(low_vals), 2),
                "falling_resistance": f"{round(high_vals[0], 2)} → {round(high_vals[-1], 2)}",
                "description": "Flat support + falling highs — breakdown below support likely",
            })

    return patterns


# ─── Breakout Detection ───────────────────────────────────────────

def detect_breakouts(df: pd.DataFrame, lookback: int = 20) -> dict:
    """Detect price breakouts from consolidation ranges."""
    if len(df) < lookback + 5:
        return {"breakout": False}

    recent = df.tail(lookback + 5)
    consolidation = recent.head(lookback)
    latest = recent.tail(5)

    cons_high = _safe_float(consolidation["high"].max())
    cons_low = _safe_float(consolidation["low"].min())
    if cons_low == 0:
        return {"breakout": False}
    cons_range_pct = (cons_high - cons_low) / cons_low * 100
    avg_vol = _safe_float(consolidation["volume"].mean(), 1.0)

    current = _safe_float(latest["close"].iloc[-1])
    current_vol = _safe_float(latest["volume"].iloc[-1])

    if current == 0:
        return {"breakout": False}

    result = {
        "breakout": False,
        "consolidation_range": {"high": round(cons_high, 2), "low": round(cons_low, 2),
                                "range_pct": round(_safe_float(cons_range_pct), 2)},
        "current_price": round(current, 2),
    }

    if current > cons_high and cons_high > 0:
        result["breakout"] = True
        result["direction"] = "bullish"
        result["breakout_pct"] = round(_safe_float((current - cons_high) / cons_high * 100), 2)
        result["volume_confirmation"] = current_vol > avg_vol * 1.5
        result["description"] = f"Price broke above {lookback}-day range high ({cons_high:.2f})"
    elif current < cons_low and cons_low > 0:
        result["breakout"] = True
        result["direction"] = "bearish"
        result["breakout_pct"] = round(_safe_float((cons_low - current) / cons_low * 100), 2)
        result["volume_confirmation"] = current_vol > avg_vol * 1.5
        result["description"] = f"Price broke below {lookback}-day range low ({cons_low:.2f})"

    return result


# ─── Mean Reversion Signals ───────────────────────────────────────

def detect_mean_reversion(df: pd.DataFrame) -> dict:
    """Detect mean reversion opportunities using Bollinger Bands, RSI, and Z-score."""
    if len(df) < 50:
        return {"error": "Need at least 50 days of data"}

    c = df["close"].values
    current = c[-1]

    # Bollinger Bands
    sma_20 = pd.Series(c).rolling(20).mean().values
    std_20 = pd.Series(c).rolling(20).std().values
    upper_band = sma_20[-1] + 2 * std_20[-1]
    lower_band = sma_20[-1] - 2 * std_20[-1]
    bb_position = (current - lower_band) / (upper_band - lower_band) if (upper_band - lower_band) > 0 else 0.5

    # RSI
    deltas = pd.Series(c).diff()
    gain = deltas.where(deltas > 0, 0).rolling(14).mean().values[-1]
    loss = (-deltas.where(deltas < 0, 0)).rolling(14).mean().values[-1]
    gain = _safe_float(gain, 0.0)
    loss = _safe_float(loss, 0.0)
    if loss == 0 and gain == 0:
        rsi = 50.0  # No movement — neutral
    elif loss == 0:
        rsi = 100.0
    else:
        rsi = 100 - (100 / (1 + gain / loss))

    # Z-Score (how many std devs from 50-day mean)
    mean_50 = np.mean(c[-50:])
    std_50 = np.std(c[-50:])
    z_score = (current - mean_50) / std_50 if std_50 > 0 else 0

    # Sanitize all computed values to avoid NaN in JSON output
    rsi = _safe_float(rsi, 50.0)
    bb_position = _safe_float(bb_position, 0.5)
    upper_band = _safe_float(upper_band, current)
    lower_band = _safe_float(lower_band, current)
    z_score = _safe_float(z_score, 0.0)
    mean_50 = _safe_float(mean_50, current)

    signals = []
    signal = "neutral"

    if rsi < 30 and bb_position < 0.1:
        signal = "strong_buy"
        signals.append("OVERSOLD — RSI below 30 + price at lower Bollinger Band")
    elif rsi < 30:
        signal = "buy"
        signals.append("Oversold — RSI below 30")
    elif rsi > 70 and bb_position > 0.9:
        signal = "strong_sell"
        signals.append("OVERBOUGHT — RSI above 70 + price at upper Bollinger Band")
    elif rsi > 70:
        signal = "sell"
        signals.append("Overbought — RSI above 70")

    if z_score < -2:
        signals.append(f"Extreme low — price {abs(z_score):.1f} std devs below 50-day mean")
    elif z_score > 2:
        signals.append(f"Extreme high — price {z_score:.1f} std devs above 50-day mean")

    return {
        "signal": signal,
        "rsi": round(rsi, 1),
        "bollinger_position": round(bb_position * 100, 1),
        "upper_band": round(upper_band, 2),
        "lower_band": round(lower_band, 2),
        "z_score": round(z_score, 2),
        "current_price": round(current, 2),
        "mean_50d": round(mean_50, 2),
        "signals": signals,
    }


# ─── Full Pattern Scan (single stock) ────────────────────────────

def scan_stock_patterns(symbol: str, days: int = 252) -> dict:
    """Run full pattern analysis on a single stock using 10-year daily data."""
    cached = cache_get("patterns", symbol, days)
    if cached is not None:
        return cached

    df = load_daily(symbol, days=days)
    if df.empty:
        return {"error": f"No data found for {symbol}"}

    # Get full data for trend (needs 200+ days)
    df_full = load_daily(symbol)

    result = {
        "symbol": symbol,
        "data_points": len(df),
        "date_range": f"{str(df['date'].iloc[0])[:10]} to {str(df['date'].iloc[-1])[:10]}",
    }

    # Trend analysis (use full data)
    if len(df_full) >= 200:
        result["trend"] = detect_trend(df_full)
    else:
        result["trend"] = {"error": "Insufficient data for trend analysis"}

    # Candlestick patterns (last 60 days)
    candle_df = df.tail(60) if len(df) > 60 else df
    candles = detect_candlestick_patterns(candle_df)
    result["recent_candlestick_patterns"] = candles[-10:] if candles else []

    # Chart patterns
    result["chart_patterns"] = detect_chart_patterns(df)

    # Support & Resistance
    result["support_resistance"] = find_support_resistance(df)

    # Breakout detection
    result["breakout"] = detect_breakouts(df)

    # Mean reversion
    result["mean_reversion"] = detect_mean_reversion(df)

    # Summary signal
    signals_bullish = 0
    signals_bearish = 0

    for cp in result.get("recent_candlestick_patterns", []):
        if cp["signal"] == "bullish":
            signals_bullish += 1
        elif cp["signal"] == "bearish":
            signals_bearish += 1

    for cp in result.get("chart_patterns", []):
        if "bullish" in cp.get("signal", ""):
            signals_bullish += 2
        elif "bearish" in cp.get("signal", ""):
            signals_bearish += 2

    trend = result.get("trend", {})
    if isinstance(trend, dict) and trend.get("trend_score", 0) > 20:
        signals_bullish += 2
    elif isinstance(trend, dict) and trend.get("trend_score", 0) < -20:
        signals_bearish += 2

    mr = result.get("mean_reversion", {})
    if mr.get("signal") in ("buy", "strong_buy"):
        signals_bullish += 2
    elif mr.get("signal") in ("sell", "strong_sell"):
        signals_bearish += 2

    total = signals_bullish + signals_bearish
    if total == 0:
        result["overall_signal"] = "NEUTRAL"
        result["signal_detail"] = "No strong patterns detected"
    elif signals_bullish > signals_bearish * 1.5:
        result["overall_signal"] = "BULLISH"
        result["signal_detail"] = f"{signals_bullish} bullish vs {signals_bearish} bearish signals"
    elif signals_bearish > signals_bullish * 1.5:
        result["overall_signal"] = "BEARISH"
        result["signal_detail"] = f"{signals_bearish} bearish vs {signals_bullish} bullish signals"
    else:
        result["overall_signal"] = "MIXED"
        result["signal_detail"] = f"{signals_bullish} bullish vs {signals_bearish} bearish signals — conflicting"

    cache_set("patterns", result, 300, symbol, days)
    return result


# ─── Market-Wide Pattern Scan ─────────────────────────────────────

def scan_market_patterns(limit: int = 20) -> dict:
    """Scan all available stocks for active patterns. Returns strongest signals."""
    symbols = get_available_symbols()
    if not symbols:
        return {"error": "No data files found in US Market Data/daily/"}

    bullish = []
    bearish = []
    breakouts = []
    oversold = []
    overbought = []

    scanned = 0
    errors = 0
    for symbol in symbols:
        try:
            df = load_daily(symbol, days=252)
            if df.empty or len(df) < 50:
                continue

            # Validate required columns exist
            required_cols = {"open", "high", "low", "close", "volume"}
            if not required_cols.issubset(set(df.columns)):
                logger.warning(f"Skipping {symbol}: missing columns {required_cols - set(df.columns)}")
                continue

            # Skip stocks with NaN in critical price columns
            if df[["open", "high", "low", "close"]].iloc[-1].isna().any():
                logger.warning(f"Skipping {symbol}: NaN in latest price data")
                continue

            scanned += 1

            # Quick mean reversion check
            mr = detect_mean_reversion(df)
            if mr.get("error"):
                continue  # Not enough data for this analysis
            if mr.get("signal") in ("buy", "strong_buy"):
                oversold.append({"symbol": symbol, "rsi": _safe_float(mr["rsi"], 50),
                                 "z_score": _safe_float(mr["z_score"], 0),
                                 "bb_position": _safe_float(mr["bollinger_position"], 50)})
            elif mr.get("signal") in ("sell", "strong_sell"):
                overbought.append({"symbol": symbol, "rsi": _safe_float(mr["rsi"], 50),
                                   "z_score": _safe_float(mr["z_score"], 0),
                                   "bb_position": _safe_float(mr["bollinger_position"], 50)})

            # Breakout check
            bo = detect_breakouts(df)
            if bo.get("breakout"):
                bp = _safe_float(bo.get("breakout_pct"), 0)
                breakouts.append({"symbol": symbol, "direction": bo["direction"],
                                  "breakout_pct": bp,
                                  "volume_confirmed": bo.get("volume_confirmation", False)})

            # Recent candlestick patterns (last 3 days only)
            candles = detect_candlestick_patterns(df.tail(10))
            recent = [p for p in candles if p["strength"] in ("strong", "very strong")]
            for p in recent[-2:]:
                entry = {"symbol": symbol, "pattern": p["pattern"], "strength": p["strength"]}
                if p["signal"] == "bullish":
                    bullish.append(entry)
                elif p["signal"] == "bearish":
                    bearish.append(entry)

        except Exception as e:
            errors += 1
            logger.warning(f"Scan error for {symbol}: {e}")
            continue

    if errors > 0:
        logger.info(f"Market scan completed: {scanned} scanned, {errors} errors out of {len(symbols)} symbols")

    # Sort and limit (use _safe_float in sort keys to avoid NaN comparison issues)
    oversold.sort(key=lambda x: _safe_float(x.get("rsi"), 50))
    overbought.sort(key=lambda x: -_safe_float(x.get("rsi"), 50))
    breakouts.sort(key=lambda x: -abs(_safe_float(x.get("breakout_pct"), 0)))

    return {
        "stocks_scanned": scanned,
        "stocks_available": len(symbols),
        "stocks_errored": errors,
        "bullish_patterns": bullish[:limit],
        "bearish_patterns": bearish[:limit],
        "breakouts": breakouts[:limit],
        "oversold": oversold[:limit],
        "overbought": overbought[:limit],
        "summary": {
            "bullish_count": len(bullish),
            "bearish_count": len(bearish),
            "breakouts_count": len(breakouts),
            "oversold_count": len(oversold),
            "overbought_count": len(overbought),
        },
    }


# ─── Historical Pattern Backtesting ──────────────────────────────

def backtest_patterns(symbol: str) -> dict:
    """Backtest pattern signals on historical data — what happened after each pattern?
    Uses full 10-year history to measure pattern reliability.
    """
    cached = cache_get("backtest", symbol)
    if cached is not None:
        return cached

    df = load_daily(symbol)
    if len(df) < 252:
        return {"error": f"Need at least 1 year of data for {symbol}, got {len(df)} days"}

    candles = detect_candlestick_patterns(df)
    if not candles:
        return {"symbol": symbol, "patterns_found": 0, "message": "No patterns detected"}

    c = df["close"].values
    dates = [str(d)[:10] for d in df["date"].values]

    results = {}
    for pattern in candles:
        name = pattern["pattern"]
        if name not in results:
            results[name] = {"occurrences": 0, "signal": pattern["signal"],
                             "avg_1d": [], "avg_5d": [], "avg_10d": [], "avg_20d": []}

        # Find the index of this pattern date
        try:
            idx = dates.index(pattern["date"])
        except ValueError:
            continue

        results[name]["occurrences"] += 1

        # Forward returns after pattern
        for days, key in [(1, "avg_1d"), (5, "avg_5d"), (10, "avg_10d"), (20, "avg_20d")]:
            if idx + days < len(c):
                ret = (c[idx + days] / c[idx] - 1) * 100
                results[name][key].append(ret)

    # Aggregate
    summary = []
    for name, data in results.items():
        entry = {
            "pattern": name,
            "signal": data["signal"],
            "occurrences": data["occurrences"],
        }
        for key in ["avg_1d", "avg_5d", "avg_10d", "avg_20d"]:
            vals = data[key]
            if vals:
                entry[key.replace("avg_", "return_")] = round(np.mean(vals), 2)
                entry[key.replace("avg_", "win_rate_")] = round(
                    sum(1 for v in vals if (v > 0 if data["signal"] == "bullish" else v < 0)) / len(vals) * 100, 1
                )
            else:
                entry[key.replace("avg_", "return_")] = None
                entry[key.replace("avg_", "win_rate_")] = None

        summary.append(entry)

    # Sort by occurrences
    summary.sort(key=lambda x: -x["occurrences"])

    result = {
        "symbol": symbol,
        "data_period": f"{dates[0]} to {dates[-1]}",
        "total_patterns": len(candles),
        "unique_patterns": len(summary),
        "pattern_performance": summary,
    }
    cache_set("backtest", result, 3600, symbol)
    return result


# ─── Portfolio Analysis (scan all holdings) ───────────────────────

def analyze_portfolio_patterns(symbols: list) -> dict:
    """Run pattern analysis on all portfolio holdings.
    Returns per-stock summary + portfolio-wide alerts.
    """
    if not symbols:
        return {"holdings": [], "alerts": [], "portfolio_signal": "NEUTRAL"}

    holdings = []
    alerts = []
    bullish_count = 0
    bearish_count = 0

    for symbol in symbols:
        try:
            df = load_daily(symbol, days=252)
            if len(df) < 20:
                holdings.append({"symbol": symbol, "error": "Insufficient data"})
                continue

            entry = {"symbol": symbol}

            # Support/Resistance
            sr = find_support_resistance(df)
            entry["current_price"] = sr["current_price"]
            entry["nearest_support"] = sr.get("nearest_support")
            entry["nearest_resistance"] = sr.get("nearest_resistance")
            entry["price_position"] = sr.get("price_position", "neutral")
            entry["support_levels"] = sr["support"][:3]
            entry["resistance_levels"] = sr["resistance"][:3]

            # Mean reversion
            if len(df) >= 50:
                mr = detect_mean_reversion(df)
                entry["rsi"] = mr.get("rsi")
                entry["bb_position"] = mr.get("bollinger_position")
                entry["mr_signal"] = mr.get("signal", "neutral")

                if mr["signal"] in ("strong_buy", "buy"):
                    alerts.append({"symbol": symbol, "type": "oversold", "severity": "high" if mr["signal"] == "strong_buy" else "medium",
                                   "message": f"{symbol} OVERSOLD — RSI {mr['rsi']:.0f}"})
                elif mr["signal"] in ("strong_sell", "sell"):
                    alerts.append({"symbol": symbol, "type": "overbought", "severity": "high" if mr["signal"] == "strong_sell" else "medium",
                                   "message": f"{symbol} OVERBOUGHT — RSI {mr['rsi']:.0f}"})

            # Trend
            df_full = load_daily(symbol)
            if len(df_full) >= 200:
                trend = detect_trend(df_full)
                entry["trend"] = trend.get("trend", "Unknown")
                entry["trend_score"] = trend.get("trend_score", 0)
                entry["return_10d"] = trend.get("return_10d", 0)
                entry["return_30d"] = trend.get("return_30d", 0)

                if trend.get("trend_score", 0) > 20:
                    bullish_count += 1
                elif trend.get("trend_score", 0) < -20:
                    bearish_count += 1

                for sig in trend.get("signals", []):
                    if "GOLDEN CROSS" in sig or "DEATH CROSS" in sig:
                        alerts.append({"symbol": symbol, "type": "ma_cross", "severity": "high", "message": sig})

            # Breakout
            bo = detect_breakouts(df)
            entry["breakout"] = bo.get("breakout", False)
            if bo.get("breakout"):
                entry["breakout_direction"] = bo["direction"]
                entry["breakout_pct"] = bo["breakout_pct"]
                alerts.append({"symbol": symbol, "type": "breakout", "severity": "high",
                               "message": f"{symbol} BREAKOUT {bo['direction'].upper()} — {bo.get('description', '')}"})

            # Recent candlestick patterns (last 5 days)
            candles = detect_candlestick_patterns(df.tail(15))
            strong_recent = [p for p in candles if p["strength"] in ("strong", "very strong")]
            entry["recent_patterns"] = strong_recent[-3:] if strong_recent else []

            for p in strong_recent[-2:]:
                if p["strength"] == "very strong":
                    alerts.append({"symbol": symbol, "type": "pattern", "severity": "medium",
                                   "message": f"{symbol}: {p['pattern']} ({p['signal']})"})

            # Chart patterns
            chart = detect_chart_patterns(df)
            entry["chart_patterns"] = chart[:2] if chart else []
            for cp in chart:
                if cp.get("strength") in ("strong", "very strong"):
                    alerts.append({"symbol": symbol, "type": "chart_pattern", "severity": "high",
                                   "message": f"{symbol}: {cp['pattern']}"})

            # S/R proximity warning
            if sr.get("price_position") == "near_support":
                alerts.append({"symbol": symbol, "type": "sr_proximity", "severity": "medium",
                               "message": f"{symbol} near support at ${sr['nearest_support']}"})
            elif sr.get("price_position") == "near_resistance":
                alerts.append({"symbol": symbol, "type": "sr_proximity", "severity": "medium",
                               "message": f"{symbol} near resistance at ${sr['nearest_resistance']}"})

            # Overall signal for this stock
            score = 0
            if entry.get("trend_score", 0) > 20: score += 1
            elif entry.get("trend_score", 0) < -20: score -= 1
            if entry.get("mr_signal") in ("buy", "strong_buy"): score += 1
            elif entry.get("mr_signal") in ("sell", "strong_sell"): score -= 1
            if entry.get("breakout") and entry.get("breakout_direction") == "bullish": score += 1
            elif entry.get("breakout") and entry.get("breakout_direction") == "bearish": score -= 1
            for p in entry.get("recent_patterns", []):
                if p["signal"] == "bullish": score += 0.5
                elif p["signal"] == "bearish": score -= 0.5

            entry["signal"] = "BULLISH" if score >= 1.5 else "BEARISH" if score <= -1.5 else "NEUTRAL" if abs(score) < 0.5 else "MIXED"
            entry["signal_score"] = round(score, 1)

            holdings.append(entry)

        except Exception as e:
            logger.warning(f"Portfolio analysis error for {symbol}: {e}")
            holdings.append({"symbol": symbol, "error": str(e)})

    # Sort alerts by severity
    severity_order = {"high": 0, "medium": 1, "low": 2}
    alerts.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 2))

    # Portfolio-wide signal
    total = len(symbols)
    if total == 0:
        portfolio_signal = "NEUTRAL"
    elif bullish_count > bearish_count * 1.5:
        portfolio_signal = "BULLISH"
    elif bearish_count > bullish_count * 1.5:
        portfolio_signal = "BEARISH"
    elif bullish_count == 0 and bearish_count == 0:
        portfolio_signal = "NEUTRAL"
    else:
        portfolio_signal = "MIXED"

    return {
        "holdings": holdings,
        "alerts": alerts,
        "portfolio_signal": portfolio_signal,
        "bullish_count": bullish_count,
        "bearish_count": bearish_count,
        "neutral_count": total - bullish_count - bearish_count,
    }
