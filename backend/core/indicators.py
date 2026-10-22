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


def true_range_series(highs: List[float], lows: List[float], closes: List[float]) -> List[float]:
    """Calculate True Range (TR) series."""
    if not highs or not lows or not closes:
        return []
    trs: List[float] = []
    for i in range(len(highs)):
        h = highs[i]
        l = lows[i]
        if i == 0 or i >= len(closes):
            trs.append(h - l)
        else:
            prev_c = closes[i - 1]
            tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
            trs.append(tr)
    return trs


def average_true_range(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> Optional[float]:
    """Calculate 14-period Average True Range (ATR)."""
    trs = true_range_series(highs, lows, closes)
    if len(trs) < period:
        return None
    # Use standard 14-period smoothed ATR
    atr_val = sum(trs[:period]) / period
    for idx in range(period, len(trs)):
        atr_val = (atr_val * (period - 1) + trs[idx]) / period
    return round(atr_val, 2)


def macd(values: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, Optional[float]]:
    """Calculate MACD line, Signal line, and Histogram."""
    if len(values) < slow + signal:
        return {"dif": None, "dea": None, "macd_bar": None}
    
    # Calculate EMA
    def calc_ema(series: List[float], n: int) -> List[float]:
        alpha = 2 / (n + 1)
        ema = [series[0]]
        for val in series[1:]:
            ema.append(alpha * val + (1 - alpha) * ema[-1])
        return ema

    ema_fast = calc_ema(values, fast)
    ema_slow = calc_ema(values, slow)
    dif_line = [f - s for f, s in zip(ema_fast, ema_slow)]
    dea_line = calc_ema(dif_line[slow - fast:], signal)
    
    curr_dif = dif_line[-1]
    curr_dea = dea_line[-1]
    curr_bar = (curr_dif - curr_dea) * 2
    return {
        "dif": round(curr_dif, 2),
        "dea": round(curr_dea, 2),
        "macd_bar": round(curr_bar, 2)
    }


def bollinger_bands(values: List[float], window: int = 20, num_std: float = 2.0) -> Dict[str, Optional[float]]:
    """Calculate Bollinger Bands (Upper, Middle, Lower)."""
    if len(values) < window:
        return {"upper": None, "middle": None, "lower": None, "bandwidth": None}
    mid = moving_average(values, window)
    recent = values[-window:]
    variance = sum((x - mid) ** 2 for x in recent) / window
    std = math.sqrt(variance)
    upper = mid + num_std * std
    lower = mid - num_std * std
    bw = ((upper - lower) / mid) * 100 if mid > 0 else 0.0
    return {
        "upper": round(upper, 2),
        "middle": round(mid, 2),
        "lower": round(lower, 2),
        "bandwidth": round(bw, 1)
    }


def compute_technical_summary(klines: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate technical indicators from kline series."""
    closes = [float(k["close"]) for k in klines if k.get("close") is not None]
    highs = [float(k.get("high", k.get("close"))) for k in klines if k.get("close") is not None]
    lows = [float(k.get("low", k.get("close"))) for k in klines if k.get("close") is not None]
    volumes = [float(k["volume"]) for k in klines if k.get("volume") is not None]

    ma20 = moving_average(closes, 20)
    ma60 = moving_average(closes, 60)
    ma200 = moving_average(closes, 200) if len(closes) >= 200 else None
    last = closes[-1] if closes else None
    volume_latest = volumes[-1] if volumes else None
    volume_avg20 = moving_average(volumes, 20)
    volume_ratio = None
    if volume_latest is not None and volume_avg20:
        volume_ratio = round(volume_latest / volume_avg20, 2)

    atr14_val = average_true_range(highs, lows, closes, 14)
    atr_pct = round((atr14_val / last * 100), 2) if (atr14_val and last and last > 0) else None

    returns = {
        "5d": pct_change(closes, 5),
        "20d": pct_change(closes, 20),
        "60d": pct_change(closes, 60),
    }

    rsi_val = rsi(closes, 14)
    macd_res = macd(closes)
    bb_res = bollinger_bands(closes)

    raw_tech = {
        "last_close": last,
        "ma20": round(ma20, 2) if ma20 else None,
        "ma60": round(ma60, 2) if ma60 else None,
        "ma200": round(ma200, 2) if ma200 else None,
        "above_ma20": bool(last is not None and ma20 is not None and last >= ma20),
        "above_ma60": bool(last is not None and ma60 is not None and last >= ma60),
        "above_ma200": bool(last is not None and ma200 is not None and last >= ma200) if ma200 else None,
        "returns": returns,
        "trend_label": trend_label(returns["20d"]),
        "volatility_20d": round(annualized_volatility(closes, 20), 1) if annualized_volatility(closes, 20) else None,
        "max_drawdown_60d": round(max_drawdown(closes, 60), 1) if max_drawdown(closes, 60) else None,
        "rsi14": round(rsi_val, 1) if rsi_val else None,
        "macd": macd_res,
        "bollinger": bb_res,
        "atr14": atr14_val,
        "atr_pct": atr_pct,
        "trailing_stop_2atr": round(last - 2 * atr14_val, 2) if (last and atr14_val) else None,
        "volume_ratio_20d": volume_ratio,
        "candles": len(closes),
    }

    # Generate institutional technical analysis modules
    price_ladder = build_support_resistance_ladder(last, highs, lows, closes, ma20, ma60, bb_res, round(last - 2 * atr14_val, 2) if (last and atr14_val) else None)
    trend_resonance = build_trend_resonance(last, ma20, ma60, ma200, returns)
    volume_action = build_volume_price_action(volume_ratio, returns.get("5d"), returns.get("20d"))
    tactical_checklist = build_tactical_checklist(bool(last is not None and ma20 is not None and last >= ma20), bool(last is not None and ma60 is not None and last >= ma60), rsi_val, macd_res.get("macd_bar") if macd_res else None, atr_pct)

    raw_tech = {
        "last_close": last,
        "ma20": round(ma20, 2) if ma20 else None,
        "ma60": round(ma60, 2) if ma60 else None,
        "ma200": round(ma200, 2) if ma200 else None,
        "above_ma20": bool(last is not None and ma20 is not None and last >= ma20),
        "above_ma60": bool(last is not None and ma60 is not None and last >= ma60),
        "above_ma200": bool(last is not None and ma200 is not None and last >= ma200) if ma200 else None,
        "returns": returns,
        "trend_label": trend_label(returns["20d"]),
        "volatility_20d": round(annualized_volatility(closes, 20), 1) if annualized_volatility(closes, 20) else None,
        "max_drawdown_60d": round(max_drawdown(closes, 60), 1) if max_drawdown(closes, 60) else None,
        "rsi14": round(rsi_val, 1) if rsi_val else None,
        "macd": macd_res,
        "bollinger": bb_res,
        "atr14": atr14_val,
        "atr_pct": atr_pct,
        "trailing_stop_2atr": round(last - 2 * atr14_val, 2) if (last and atr14_val) else None,
        "volume_ratio_20d": volume_ratio,
        "candles": len(closes),
        "price_ladder": price_ladder,
        "trend_resonance": trend_resonance,
        "volume_action": volume_action,
        "tactical_checklist": tactical_checklist,
    }

    # Generate interactive plain-language compass
    raw_tech["compass_items"] = build_technical_compass_items(raw_tech)
    raw_tech["plain_verdict"] = generate_plain_verdict(raw_tech)
    return raw_tech


def build_support_resistance_ladder(last: Optional[float], highs: List[float], lows: List[float], closes: List[float], ma20: Optional[float], ma60: Optional[float], bb_res: Optional[Dict[str, Any]], stop_2atr: Optional[float]) -> Dict[str, Any]:
    """Calculate 5-step key support and resistance price ladder."""
    if not last or last <= 0:
        return {}

    recent_60_high = round(max(highs[-60:]), 2) if len(highs) >= 20 else round(last * 1.15, 2)
    bb_upper = bb_res.get("upper") if bb_res else round(last * 1.08, 2)
    bb_lower = bb_res.get("lower") if bb_res else round(last * 0.92, 2)

    # Resistance R2: Major High
    r2 = max(recent_60_high, round(last * 1.05, 2)) if recent_60_high > last else round(last * 1.12, 2)
    
    # Resistance R1: Near-term pressure (Bollinger upper or MA20)
    if bb_upper and bb_upper > last:
        r1 = round(bb_upper, 2)
    elif ma20 and ma20 > last:
        r1 = round(ma20, 2)
    else:
        r1 = round(last * 1.04, 2)

    # Support S1: Near-term support (MA20 if above, or MA60)
    if ma20 and last > ma20:
        s1 = round(ma20, 2)
    elif ma60 and last > ma60:
        s1 = round(ma60, 2)
    else:
        s1 = round(bb_lower, 2) if bb_lower and bb_lower < last else round(last * 0.96, 2)

    # Support S2: Major defense line (2xATR trailing stop or Bollinger Lower)
    s2 = stop_2atr if (stop_2atr and stop_2atr < s1) else (round(bb_lower, 2) if (bb_lower and bb_lower < s1) else round(last * 0.90, 2))

    return {
        "current_price": round(last, 2),
        "r2_major": {
            "name": "强阻力 R2 (近期波段高点)",
            "price": r2,
            "diff_pct": round(((r2 - last) / last) * 100, 1),
            "desc": "前期密集套牢盘与获利盘止盈反压密集区"
        },
        "r1_near": {
            "name": "第一阻力 R1 (布林上轨/均线反压)",
            "price": r1,
            "diff_pct": round(((r1 - last) / last) * 100, 1),
            "desc": "短线冲高测试点，突破需温和放量配合"
        },
        "s1_near": {
            "name": "第一支撑 S1 (核心均线支撑位)",
            "price": s1,
            "diff_pct": round(((s1 - last) / last) * 100, 1),
            "desc": "顺势多头第一防守线，回踩不破为良性低吸窗口"
        },
        "s2_defense": {
            "name": "生命防守 S2 (2xATR 动态硬止损线)",
            "price": s2,
            "diff_pct": round(((s2 - last) / last) * 100, 1),
            "desc": "中长线仓位破位防守底线，跌破意味多头结构彻底瓦解"
        }
    }


def build_trend_resonance(last: Optional[float], ma20: Optional[float], ma60: Optional[float], ma200: Optional[float], returns: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate multi-timeframe trend resonance score and status."""
    if not last:
        return {"score": None, "status": "数据不足", "alignment": "无行情数据", "badge": "NEUTRAL", "desc": "缺少真实收盘价，无法计算均线共振。", "cycles": {}}

    above_20 = bool(ma20 and last >= ma20)
    above_60 = bool(ma60 and last >= ma60)
    above_200 = bool(ma200 and last >= ma200) if ma200 else above_60

    score = 50
    if above_20: score += 18
    if above_60: score += 18
    if above_200: score += 14

    r20 = returns.get("20d") or 0.0
    if r20 > 5.0: score += 10
    elif r20 < -5.0: score -= 10

    score = max(5, min(98, score))

    if above_20 and above_60 and above_200:
        alignment = "三周期全多头排列 (Golden Bullish Alignment)"
        status = "强大多头主升通道"
        badge = "STRONG_BULL"
        desc = "短期动量、中期波段与长期年线全部处于向上多头通道，大资金持仓底仓极其稳固，属于典型的‘顺风车’右侧行情。"
    elif above_60 and above_200 and not above_20:
        alignment = "大周期多头 · 短期良性回踩 (Healthy Pullback)"
        status = "上升中继休整"
        badge = "PULLBACK"
        desc = "中长线大趋势依然保持向上，短期跌破 20 日均线属于获利盘换手与筹码洗盘，无需盲目恐慌，回踩企稳是优质加仓点。"
    elif above_20 and not above_60:
        alignment = "短期超跌反弹 · 面临季线反压 (Rebound under Pressure)"
        status = "弱势反弹试探"
        badge = "REBOUND"
        desc = "短线虽有动能修复站上 20 日线，但上方 60 日季度线依然处于下行压制状态，暂按‘反弹而非反转’对待，建仓应控制仓位。"
    else:
        alignment = "多周期空头压制格局 (Bearish Breakdown)"
        status = "空头防守观察"
        badge = "BEARISH"
        desc = "价格同时受制于 20/60/200 日多条均线反压，空方占据压倒性优势，切忌盲目左侧重仓抄底接飞刀。"

    return {
        "score": score,
        "status": status,
        "badge": badge,
        "alignment": alignment,
        "desc": desc,
        "cycles": {
            "short_20d": {"name": "短期动量 (20日月线)", "status": "站上多头" if above_20 else "跌破空头", "ok": above_20},
            "mid_60d": {"name": "中期波段 (60日季线)", "status": "站上多头" if above_60 else "跌破空头", "ok": above_60},
            "long_200d": {"name": "长期牛熊 (200日年线)", "status": "站上多头" if above_200 else "跌破空头", "ok": above_200}
        }
    }


def build_volume_price_action(volume_ratio: Optional[float], r5: Optional[float], r20: Optional[float]) -> Dict[str, Any]:
    """Diagnose volume-price action and institutional capital behavior."""
    if volume_ratio is None:
        return {
            "category": "量能数据不足 (Data Insufficient)",
            "volume_ratio": None,
            "verdict": "样本不足 20 日均量基准，无法测算量能放大倍率。",
            "badge": "INSUFFICIENT"
        }

    v_rat = volume_ratio
    r5_val = r5 if r5 is not None else 0.0

    if v_rat >= 1.4 and r5_val > 1.5:
        category = "放量突破进攻 (Volume Surge & Rally)"
        verdict = "大资金积极进场抢筹，量价齐升，突破有效性极高。"
        badge = "ACCUMULATION"
    elif v_rat <= 0.85 and r5_val < 0 and r5_val > -4.5:
        category = "缩量良性回踩 (Healthy Low-Volume Pullback)"
        verdict = "价格调整但成交量明显萎缩，说明并无主力恐慌出逃抛压，属于经典的‘缩量洗盘’。"
        badge = "HEALTHY_RETREAT"
    elif v_rat >= 1.5 and r5_val < -1.5:
        category = "放量杀跌抛压 (Distribution / Selloff)"
        verdict = "大阴线下跌伴随成交量急剧放大，存在主力资金减仓出逃迹象，短期需严格防守避险。"
        badge = "DISTRIBUTION"
    elif v_rat >= 1.4 and abs(r5_val) <= 1.5:
        category = "高位放量滞涨 (Volume Churning / Stalling)"
        verdict = "成交量巨大但股价涨幅停滞，筹码换手剧烈，需警惕主力暗中派发筹码。"
        badge = "CHURNING"
    else:
        category = "常态换手整理 (Normal Turnover & Consolidation)"
        verdict = "成交量与价格波动维持在历史常态区间，买卖双方处于平稳对峙阶段。"
        badge = "NEUTRAL"

    return {
        "category": category,
        "volume_ratio": v_rat,
        "verdict": verdict,
        "badge": badge
    }


def build_tactical_checklist(above_20: bool, above_60: bool, rsi_val: Optional[float], macd_bar: Optional[float], atr_pct: Optional[float]) -> List[Dict[str, Any]]:
    """Build institutional tactical checklist lights (Traffic Signals)."""
    rsi_num = rsi_val if rsi_val is not None else 50.0
    bar_num = macd_bar if macd_bar is not None else 0.0
    atr_num = atr_pct if atr_pct is not None else 2.5

    # Signal 1: Moving average structure
    sig1_pass = above_20 and above_60
    # Signal 2: RSI momentum in sweet spot (40~70)
    sig2_pass = (38.0 <= rsi_num <= 72.0)
    # Signal 3: MACD Acceleration
    sig3_pass = bar_num >= 0
    # Signal 4: Volatility Risk
    sig4_pass = atr_num < 4.0

    return [
        {
            "name": "均线多头排列 (MA20 & MA60)",
            "pass": sig1_pass,
            "status_text": "全线站上 (顺势通道)" if sig1_pass else "均线承压 (需防守)",
            "rule": "买方右侧建仓底线：股价应运行在 20日/60日 均线之上"
        },
        {
            "name": "RSI 动能舒适区 (40~70)",
            "pass": sig2_pass,
            "status_text": f"指标健康 ({rsi_num})" if sig2_pass else (f"严重超买发烧 ({rsi_num})" if rsi_num > 72 else f"超卖恐慌 ({rsi_num})"),
            "rule": "避开 >72 的高位发烧追涨，利用 35~50 的安全舒适区低吸"
        },
        {
            "name": "MACD 动能加速度 (柱体方向)",
            "pass": sig3_pass,
            "status_text": f"多头推升 (+{bar_num})" if sig3_pass else f"空头整理 ({bar_num})",
            "rule": "红柱持续放大代表大资金推升加速度正向，绿柱代表调整消化"
        },
        {
            "name": "波动率风险控制 (ATR %)",
            "pass": sig4_pass,
            "status_text": f"波幅适中 ({atr_num}%)" if sig4_pass else f"波动剧烈 ({atr_num}%)",
            "rule": "单日波幅 >4% 说明脾气火爆，长线建仓应主动降低单笔仓位敞口"
        }
    ]


def build_technical_compass_items(tech: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build beginner-friendly hover education cards for every key technical indicator."""
    p = tech.get("last_close") or 0.0
    ma20 = tech.get("ma20")
    ma60 = tech.get("ma60")
    ma200 = tech.get("ma200")
    rsi14 = tech.get("rsi14")
    macd_data = tech.get("macd") or {}
    bar = macd_data.get("macd_bar")
    bb_data = tech.get("bollinger") or {}
    atr14 = tech.get("atr14")
    atr_pct = tech.get("atr_pct")
    v_ratio = tech.get("volume_ratio_20d")
    stop_2atr = tech.get("trailing_stop_2atr")

    items = []

    # 1. 20日均线 (月线趋势生命线)
    if ma20 is not None:
        above = p >= ma20
        diff_pct = round(((p - ma20) / ma20) * 100, 1)
        items.append({
            "id": "ma20",
            "name": "MA20 (20日均线)",
            "value_display": f"${ma20} ({'站上 +' if above else '跌破 -'}{abs(diff_pct)}%)",
            "badge": "多头偏强" if above else "空头承压",
            "status": "good" if above else "danger",
            "plain_english": "过去 20 个交易日（约 1 个月）所有买入者的平均持仓成本。它是短线波段与月度动量的核心‘生命线’。",
            "good_bad_rule": "【好】：股价持续运行在 MA20 之上，说明短期买盘充裕，均线提供坚实支撑；【坏】：跌破 MA20 说明近一个月进场资金处于亏损套牢状态。",
            "current_diagnosis": f"当前股价 ${p} 处于 20 日均线 (${ma20}) {'上方' if above else '下方'}，短期动量{'健康向上' if above else '弱势回调'}。",
            "scenario": "中长线建仓时，若股价回踩 MA20 且不跌破，是极佳的顺势分批低吸加仓点。"
        })

    # 2. 60日均线 (季度决策生命线)
    if ma60 is not None:
        above_60 = p >= ma60
        diff_60 = round(((p - ma60) / ma60) * 100, 1)
        items.append({
            "id": "ma60",
            "name": "MA60 (60日季度线)",
            "value_display": f"${ma60} ({'站上 +' if above_60 else '跌破 -'}{abs(diff_60)}%)",
            "badge": "季度多头" if above_60 else "季度趋势走弱",
            "status": "good" if above_60 else "danger",
            "plain_english": "过去一整个季度的持股成本基准。机构中长线大资金最为看重的‘牛熊分界线’之一。",
            "good_bad_rule": "【好】：股价稳守 MA60 之上，且均线方向朝上，代表中长期趋势向好；【坏】：跌破 MA60 往往意味着季度级别的趋势逆转或深度洗盘。",
            "current_diagnosis": f"当前股价位于 60 日季度线{'之上，中线趋势保持良好' if above_60 else '之下，中线面临均线反压'}。",
            "scenario": "中长期价值投资者的重要底仓防线。只要不有效跌破 60 日线，长线多头仓位无需惊慌。"
        })

    # 3. 200日均线 (长期牛熊生命线 - 华尔街机构仓位基准)
    if ma200 is not None:
        above_200 = p >= ma200
        diff_200 = round(((p - ma200) / ma200) * 100, 1)
        items.append({
            "id": "ma200",
            "name": "MA200 (200日年线/牛熊分水岭)",
            "value_display": f"${ma200} ({'站上 +' if above_200 else '跌破 -'}{abs(diff_200)}%)",
            "badge": "长线大牛市通道" if above_200 else "长线熊市承压",
            "status": "good" if above_200 else "danger",
            "plain_english": "美股长线机构（共同基金、主权财富基金）最核心的宏观仓位基准。站上年线才具备长牛持有底仓逻辑。",
            "good_bad_rule": "【好】：价格稳居 MA200 之上，代表长期资本持续流入；【坏】：跌破 MA200 会触发被动型大资金系统性减仓。",
            "current_diagnosis": f"当前股价运行在 200 日年线 (${ma200}) {'上方' if above_200 else '下方'}，长线牛熊格局属于{'多头支配' if above_200 else '空头承压'}。",
            "scenario": "长线大资金建仓底线：绝不在股价有效跌破 MA200 且趋势向下时盲目重仓。"
        })

    # 4. RSI(14) 相对强弱指标
    if rsi14 is not None:
        if rsi14 >= 72:
            st = "danger"
            bg = "严重超买 (警惕回调)"
            diag = f"当前 RSI 高达 {rsi14}，买方情绪过热，短线存在极大的获利回吐与急跌风险，严禁盲目追高。"
        elif rsi14 >= 52:
            st = "good"
            bg = "强势活跃区间"
            diag = f"当前 RSI 为 {rsi14}，处于健康的动能扩张区，多方力量明显占据主导。"
        elif rsi14 >= 38:
            st = "neutral"
            bg = "中性震荡区间"
            diag = f"当前 RSI 为 {rsi14}，买卖双方处于均势震荡拉锯状态，无明显超买或超卖偏离。"
        else:
            st = "good"
            bg = "超卖恐慌区间 (潜在底部)"
            diag = f"当前 RSI 仅为 {rsi14}，空头抛压已严重宣泄，情绪过度悲观，常孕育技术性超跌反弹或中长线黄金坑。"

        items.append({
            "id": "rsi14",
            "name": "RSI(14) 动能强弱指标",
            "value_display": f"{rsi14}",
            "badge": bg,
            "status": st,
            "plain_english": "衡量过去 14 天里买方和卖方谁力气更大，范围在 0~100 之间，用来诊断股票是‘涨太急发烧’还是‘跌太狠恐慌’。",
            "good_bad_rule": "【好/机会】：RSI 在 30 以下为超卖，是价值投资者分批捡廉价筹码的好时机；【坏/风险】：RSI 超过 70~75 为超买，极易引发急跌回调；【正常】：40~65 属于健康常态。",
            "current_diagnosis": diag,
            "scenario": "中长线定投时：严格执行‘RSI 超买不追，RSI 超卖敢买’的纪律。"
        })

    # 5. MACD 趋势动能柱
    if bar is not None:
        macd_pos = bar >= 0
        items.append({
            "id": "macd",
            "name": "MACD 指标 (动能柱)",
            "value_display": f"{'多头红柱' if macd_pos else '空头绿柱'} ({bar})",
            "badge": "多头主导" if macd_pos else "空头动能释放",
            "status": "good" if macd_pos else "danger",
            "plain_english": "通过快慢均线的离合，捕捉大资金推升或压制股价的‘加速度’。红柱代表买盘加速度变快，绿柱代表卖盘加速度施压。",
            "good_bad_rule": "【好】：红柱持续放大，表明多头势头强劲；出现‘零轴上金叉’为极佳右侧信号；【坏】：绿柱持续发散，表明空头动能还在下杀。",
            "current_diagnosis": f"当前动能柱为{'多头红柱' if macd_pos else '空头绿柱'} (数值 {bar})，动量处于{'正向推升' if macd_pos else '消化调整'}阶段。",
            "scenario": "右侧建仓参考：等待 MACD 绿柱缩短并转为红柱的第一天，往往是调整结束的右侧上车点。"
        })

    # 6. 布林带通道 (Bollinger Bands) 与波动带宽
    if bb_data and bb_data.get("upper") and bb_data.get("lower"):
        b_up = bb_data.get("upper")
        b_low = bb_data.get("lower")
        b_width = bb_data.get("bandwidth", 15.0)
        
        if b_width < 10.0:
            b_badge = "极度挤压 (变盘在即)"
            b_st = "good"
            b_diag = f"通道带宽仅 {b_width}%，波动率被压缩到极限，根据历史统计，极度挤压后通常会爆发大级别单边突破行情。"
        elif p >= b_up:
            b_badge = "触及上轨 (波动扩张)"
            b_st = "danger"
            b_diag = f"当前股价触及布林上轨 (${b_up})，短线处于强势扩张但也存在均值回归回调引力。"
        elif p <= b_low:
            b_badge = "触及下轨 (超跌试探)"
            b_st = "good"
            b_diag = f"当前股价触及布林下轨 (${b_low})，空头超跌严重，关注下轨能否构筑支撑底背离。"
        else:
            b_badge = f"通道运行 (宽{b_width}%)"
            b_st = "neutral"
            b_diag = f"股价在布林带上下轨 (${b_low} ~ ${b_up}) 之间常态震荡，通道波动率保持平稳。"

        items.append({
            "id": "bollinger",
            "name": "布林带通道 (Bollinger Bands)",
            "value_display": f"${b_low} ~ ${b_up}",
            "badge": b_badge,
            "status": b_st,
            "plain_english": "由一条基准均线加减 2 倍标准差构成的动态波动信道。统计学上 95% 的交易日股价都会落在该通道内部。",
            "good_bad_rule": "【挤压变盘】：上下轨紧紧收窄代表‘暴风雨前的平静’；【通道触轨】：突破上轨多头狂飙，跌破下轨恐慌超卖。",
            "current_diagnosis": b_diag,
            "scenario": "当布林带宽收窄到 10% 以下时，应准备好右侧突破跟进的建仓策略。"
        })

    # 7. ATR(14) 与 2xATR 防守底线
    if atr14 is not None and stop_2atr:
        items.append({
            "id": "atr14",
            "name": "ATR(14) 波动尺与止损防线",
            "value_display": f"日均波动 ${atr14} ({atr_pct}%)",
            "badge": f"推荐止损线 ${stop_2atr}",
            "status": "neutral",
            "plain_english": "真实平均波幅。告诉你这只股票每天正常情况下会晃动多大金额，避免你被盘中的正常假摔甩下车。",
            "good_bad_rule": "【理解逻辑】：ATR 不是非黑即白的好坏，而是风险尺子；ATR 越大说明股票脾气越烈，仓位应适当调小；ATR 越小说明走势越稳重。",
            "current_diagnosis": f"当前 14 日平均真实波幅为 ${atr14} (约占股价 {atr_pct}%)，据此测算的 2xATR 动态硬止损线为 ${stop_2atr}。",
            "scenario": "仓位管理利器：中长线投资者建仓后，若股价跌破 ${stop_2atr}，通常代表核心投资逻辑被破坏，应无条件离场减仓。"
        })

    # 8. 成交量量比 (Volume Ratio)
    if v_ratio is not None:
        if v_ratio >= 1.6:
            v_badge = "显著放量"
            v_st = "good"
            v_diag = f"今日成交量是过去 20 天均量的 {v_ratio} 倍，大资金参与度极高，关注是突破放量还是高位滞涨放量。"
        elif v_ratio >= 0.7:
            v_badge = "正常换手"
            v_st = "neutral"
            v_diag = f"成交量与 20 日均量基本持平 (倍率 {v_ratio})，市场处于平稳换手交易状态。"
        else:
            v_badge = "地量缩量"
            v_st = "neutral"
            v_diag = f"成交量极度萎缩 (倍率仅 {v_ratio})，市场观望情绪浓厚，常预示变盘在即。"

        items.append({
            "id": "vol_ratio",
            "name": "成交量比 (相对20日均量)",
            "value_display": f"{v_ratio}x 均量",
            "badge": v_badge,
            "status": v_st,
            "plain_english": "比较今天的成交量和过去一个月平均水平相比是多了还是少了。俗话说‘股市里什么都能骗人，只有成交量骗不了人’。",
            "good_bad_rule": "【好】：在关键支撑位或突破前期高点时温和放量 (1.3x~2x)；【坏】：高位放天量滞涨（主力出货），或下跌时持续放量恐慌杀跌。",
            "current_diagnosis": v_diag,
            "scenario": "突破验证：当股票突破关键阻力位时，必须有成交量放大至 1.5 倍以上才算有效真突破。"
        })

    return items


def generate_plain_verdict(tech: Dict[str, Any]) -> str:
    """Generate concise 1-sentence plain-language technical conclusion."""
    p = tech.get("last_close") or 0.0
    above_20 = tech.get("above_ma20")
    above_60 = tech.get("above_ma60")
    above_200 = tech.get("above_ma200")
    rsi14 = tech.get("rsi14") or 50.0

    if above_20 and above_60:
        if rsi14 > 72:
            return f"短期动量与季度趋势均处于多头强势通道，但 RSI({rsi14}) 已触发超买发烧预警，中长线资金不宜追高追涨，建议等待回踩 MA20 均线企稳后再分批建仓。"
        return f"中短期均线系统多头排列完整，动能充沛且处于舒适运行区间，技术面处于健康的顺势上行窗口。"
    elif above_60 and not above_20:
        return f"季度中长线牛熊分界线依然完好，但短期跌破 20 日均线进入回调整理期，技术面属于‘大趋势向上中的良性洗盘’，中长线资金可关注逢低低吸机会。"
    elif not above_60 and above_20:
        return f"短期出现超跌反弹突破 20 日线，但上方依然面临 60 日季度线反压，技术面暂定为‘反弹而非反转’，建仓应保持克制节奏。"
    else:
        return f"股价同时运行在 20 日线与 60 日线下方，空头格局压制明显，技术面处于防守观察期，切忌盲目左侧重仓抄底接飞刀。"



