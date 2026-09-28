"""
Technical and quantitative indicators: Moving Averages, RSI, Volatility, Drawdowns.
"""
import math
from typing import Any, Dict, List, Optional


def moving_average(values: List[float], window: int) -> Optional[float]:
    """Calculate simple moving average."""
    if len(values) < window:
        return None
    return sum(values[-window:]) / window


def pct_change(values: List[float], periods: int) -> Optional[float]:
    """Calculate percentage change over n periods."""
    if len(values) <= periods:
        return None
    base = values[-periods - 1]
    if not base:
        return None
    return (values[-1] / base - 1) * 100


def annualized_volatility(values: List[float], periods: int = 20) -> Optional[float]:
    """Calculate annualized volatility from historical closes."""
    if len(values) <= periods:
        return None
    closes = values[-periods - 1 :]
    returns = []
    for idx in range(1, len(closes)):
        if closes[idx - 1]:
            returns.append(math.log(closes[idx] / closes[idx - 1]))
    if len(returns) < 2:
        return None
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    return math.sqrt(variance) * math.sqrt(252) * 100


def max_drawdown(values: List[float], periods: int = 60) -> Optional[float]:
    """Calculate maximum drawdown percentage over n periods."""
    if not values:
        return None
    window = values[-periods:]
    peak = window[0]
    worst = 0.0
    for value in window:
        peak = max(peak, value)
        if peak:
            worst = min(worst, (value / peak - 1) * 100)
    return worst


def rsi(values: List[float], period: int = 14) -> Optional[float]:
    """Calculate Relative Strength Index (RSI)."""
    if len(values) <= period:
        return None
    gains = []
    losses = []
    recent = values[-period - 1 :]
    for idx in range(1, len(recent)):
        delta = recent[idx] - recent[idx - 1]
        gains.append(max(delta, 0))
        losses.append(abs(min(delta, 0)))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def trend_label(value: Optional[float]) -> str:
    """Label trend by 20-day return."""
    if value is None:
        return "数据不足"
    if value >= 10:
        return "强势"
    if value >= 3:
        return "偏强"
    if value <= -10:
        return "弱势"
    if value <= -3:
        return "偏弱"
    return "震荡"


def compute_technical_summary(klines: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate technical indicators from kline series."""
    closes = [float(k["close"]) for k in klines if k.get("close") is not None]
    volumes = [float(k["volume"]) for k in klines if k.get("volume") is not None]
    ma20 = moving_average(closes, 20)
    ma60 = moving_average(closes, 60)
    last = closes[-1] if closes else None
    volume_latest = volumes[-1] if volumes else None
    volume_avg20 = moving_average(volumes, 20)
    volume_ratio = None
    if volume_latest is not None and volume_avg20:
        volume_ratio = volume_latest / volume_avg20

    returns = {
        "5d": pct_change(closes, 5),
        "20d": pct_change(closes, 20),
        "60d": pct_change(closes, 60),
    }
    return {
        "last_close": last,
        "ma20": ma20,
        "ma60": ma60,
        "above_ma20": bool(last is not None and ma20 is not None and last >= ma20),
        "above_ma60": bool(last is not None and ma60 is not None and last >= ma60),
        "returns": returns,
        "trend_label": trend_label(returns["20d"]),
        "volatility_20d": annualized_volatility(closes, 20),
        "max_drawdown_60d": max_drawdown(closes, 60),
        "rsi14": rsi(closes, 14),
        "volume_ratio_20d": volume_ratio,
        "candles": len(closes),
    }
