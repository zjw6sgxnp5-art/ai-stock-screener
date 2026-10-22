"""
Macro Climate & Market Regime Service:
Real SPY/QQQ/VIX regime state machine.
Data sourced from Longbridge CLI with automatic Yahoo Finance fallback.
No synthetic or fabricated macro events.
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from backend.core.utils import first_value, number_from, utc_now_iso
from backend.db import get_cache, set_cache
from backend.services.backtester import fetch_yahoo_history
from backend.services.market_data import run_longbridge, unwrap_items


REGIME_FACTOR_WEIGHTS: Dict[str, Dict[str, Any]] = {
    "RISK_ON": {
        "name": "顺风价值成长矩阵 (Risk-On Growth)",
        "weights": {"quality": 30, "valuation": 25, "momentum": 20, "catalyst": 15, "liquidity": 10},
        "risk_multiplier": 0.8,
        "anti_chasing_note": "低波动顺风环境下，以财务质量(30%)与估值合理性(25%)为核心基石，动量仅作顺势辅助，防范高位追高泡沫。"
    },
    "NEUTRAL": {
        "name": "常态平衡矩阵 (Neutral Balanced)",
        "weights": {"quality": 35, "valuation": 25, "momentum": 15, "catalyst": 15, "liquidity": 10},
        "risk_multiplier": 1.0,
        "anti_chasing_note": "市场震荡分化期，基本面质量(35%)与估值比较优势(25%)居绝对主导地位，拒绝纯情绪追涨杀跌。"
    },
    "CAUTION": {
        "name": "防御避险矩阵 (Caution Defensive)",
        "weights": {"quality": 40, "valuation": 30, "liquidity": 15, "momentum": 10, "catalyst": 5},
        "risk_multiplier": 1.5,
        "anti_chasing_note": "波动率放大期，质量与估值合计权重达70%，严格锁定稳健资产负债表与充沛造血能力。"
    },
    "PANIC": {
        "name": "极度防守矩阵 (Extreme Panic Preservation)",
        "weights": {"quality": 45, "valuation": 35, "liquidity": 15, "momentum": 5, "catalyst": 0},
        "risk_multiplier": 2.5,
        "anti_chasing_note": "全市场系统性抛压，强制激活防守熔断，剔除情绪催化，质量(45%)与估值(35%)决定生死存亡。"
    }
}


def _compute_ma20_trend(symbol: str, current_price: float, use_longbridge: bool = True) -> tuple[str, bool]:
    """Compute MA20 and return (trend_label, above_ma20) based on historical daily closes."""
    if current_price <= 0:
        return "未取得", False
    try:
        clean_sym = symbol.replace(".US", "").replace("^", "")
        # 1. 优先尝试使用长桥官方日 K 线计算 MA20 (仅在长桥模式启用时，超时缩短至 4 秒)
        if use_longbridge:
            try:
                from backend.services.market_data import extract_klines, run_longbridge
                k_res = run_longbridge(["kline", f"{clean_sym}.US", "--period", "day", "--count", "30", "--format", "json"], ttl_seconds=1800, timeout=4)
                klines = extract_klines(k_res)
                if klines and len(klines) >= 20:
                    recent_closes = [k["close"] for k in klines[-20:] if k.get("close")]
                    if len(recent_closes) >= 15:
                        ma20 = sum(recent_closes) / len(recent_closes)
                        above = current_price >= ma20
                        trend = "站上 20 日均线 (偏强)" if above else "跌破 20 日均线 (承压)"
                        return trend, above
            except Exception:
                pass

        # 2. 长桥日 K 未就绪时，降级使用 Yahoo Finance 日线历史
        bars = fetch_yahoo_history(clean_sym, "3mo")
        if not bars:
            return "未取得", False
        dates = sorted(bars.keys())
        if len(dates) < 20:
            return "样本不足 20 日", False
        recent_closes = [bars[d]["close"] for d in dates[-20:] if bars[d].get("close")]
        if len(recent_closes) < 15:
            return "未取得", False
        ma20 = sum(recent_closes) / len(recent_closes)
        latest_yahoo_close = bars[dates[-1]]["close"]
        cmp_price = latest_yahoo_close if abs(current_price - latest_yahoo_close) / latest_yahoo_close > 0.05 else current_price
        above = cmp_price >= ma20
        trend = "站上 20 日均线 (偏强)" if above else "跌破 20 日均线 (承压)"
        return trend, above
    except Exception:
        return "未取得", False


def _fetch_yahoo_macro_bar(symbol: str) -> Optional[Dict[str, Any]]:
    """Fetch real latest close and change percentage from Yahoo Finance daily history."""
    try:
        bars = fetch_yahoo_history(symbol, "3mo")
        if not bars:
            return None
        dates = sorted(bars.keys())
        if len(dates) < 1:
            return None
        latest_d = dates[-1]
        latest_c = bars[latest_d]["close"]
        prev_c = bars[dates[-2]]["close"] if len(dates) >= 2 else latest_c
        chg = round((latest_c / prev_c - 1) * 100, 2) if prev_c else 0.0
        return {
            "last": round(latest_c, 2),
            "change_pct": chg,
            "date": latest_d,
            "source": "Yahoo Finance (日线备用数据 · 存在延迟)"
        }
    except Exception:
        return None


def get_macro_climate() -> Dict[str, Any]:
    """Retrieve macro regime, market indices, VIX panic index, and data source tags."""
    cached = get_cache("macro:climate:v3")
    if cached is not None:
        return cached

    spy_data = {"symbol": "SPY.US", "name": "标普 500 基准 (SPY)", "last": 0.0, "change_pct": 0.0, "trend": "未取得", "above_ma20": False, "source": "未连接"}
    qqq_data = {"symbol": "QQQ.US", "name": "纳斯达克 100 基准 (QQQ)", "last": 0.0, "change_pct": 0.0, "trend": "未取得", "above_ma20": False, "source": "未连接"}
    vix_data = {"symbol": ".VIX.US", "name": "CBOE 恐慌波动率 (VIX)", "last": 0.0, "change_pct": 0.0, "source": "未连接"}

    data_source_mode = "LONGBRIDGE"

    # 1. 优先尝试从长桥获取实时三指数行情（设置 5 秒快速握手，如离线即刻降级至 Yahoo 备用源）
    try:
        res = run_longbridge(["quote", "SPY.US", "QQQ.US", ".VIX.US", "--format", "json"], ttl_seconds=60, timeout=5)
        items = unwrap_items(res.get("data"))
        for item in items:
            sym = first_value(item, ["symbol"])
            last = number_from(first_value(item, ["last", "last_done"]))
            prev = number_from(first_value(item, ["prev_close"]))
            chg = number_from(first_value(item, ["change_percentage"]))
            if chg is None and last and prev:
                chg = round((last / prev - 1) * 100, 2)
            if sym == "SPY.US" and last:
                spy_data.update({"last": last, "change_pct": chg or 0.0, "source": "长桥实时行情"})
            elif sym == "QQQ.US" and last:
                qqq_data.update({"last": last, "change_pct": chg or 0.0, "source": "长桥实时行情"})
            elif sym in (".VIX.US", "VIX.US") and last:
                vix_data.update({"last": last, "change_pct": chg or 0.0, "source": "长桥实时行情"})
    except Exception:
        pass

    # 2. 若长桥未就绪（如 Token 过期或未配置指数权限），自动使用 Yahoo Finance 真实日线数据填充
    if spy_data["last"] <= 0:
        data_source_mode = "YAHOO_FINANCE"
        spy_bar = _fetch_yahoo_macro_bar("SPY")
        if spy_bar:
            spy_data.update(spy_bar)
        qqq_bar = _fetch_yahoo_macro_bar("QQQ")
        if qqq_bar:
            qqq_data.update(qqq_bar)
        vix_bar = _fetch_yahoo_macro_bar("^VIX")
        if vix_bar:
            vix_data.update(vix_bar)

    # 3. 严格计算 SPY 和 QQQ 的 20 日均线趋势状态 (若降级为 Yahoo 模式，直连 Yahoo 免去长桥重试等待)
    use_lb = (data_source_mode == "LONGBRIDGE")
    if spy_data["last"] > 0:
        trend, above = _compute_ma20_trend("SPY", spy_data["last"], use_longbridge=use_lb)
        spy_data["trend"] = trend
        spy_data["above_ma20"] = above

    if qqq_data["last"] > 0:
        trend, above = _compute_ma20_trend("QQQ", qqq_data["last"], use_longbridge=use_lb)
        qqq_data["trend"] = trend
        qqq_data["above_ma20"] = above

    spy_chg = spy_data.get("change_pct", 0.0)
    qqq_chg = qqq_data.get("change_pct", 0.0)
    both_down = (spy_chg < 0 and qqq_chg < 0)
    pullback = (spy_chg <= -0.4 or qqq_chg <= -0.5)

    vix_val = vix_data.get("last", 0.0)
    vix_chg = vix_data.get("change_pct", 0.0)
    is_vix_spike = (vix_chg >= 15.0)  # 单日恐慌指数跳升超 15%，触发避险脉冲

    if vix_val <= 0:
        regime_code = "NEUTRAL"
        regime = {
            "code": regime_code,
            "level": "常态平衡期",
            "tag": "Neutral",
            "badge_class": "badge-info",
            "vix_regime": "波动率数据未连接 (维持基准常态)",
            "suggested_exposure": "50% - 70%",
            "strategy_style": "精选绩优白马，兼顾估值支撑与财报确定性",
            "description": "宏观波动率未接通，按常态平衡期基准运行，依托扎实基本面与合理估值交易。",
            "factor_matrix": REGIME_FACTOR_WEIGHTS[regime_code]
        }
    elif vix_val < 17.5:
        if both_down and pullback:
            regime_code = "RISK_ON"
            regime = {
                "code": regime_code,
                "level": "低波分化 / 审慎进攻期",
                "tag": "Risk-On (Pullback)",
                "badge_class": "badge-info",
                "vix_regime": f"波动受抑但指数回踩 (VIX {vix_val:.2f}, SPY {spy_chg:+.2f}%, QQQ {qqq_chg:+.2f}%)",
                "suggested_exposure": "60% - 75%",
                "strategy_style": "结构分化精选，逢低布局高确定性突破龙头，控制单笔追高风险",
                "description": f"全市场波动率整体受控（VIX={vix_val:.2f}），但标普/纳指最近交易日出现回踩调整（SPY {spy_chg:+.2f}%, QQQ {qqq_chg:+.2f}%），不可盲目满仓激进追高，建议适度收紧仓位至 60%–75%，严守 2xATR 止损防线。",
                "factor_matrix": {
                    "name": "审慎进攻矩阵 (Cautious Growth)",
                    "weights": {"momentum": 30, "catalyst": 20, "quality": 20, "liquidity": 15, "valuation": 15},
                    "risk_multiplier": 1.0,
                    "anti_chasing_note": "大盘微调环境下适度提升质量与估值护城河，防范高位假突破。"
                }
            }
        else:
            regime_code = "RISK_ON"
            regime = {
                "code": regime_code,
                "level": "顺风进攻期",
                "tag": "Risk-On",
                "badge_class": "badge-success",
                "vix_regime": f"极度平静 ({vix_val:.2f} < 17.5)",
                "suggested_exposure": "75% - 90%",
                "strategy_style": "主攻高动量突破、强基本面与放量龙头",
                "description": "市场波动受抑，做多宽容度极高，资金风险偏好旺盛，持股胜率佳。",
                "factor_matrix": REGIME_FACTOR_WEIGHTS[regime_code]
            }
    elif vix_val <= 22.0:
        regime_code = "NEUTRAL"
        vix_note = f"健康震荡 · 日内波动抬升 (VIX {vix_val:.2f}, 单日 {vix_chg:+.2f}%)" if is_vix_spike else f"健康震荡 ({vix_val:.2f} ∈ [17.5, 22])"
        desc = (
            f"指数健康震荡分化（VIX={vix_val:.2f}），虽最近单日波动率跳升 {vix_chg:+.2f}%，但绝对水位受控。建议仓位维持在 50%–70%，精选绩优白马，兼顾估值支撑与财报确定性。"
            if is_vix_spike else
            "指数健康震荡分化，不宜盲目追涨纯情绪概念，依托扎实基本面与合理PE交易。"
        )
        regime = {
            "code": regime_code,
            "level": "常态分化期",
            "tag": "Neutral",
            "badge_class": "badge-info",
            "vix_regime": vix_note,
            "suggested_exposure": "50% - 70%",
            "strategy_style": "精选绩优白马，兼顾估值支撑与财报确定性",
            "description": desc,
            "factor_matrix": REGIME_FACTOR_WEIGHTS[regime_code]
        }
    elif vix_val <= 28.0:
        regime_code = "CAUTION"
        regime = {
            "code": regime_code,
            "level": "情绪扰动期",
            "tag": "Caution",
            "badge_class": "badge-warning",
            "vix_regime": f"波动放大 ({vix_val:.2f} ∈ (22, 28])",
            "suggested_exposure": "30% - 50%",
            "strategy_style": "防御为上，切换至高股息/低Beta防御性核心资产",
            "description": "宏观利率或地缘扰动升温，高估值成长股杀估值风险上升，严格收窄止损保护利润。",
            "factor_matrix": REGIME_FACTOR_WEIGHTS[regime_code]
        }
    else:
        regime_code = "PANIC"
        regime = {
            "code": regime_code,
            "level": "极度恐慌期",
            "tag": "Extreme Fear",
            "badge_class": "badge-danger",
            "vix_regime": f"恐慌飙升 ({vix_val:.2f} > 28)",
            "suggested_exposure": "0% - 20%",
            "strategy_style": "触发熔断预警：现金为王，停止主动做多，等待极值企稳",
            "description": "全市场面临流动性冲击与系统性抛压，泥沙俱下，强行选股大概率沦为活靶子。",
            "factor_matrix": REGIME_FACTOR_WEIGHTS[regime_code]
        }

    # 同步补齐前端驾驶舱所读取的 action_advice 字段
    if regime and "action_advice" not in regime:
        regime["action_advice"] = regime.get("strategy_style", "以业绩确定性高、动量突破的龙头标的为主。")

    result = {
        "ok": True,
        "spy": spy_data,
        "qqq": qqq_data,
        "vix": vix_data,
        "regime": regime,
        "data_source_mode": data_source_mode,
        "calendar_available": False,
        "calendar_notice": "宏观经济日历（CPI/非农/美联储议息）暂未接入外部开放 API Key，系统已彻底停用伪造演示事件。大盘天气与 VIX 状态机严格基于真实市场行情推导。",
        "past_events": [],
        "upcoming_events": [],
        "updated_at": utc_now_iso(),
    }
    set_cache("macro:climate:v3", result, 180)
    return result


def get_active_factor_config() -> tuple[Dict[str, int], float]:
    """
    Retrieve synchronized factor weights and risk multiplier from the active macro climate state machine.
    Ensures Daily Screener, Stock 360 (/api/analyze), and Multi-Stock Compare (/api/compare) use identical parameters.
    """
    try:
        climate = get_macro_climate()
        regime = climate.get("regime", {})
        factor_matrix = regime.get("factor_matrix", {})
        weights = factor_matrix.get("weights") or {
            "momentum": 30,
            "catalyst": 20,
            "quality": 20,
            "liquidity": 15,
            "valuation": 15,
        }
        risk_multiplier = float(factor_matrix.get("risk_multiplier", 1.0))
        return dict(weights), risk_multiplier
    except Exception:
        return {"momentum": 30, "catalyst": 20, "quality": 20, "liquidity": 15, "valuation": 15}, 1.0

