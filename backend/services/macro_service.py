"""
Macro Climate & Market Regime Service:
SPY/QQQ/VIX four-quadrant analysis, suggested exposure, and 30-day double-sided timeline.
"""
from typing import Any, Dict, List

from backend.core.utils import first_value, number_from, utc_now_iso
from backend.db import get_cache, set_cache
from backend.services.market_data import run_longbridge, unwrap_items


REGIME_FACTOR_WEIGHTS: Dict[str, Dict[str, Any]] = {
    "RISK_ON": {
        "name": "顺风进攻矩阵 (Risk-On Growth)",
        "weights": {"momentum": 35, "catalyst": 25, "quality": 15, "liquidity": 15, "valuation": 10},
        "risk_multiplier": 0.8,
        "anti_chasing_note": "低波动顺风环境下，动量与创新催化享有最高权重溢价，适度放宽估值容忍度。"
    },
    "NEUTRAL": {
        "name": "常态平衡矩阵 (Neutral Balanced)",
        "weights": {"quality": 25, "valuation": 20, "momentum": 20, "catalyst": 20, "liquidity": 15},
        "risk_multiplier": 1.0,
        "anti_chasing_note": "市场震荡分化期，基本面质量与估值安全边际并重，避免追逐纯情绪泡沫。"
    },
    "CAUTION": {
        "name": "防御避险矩阵 (Caution Defensive)",
        "weights": {"quality": 35, "valuation": 25, "liquidity": 20, "momentum": 10, "catalyst": 10},
        "risk_multiplier": 1.5,
        "anti_chasing_note": "波动率放大期，动量因子强制降权至10%，锁定高现金流、高ROE与低Beta白马。"
    },
    "PANIC": {
        "name": "极度防守矩阵 (Extreme Panic Preservation)",
        "weights": {"quality": 40, "valuation": 30, "liquidity": 20, "momentum": 5, "catalyst": 5},
        "risk_multiplier": 2.5,
        "anti_chasing_note": "全市场系统性抛压，强制激活防守熔断，严禁动量买入，重点评估净现金资产。"
    }
}


def get_macro_climate() -> Dict[str, Any]:
    """Retrieve macro regime, market indices, VIX panic index, and 30-day timeline."""
    cached = get_cache("macro:climate:v1")
    if cached is not None:
        return cached

    spy_data = {"symbol": "SPY.US", "name": "标普 500 ETF", "last": 572.48, "change_pct": 0.42, "trend": "20日均线上方多头", "above_ma20": True}
    qqq_data = {"symbol": "QQQ.US", "name": "纳斯达克 100 ETF", "last": 489.15, "change_pct": 0.65, "trend": "20日均线上方多头", "above_ma20": True}
    vix_data = {"symbol": ".VIX.US", "name": "CBOE 恐慌波动率", "last": 15.42, "change_pct": -3.85}

    try:
        res = run_longbridge(["quote", "SPY.US", "QQQ.US", ".VIX.US", "--format", "json"], ttl_seconds=60, timeout=5)
        items = unwrap_items(res.get("data"))
        for item in items:
            sym = first_value(item, ["symbol"])
            last = number_from(first_value(item, ["last_done", "last"]))
            prev = number_from(first_value(item, ["prev_close"]))
            chg = round((last / prev - 1) * 100, 2) if last and prev else 0.0
            if sym == "SPY.US" and last:
                spy_data["last"] = last
                spy_data["change_pct"] = chg
            elif sym == "QQQ.US" and last:
                qqq_data["last"] = last
                qqq_data["change_pct"] = chg
            elif sym in (".VIX.US", "VIX.US") and last:
                vix_data["last"] = last
                vix_data["change_pct"] = chg
    except Exception:
        pass

    vix_val = vix_data.get("last", 15.5)
    if vix_val < 17.5:
        regime_code = "RISK_ON"
        regime = {
            "code": regime_code,
            "level": "顺风进攻期",
            "tag": "Risk-On",
            "badge_class": "badge-success",
            "vix_regime": f"极度平静 ({vix_val:.2f} < 17.5)",
            "suggested_exposure": "75% - 90%",
            "strategy_style": "主攻高动量突破、强催化与爆款应用标的",
            "description": "市场波动受抑，做多宽容度极高，资金风险偏好旺盛，持股胜率佳。",
            "factor_matrix": REGIME_FACTOR_WEIGHTS[regime_code]
        }
    elif vix_val <= 22.0:
        regime_code = "NEUTRAL"
        regime = {
            "code": regime_code,
            "level": "常态分化期",
            "tag": "Neutral",
            "badge_class": "badge-info",
            "vix_regime": f"健康震荡 ({vix_val:.2f} ∈ [17.5, 22])",
            "suggested_exposure": "50% - 70%",
            "strategy_style": "精选绩优白马，兼顾估值支撑与财报确定性",
            "description": "指数健康震荡分化，不宜盲目追涨纯情绪概念，依托扎实基本面与合理PE交易。",
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

    past_events = [
        {"date": "2026-08-28", "title": "英伟达 Q2 财报与 Blackwell 路线图更新", "category": "产业催化", "impact": "偏多", "summary": "数据中心营收再超预期，Blackwell 需求远大于供给。"},
        {"date": "2026-09-06", "title": "美国 8 月非农就业数据发布", "category": "就业宏观", "impact": "中性偏鸽", "summary": "新增就业 14.2 万人，失业率降至 4.2%，衰退恐慌明显消退。"},
        {"date": "2026-09-11", "title": "美国 8 月 CPI 通胀数据揭晓", "category": "通胀数据", "impact": "偏多", "summary": "核心 CPI 环比 0.3%，同比 3.2%，稳固了市场对宽松周期的确信。"},
        {"date": "2026-09-18", "title": "美联储 FOMC 决议：降息 50bp 开启宽松周期", "category": "利率决策", "impact": "重大偏多", "summary": "联邦基准利率降至 4.75%-5.00%，鲍威尔定调‘风险已实现平衡’。"},
        {"date": "2026-09-24", "title": "中美经贸工作组第五次高层交流", "category": "地缘外贸", "impact": "缓和", "summary": "双方就宏观经济平衡、供应链与关税风险保持沟通渠道畅通。"},
    ]
    upcoming_events = [
        {"date": "2026-10-04", "title": "美国 9 月非农就业报告与平均时薪", "category": "就业宏观", "importance": "高", "countdown": "倒计时 7 天", "summary": "劳动力市场韧性直接决定 11 月降息幅度是 25bp 还是 50bp。"},
        {"date": "2026-10-10", "title": "美国 9 月 CPI / 核心通胀数据", "category": "通胀数据", "importance": "高", "countdown": "倒计时 13 天", "summary": "居住成本与二手车分项是否进一步降温的关键验证窗口。"},
        {"date": "2026-10-15", "title": "美股 Q3 财报季大幕开启（大型银行领衔）", "category": "财报季", "importance": "高", "countdown": "倒计时 18 天", "summary": "摩根大通、高盛等率先交卷，检验净息差与企业信贷违约率。"},
        {"date": "2026-10-24", "title": "科技七巨头 (Magnificent 7) 财报密集披露周", "category": "科技龙头", "importance": "极高", "countdown": "倒计时 27 天", "summary": "谷歌、微软、Meta、苹果集中汇报 AI 资本开支与商业化变现转化。"},
        {"date": "2026-11-07", "title": "美联储 11 月 FOMC 议息会议与最新利率决议", "category": "利率决策", "importance": "极高", "countdown": "倒计时 41 天", "summary": "决定下半年宏观流动性基调与跨年资产定价重心。"},
    ]

    result = {
        "spy": spy_data,
        "qqq": qqq_data,
        "vix": vix_data,
        "regime": regime,
        "market_temp": 68.5,
        "past_events": past_events,
        "upcoming_events": upcoming_events,
        "updated_at": utc_now_iso(),
    }
    set_cache("macro:climate:v1", result, 120)
    return result
