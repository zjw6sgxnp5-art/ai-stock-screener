"""
Financial, valuation, risk radar, governance, and multi-factor breakdown module.
"""
import math
import re
from typing import Any, Dict, List, Optional, Tuple

from backend.core.utils import clamp, first_value, number_from, pick_number, strip_html


def indicator_lookup(financials: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Index financial indicators by field name."""
    if not financials:
        return {}
    return {
        item.get("field"): item
        for item in financials.get("indicators", [])
        if isinstance(item, dict) and item.get("field")
    }


def financial_value(indicators: Dict[str, Dict[str, Any]], field: str, key: str = "value") -> Optional[float]:
    """Retrieve numeric value from an indicator field."""
    item = indicators.get(field)
    if not item:
        return None
    return number_from(item.get(key))


def yoy_percent(indicators: Dict[str, Dict[str, Any]], field: str) -> Optional[float]:
    """Get Year-over-Year percentage change for an indicator."""
    value = financial_value(indicators, field, "yoy")
    if value is None:
        return None
    # Longbridge API returns decimal ratios (e.g. 0.89 for +89%, 2.5735 for +257.35%, -0.12 for -12%)
    return value * 100



def analyze_financial_quality(financials: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze fundamental financial quality and key balance sheet / income metrics."""
    indicators = indicator_lookup(financials)
    score = 48.0
    positives: List[str] = []
    red_flags: List[str] = []
    metrics: Dict[str, Optional[float]] = {
        "revenue_yoy": yoy_percent(indicators, "operating_revenue"),
        "profit_yoy": yoy_percent(indicators, "net_profit"),
        "eps_yoy": yoy_percent(indicators, "eps"),
        "roe": financial_value(indicators, "roe"),
        "net_margin": financial_value(indicators, "net_profit_margin"),
        "total_assets": financial_value(indicators, "total_assets"),
        "total_debts": financial_value(indicators, "total_debts"),
    }
    debt_to_assets = None
    if metrics["total_assets"] and metrics["total_debts"] is not None:
        debt_to_assets = metrics["total_debts"] / metrics["total_assets"] * 100
        metrics["debt_to_assets"] = debt_to_assets

    if not indicators:
        return {
            "score": None,
            "verdict": "财务数据不足",
            "positives": [],
            "red_flags": ["财务快照缺失，无法判断增长质量、利润率和资产负债结构。"],
            "metrics": metrics,
            "questions": ["需要补充多期利润表、资产负债表和现金流量表。"],
        }

    revenue_yoy = metrics["revenue_yoy"]
    profit_yoy = metrics["profit_yoy"]
    eps_yoy = metrics["eps_yoy"]
    roe_value = metrics["roe"]
    net_margin = metrics["net_margin"]

    if revenue_yoy is not None:
        score += max(min(revenue_yoy * 0.25, 16), -14)
        if revenue_yoy >= 15:
            positives.append(f"营业收入同比增长约 {revenue_yoy:.1f}%，增长动能较强。")
        elif revenue_yoy < 0:
            red_flags.append(f"营业收入同比下降约 {abs(revenue_yoy):.1f}%，需要判断是否为周期性回落。")

    if profit_yoy is not None:
        score += max(min(profit_yoy * 0.22, 16), -16)
        if profit_yoy >= 15:
            positives.append(f"净利润同比增长约 {profit_yoy:.1f}%，利润弹性较好。")
        elif profit_yoy < 0:
            red_flags.append(f"净利润同比下降约 {abs(profit_yoy):.1f}%，盈利质量承压。")

    if eps_yoy is not None and eps_yoy >= 15:
        score += 5
        positives.append(f"每股收益同比增长约 {eps_yoy:.1f}%，股东口径增长较强。")

    if roe_value is not None:
        if roe_value >= 25:
            score += 10
            positives.append(f"ROE 约 {roe_value:.1f}%，资本回报率突出。")
        elif roe_value < 8:
            score -= 8
            red_flags.append(f"ROE 约 {roe_value:.1f}%，资本效率偏低。")

    if net_margin is not None:
        if net_margin >= 25:
            score += 8
            positives.append(f"净利率约 {net_margin:.1f}%，利润率结构优秀。")
        elif net_margin < 8:
            score -= 6
            red_flags.append(f"净利率约 {net_margin:.1f}%，盈利缓冲较薄。")

    if debt_to_assets is not None:
        if debt_to_assets <= 35:
            score += 5
            positives.append(f"负债/资产约 {debt_to_assets:.1f}%，资产负债表压力相对可控。")
        elif debt_to_assets >= 75:
            score -= 8
            red_flags.append(f"负债/资产约 {debt_to_assets:.1f}%，杠杆压力需要重点核验。")

    if not red_flags:
        red_flags.append("当前财务快照未发现强红旗，但仍需补充现金流质量和多期趋势。")

    score = round(clamp(score), 1)
    # 规矩3：注明「单期利润表，无现金流」，缺少现金流时封顶不超过 70 分
    score = min(score, 70.0)
    positives.insert(0, "单期利润表，无现金流 (质量分封顶 70 分)")

    if score >= 65:
        verdict = "财务质量较好 (单期)"
    elif score >= 50:
        verdict = "财务质量中性 (单期)"
    else:
        verdict = "财务质量承压 (单期)"

    return {
        "score": score,
        "verdict": verdict,
        "positives": positives[:6],
        "red_flags": red_flags[:5],
        "metrics": metrics,
        "questions": [
            "自由现金流是否与净利润同步增长？",
            "毛利率和经营利润率是否连续改善或至少保持稳定？",
            "收入增长是否来自真实需求，而非一次性项目或渠道压货？",
        ],
    }


def analyze_valuation_profile(
    quote: Dict[str, Any],
    valuation: Optional[Dict[str, Any]],
    rating: Optional[Dict[str, Any]],
    industry_peers: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Analyze valuation multiples, target price upside, and peer percentiles."""
    pe = valuation.get("pe_raw") if valuation else None
    median = number_from((valuation or {}).get("industry_median"))
    last = quote.get("last")
    target = rating.get("target") if rating else None
    target_upside = (target / last - 1) * 100 if target and last else None
    peer_pes = [item.get("pe") for item in industry_peers if item.get("pe") is not None and item.get("pe") > 0]
    peer_rank = None
    peer_percentile = None
    if pe is not None and peer_pes:
        lower_or_equal = sum(1 for value in peer_pes if value <= pe)
        peer_rank = lower_or_equal
        peer_percentile = lower_or_equal / len(peer_pes) * 100

    observations: List[str] = []
    risks: List[str] = []
    score = 50.0
    premium_to_industry = None
    if pe is not None:
        if median and median > 0:
            premium_to_industry = (pe / median - 1) * 100
            if premium_to_industry > 80:
                score -= 12
                risks.append(f"PE 较行业中位数溢价约 {premium_to_industry:.1f}%，对增长兑现敏感。")
            elif premium_to_industry < 0:
                score += 10
                observations.append(f"PE 低于行业中位数约 {abs(premium_to_industry):.1f}%，相对估值不激进。")
            else:
                observations.append(f"PE 较行业中位数溢价约 {premium_to_industry:.1f}%。")
        if pe <= 30:
            score += 12
            observations.append(f"当前 PE 约 {pe:.1f}，绝对估值压力相对可控。")
        elif pe >= 70:
            score -= 12
            risks.append(f"当前 PE 约 {pe:.1f}，需要高增长持续兑现。")
        else:
            observations.append(f"当前 PE 约 {pe:.1f}，处于增长股常见敏感区间。")
    else:
        score -= 5
        risks.append("PE 数值缺失，估值画像可靠性下降。")

    if target_upside is not None:
        score += max(min(target_upside * 0.25, 12), -12)
        if target_upside >= 15:
            observations.append(f"机构平均目标价隐含约 {target_upside:.1f}% 上行空间。")
        elif target_upside <= -5:
            risks.append(f"机构平均目标价低于现价约 {abs(target_upside):.1f}%，预期可能偏满。")
        else:
            observations.append("机构平均目标价与现价接近，需关注后续评级修正。")

    if peer_percentile is not None:
        observations.append(f"在可比 PE 样本中的估值分位约 {peer_percentile:.1f}%。")

    if not observations:
        observations.append("估值数据有限，暂以评级、同业和价格行为作为补充锚。")
    if not risks:
        risks.append("未发现强估值红旗，但估值仍会随增长预期和利率环境变化。")

    score = round(clamp(score), 1)
    if score >= 68:
        verdict = "估值支撑较好"
    elif score >= 50:
        verdict = "估值中性"
    else:
        verdict = "估值敏感"

    return {
        "score": score,
        "verdict": verdict,
        "pe": pe,
        "industry_median": median,
        "premium_to_industry": premium_to_industry,
        "target_upside": target_upside,
        "peer_percentile": peer_percentile,
        "peer_rank": peer_rank,
        "peer_count": len(peer_pes),
        "observations": observations[:5],
        "risks": risks[:5],
    }


def summarize_insider_trades(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate insider trading activities (buys vs sells, top sellers)."""
    sell_value = sum(item.get("value") or 0 for item in trades if str(item.get("type", "")).upper() == "SELL")
    buy_value = sum(item.get("value") or 0 for item in trades if str(item.get("type", "")).upper() in ("BUY", "PURCHASE"))
    grant_count = sum(1 for item in trades if str(item.get("type", "")).upper() == "GRANT")
    gift_count = sum(1 for item in trades if str(item.get("type", "")).upper() == "GIFT")
    tax_count = sum(1 for item in trades if str(item.get("type", "")).upper() == "TAX")
    top_sellers: Dict[str, float] = {}
    for item in trades:
        if str(item.get("type", "")).upper() == "SELL":
            owner = item.get("owner") or "Unknown"
            top_sellers[owner] = top_sellers.get(owner, 0) + (item.get("value") or 0)
    return {
        "trade_count": len(trades),
        "sell_value": sell_value,
        "buy_value": buy_value,
        "grant_count": grant_count,
        "gift_count": gift_count,
        "tax_count": tax_count,
        "top_sellers": [
            {"owner": owner, "value": value}
            for owner, value in sorted(top_sellers.items(), key=lambda pair: pair[1], reverse=True)[:5]
        ],
    }


def analyze_management_governance(
    executives: List[Dict[str, Any]],
    shareholders: List[Dict[str, Any]],
    insider_trades: List[Dict[str, Any]],
    insider_summary: Dict[str, Any],
    controversies: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Evaluate executive leadership, ownership concentration, and insider sentiment."""
    score = 58.0
    positives: List[str] = []
    red_flags: List[str] = []
    questions: List[str] = []

    if executives:
        score += min(10, len(executives) * 1.5)
        ceo = next((item for item in executives if "CEO" in str(item.get("title", "")).upper()), executives[0])
        positives.append(f"已识别核心高管：{ceo.get('name')}，{ceo.get('title') or '职位待核验'}")
    else:
        score -= 10
        questions.append("高管数据缺失，需要补充 CEO/CFO/董事会资料。")

    if shareholders:
        top_holder = shareholders[0]
        percent = top_holder.get("percent")
        if percent is not None:
            if 3 <= percent <= 20:
                score += 6
                positives.append(f"第一大股东持股约 {percent:.2f}%，存在一定股东约束。")
            elif percent > 40:
                score -= 4
                red_flags.append(f"第一大股东持股约 {percent:.2f}%，需关注控制权和中小股东保护。")
        positives.append(f"主要股东数据覆盖 {len(shareholders)} 条。")
    else:
        score -= 6
        questions.append("主要股东数据缺失，难以判断股东结构。")

    sell_value = insider_summary.get("sell_value") or 0
    buy_value = insider_summary.get("buy_value") or 0
    trade_count = insider_summary.get("trade_count") or 0
    if trade_count:
        if buy_value > sell_value and buy_value > 0:
            score += 8
            positives.append(f"内部人买入金额约 ${buy_value / 1_000_000:.1f}M，高于卖出。")
        elif sell_value > 0 and sell_value > max(buy_value * 3, 1_000_000):
            penalty = min(14, math.log10(max(sell_value, 1)) * 1.8)
            score -= penalty
            red_flags.append(f"内部人卖出金额约 ${sell_value / 1_000_000:.1f}M，需要区分计划性减持与信心变化。")
        else:
            positives.append(f"内部人交易共 {trade_count} 条，未形成单边强信号。")
    else:
        questions.append("未获取到近期内部人交易，不能据此判断管理层信心。")

    severe_controversies = [item for item in (controversies or []) if item.get("severity") in ("high", "medium")]
    if severe_controversies:
        score -= min(12, len(severe_controversies) * 3)
        red_flags.append(f"争议雷达发现 {len(severe_controversies)} 条中高关注事件，可能影响管理层可信度。")

    if not red_flags:
        red_flags.append("当前规则未发现强治理红旗，但仍需核验审计意见、薪酬激励和关联交易。")
    questions.extend(
        [
            "CEO/CFO 任期、过往资本配置和并购记录是否创造长期股东价值？",
            "股权激励指标是否绑定自由现金流、ROIC 或长期股价表现？",
            "近期 Form 4 交易是否属于 10b5-1 计划性安排？",
        ]
    )

    score = round(clamp(score), 1)
    if score >= 75:
        verdict = "治理画像偏强"
    elif score >= 60:
        verdict = "治理画像中性偏好"
    elif score >= 45:
        verdict = "治理画像需观察"
    else:
        verdict = "治理风险偏高"

    return {
        "score": score,
        "verdict": verdict,
        "positives": positives[:5],
        "red_flags": red_flags[:5],
        "questions": questions[:5],
    }


def analyze_risk_radar(
    short_positions: Dict[str, Any],
    controversies: List[Dict[str, Any]],
    filings: List[Dict[str, Any]],
    news: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Detect short interest spikes, controversies, legal and filing red flags."""
    risk_score = 18.0
    key_risks: List[str] = []
    thesis_breakers: List[str] = []

    latest_short = short_positions.get("latest") if short_positions else None
    if latest_short:
        short_rate = latest_short.get("short_rate")
        days_to_cover = latest_short.get("days_to_cover")
        if short_rate is not None and short_rate >= 0.05:
            risk_score += min(18, short_rate * 220)
            key_risks.append(f"做空比例约 {short_rate * 100:.2f}%，空头拥挤度偏高。")
        if days_to_cover is not None and days_to_cover >= 3:
            risk_score += min(10, days_to_cover * 1.8)
            key_risks.append(f"Days to Cover 约 {days_to_cover:.1f}，消息冲击时波动可能放大。")

    high = [item for item in controversies if item.get("severity") == "high"]
    medium = [item for item in controversies if item.get("severity") == "medium"]
    if high or medium:
        risk_score += min(34, len(high) * 12 + len(medium) * 6)
        key_risks.append(f"历史争议检出 {len(high)} 条高风险、{len(medium)} 条中风险事件。")
        for item in (high + medium)[:3]:
            thesis_breakers.append(f"{item.get('category')}：{item.get('title')}")

    filing_titles = " ".join(item.get("title", "") or "" for item in filings[:8]).lower()
    special_risk_keywords = ("investigation", "litigation", "subpoena", "restatement", "material weakness", "sec probe", "lawsuit")
    if any(term in filing_titles for term in special_risk_keywords):
        risk_score += 8
        key_risks.append("近期公告/SEC 文件中检出非日常监管调查、诉讼或财务重述风险。")

    news_titles = " ".join(item.get("title", "") or "" for item in news[:12]).lower()
    if any(term in news_titles for term in ("cuts guidance", "probe", "lawsuit", "misses", "recall", "downgrade")):
        risk_score += 8
        key_risks.append("近期新闻标题出现负面催化词，需要复核影响范围。")

    if not key_risks:
        key_risks.append("未检出显著重大公开违规或财务警报信号。")
    if not thesis_breakers:
        thesis_breakers.append("未检出已知历史公开争议事项；重点跟踪下期财报指引兑现度。")

    risk_score = round(clamp(risk_score), 1)
    if risk_score >= 70:
        level = "高"
    elif risk_score >= 45:
        level = "中"
    else:
        level = "低"

    return {
        "risk_score": risk_score,
        "level": level,
        "key_risks": key_risks[:5],
        "thesis_breakers": thesis_breakers[:6],
    }


def build_factor_breakdown(
    quote: Dict[str, Any],
    technical: Dict[str, Any],
    news: List[Dict[str, Any]],
    valuation: Optional[Dict[str, Any]],
    rating: Optional[Dict[str, Any]],
    financials: Optional[Dict[str, Any]],
    risk_radar: Optional[Dict[str, Any]],
    regime_weights: Optional[Dict[str, int]] = None,
    capex_verified: Optional[bool] = None,
    risk_multiplier: float = 1.0,
) -> Dict[str, Any]:
    """
    Break down multi-factor attribution: Momentum, Liquidity, Quality, Valuation, Catalyst, Risk.
    Supports dynamic factor weighting from Discrete Macro Regime State Machine (Step 7)
    and Capex Reality Gate validation (Step 3).
    """
    weights = {
        "momentum": 20,
        "liquidity": 15,
        "quality": 20,
        "valuation": 15,
        "catalyst": 20,
    }
    if regime_weights:
        weights.update(regime_weights)

    factors: List[Dict[str, Any]] = []

    ret20 = technical.get("returns", {}).get("20d")
    ret60 = technical.get("returns", {}).get("60d")
    momentum_score = 50.0
    if ret20 is not None:
        momentum_score += max(min(ret20 * 1.2, 25), -25)
    if ret60 is not None:
        momentum_score += max(min(ret60 * 0.55, 20), -20)
    if technical.get("above_ma20"):
        momentum_score += 8
    if technical.get("above_ma60"):
        momentum_score += 8
    factors.append(
        {
            "key": "momentum",
            "name": "价格动量",
            "score": round(clamp(momentum_score), 1),
            "weight": weights.get("momentum", 20),
            "evidence": [
                f"20日涨跌 {ret20:.1f}%" if ret20 is not None else "20日涨跌数据不足",
                f"60日涨跌 {ret60:.1f}%" if ret60 is not None else "60日涨跌数据不足",
                "站上20/60日均线" if technical.get("above_ma20") and technical.get("above_ma60") else "均线结构仍需确认",
            ],
        }
    )

    volume_ratio = technical.get("volume_ratio_20d")
    liquidity_score = 50.0
    if volume_ratio is not None:
        liquidity_score += max(min((volume_ratio - 1) * 45, 28), -22)
    turnover = quote.get("turnover") or 0.0
    if turnover >= 1_000_000_000:
        liquidity_score += 10
    factors.append(
        {
            "key": "liquidity",
            "name": "成交活跃",
            "score": round(clamp(liquidity_score), 1),
            "weight": weights.get("liquidity", 15),
            "evidence": [
                f"量能倍率 {volume_ratio:.2f}x" if volume_ratio is not None else "量能倍率数据不足",
                f"成交额约 {turnover / 100_000_000:.2f} 亿" if turnover else "成交额缺失",
            ],
        }
    )

    # 3. 基本面质量因子 (严谨口径：单期利润表无现金流，封顶 70 分)
    quality_score = 45.0
    quality_evidence: List[str] = []
    has_quality_data = False
    if financials and financials.get("indicators"):
        has_quality_data = True
        quality_score += 8
        quality_evidence.append("单期利润表，无现金流 (质量分封顶 70 分)")
        for item in financials["indicators"][:8]:
            name = item.get("name") or item.get("field")
            yoy = number_from(item.get("yoy"))
            val = item.get("value")
            if yoy is not None:
                quality_score += max(min(yoy * 35, 10), -10)
                quality_evidence.append(f"{name} YoY {yoy * 100:.1f}%")
            elif val:
                quality_evidence.append(f"{name} {val}")
            if len(quality_evidence) >= 3:
                break
        quality_score = min(quality_score, 70.0)
    else:
        quality_evidence.append("财务快照缺失，不计入综合评分")

    factors.append(
        {
            "key": "quality",
            "name": "基本面质量 (单期利润表)",
            "score": round(clamp(quality_score), 1) if has_quality_data else None,
            "weight": weights.get("quality", 20) if has_quality_data else 0,
            "has_data": has_quality_data,
            "evidence": quality_evidence[:3],
        }
    )

    # 4. 估值合理性因子
    valuation_score = 50.0
    valuation_evidence: List[str] = []
    pe = number_from(valuation.get("pe_raw") or valuation.get("pe")) if valuation else None
    ps = number_from(valuation.get("ps_raw") or valuation.get("ps")) if valuation else None
    pb = number_from(valuation.get("pb_raw") or valuation.get("pb")) if valuation else None
    peer_premium = number_from(valuation.get("peer_premium_pct") or valuation.get("premium_pct")) if valuation else None

    has_val_data = False
    if pe is not None and pe > 0:
        has_val_data = True
        if pe <= 25:
            valuation_score += 15
            valuation_evidence.append(f"PE {pe:.1f}x，相对不激进")
        elif pe <= 55:
            valuation_score += 2
            valuation_evidence.append(f"PE {pe:.1f}x，需要持续增长兑现")
        else:
            valuation_score -= 16
            valuation_evidence.append(f"PE {pe:.1f}x，高估值对预期极其敏感")
    elif ps is not None and ps > 0:
        has_val_data = True
        if ps <= 5.0:
            valuation_score += 12
            valuation_evidence.append(f"市销率 PS {ps:.1f}x，相对平价")
        elif ps <= 15.0:
            valuation_score -= 2
            valuation_evidence.append(f"市销率 PS {ps:.1f}x，成长溢价")
        elif ps <= 30.0:
            valuation_score -= 14
            valuation_evidence.append(f"市销率 PS {ps:.1f}x，高成长但倍数承压")
        else:
            valuation_score -= 22
            valuation_evidence.append(f"市销率 PS {ps:.1f}x，极度高估值风险")
    elif pe is not None and pe <= 0:
        has_val_data = True
        valuation_score -= 18
        valuation_evidence.append("PE 为负或异常，缺乏稳健利润支撑")

    if peer_premium is not None:
        has_val_data = True
        if peer_premium > 50.0:
            valuation_score -= 8
            valuation_evidence.append(f"同业估值显著高溢价 +{peer_premium:.1f}%")
        elif peer_premium < -15.0:
            valuation_score += 8
            valuation_evidence.append(f"同业估值折价 {peer_premium:.1f}%，具备比价优势")

    if rating and rating.get("target") and quote.get("last"):
        upside = (rating["target"] / quote["last"] - 1) * 100
        valuation_score += max(min(upside * 0.35, 12), -12)
        valuation_evidence.append(f"机构目标价隐含 {upside:.1f}% 空间")
        has_val_data = True

    if not has_val_data:
        valuation_evidence.append("估值乘数数据缺失，不计入综合评分")

    factors.append(
        {
            "key": "valuation",
            "name": "估值合理性",
            "score": round(clamp(valuation_score), 1) if has_val_data else None,
            "weight": weights.get("valuation", 15) if has_val_data else 0,
            "has_data": has_val_data,
            "evidence": valuation_evidence[:3],
        }
    )

    # 5. 消息与催化因子 (规矩3：整改按要求改为展示项，不进 65 分闸门，新闻条数与关键词不再加分)
    catalyst_evidence = [f"近期市场资讯 {len(news)} 条 (仅作展示，不计入综合评分)"]
    if rating and rating.get("recommend"):
        catalyst_evidence.append(f"机构建议评级: {rating['recommend']}")
    factors.append(
        {
            "key": "catalyst",
            "name": "消息与催化 (仅展示)",
            "score": None,
            "weight": 0,
            "has_data": bool(news),
            "is_display_only": True,
            "evidence": catalyst_evidence[:3],
        }
    )

    # 6. 风险惩罚
    risk_penalty = 0.0
    risk_evidence: List[str] = []
    volatility = technical.get("volatility_20d")
    drawdown = technical.get("max_drawdown_60d")
    if volatility is not None and volatility > 65:
        risk_penalty -= 4
        risk_evidence.append(f"20日年化波动率 {volatility:.1f}%")
    if drawdown is not None and drawdown < -20:
        risk_penalty -= 4
        risk_evidence.append(f"60日最大回撤 {drawdown:.1f}%")
    controversies = (risk_radar or {}).get("controversies") or []
    severe_events = [item for item in controversies if item.get("severity") in ("high", "medium")]
    if severe_events:
        risk_penalty -= min(8, 2 + len(severe_events) * 2)
        risk_evidence.append(f"争议雷达发现 {len(severe_events)} 条中高风险事件")
    if not risk_evidence:
        risk_evidence.append("规则未识别出强风险惩罚项")
    factors.append(
        {
            "key": "risk",
            "name": "风险惩罚",
            "score": risk_penalty,
            "weight": -10,
            "evidence": risk_evidence[:3],
        }
    )

    # 规矩1：没有数就空着，空着的项不进综合分，核心项缺失直接不给综合分
    valid_positive = [item for item in factors if item.get("weight", 0) > 0 and item.get("score") is not None]
    weighted_positive = sum(item["score"] * item["weight"] for item in valid_positive)
    positive_weight = sum(item["weight"] for item in valid_positive)

    if (not has_quality_data and not has_val_data) or positive_weight < 30:
        composite = None
    else:
        raw_comp = weighted_positive / positive_weight if positive_weight else 50.0
        effective_risk_penalty = risk_penalty * (risk_multiplier if risk_multiplier is not None else 1.0)
        composite = round(clamp(raw_comp + effective_risk_penalty), 1)

    for item in factors:
        if item.get("weight", 0) > 0 and positive_weight and item.get("score") is not None:
            item["contribution"] = round(item["score"] * item["weight"] / positive_weight, 2)
        else:
            item["contribution"] = 0.0

    return {
        "composite": composite,
        "factors": factors,
        "formula": "多因子分 = Σ(有效因子分 × 权重) / Σ有效正向权重 + 风险惩罚 (催化不参与打分)",
        "positive_weight": positive_weight,
        "weighted_positive": round(weighted_positive, 2),
        "risk_penalty": round(risk_penalty, 2),
    }


def analyze_capital_allocation_and_shareholder_yield(
    financials: Optional[Dict[str, Any]],
    valuation: Optional[Dict[str, Any]],
    quote: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Evaluate Buy-Side Capital Allocation & Balance Sheet Reality:
    1. Ground-Truth Balance Sheet & Leverage (Debt Ratio, Negative Equity Detection)
    2. Real DuPont Decomposition (Net Margin, Asset Turnover, Equity Multiplier)
    3. Shareholder Yield (Only Verified Dividend Yield, No Fabricated Buyback Yield)
    4. Honest Disclosure: Flags missing Cash Flow / Interest Expense data instead of fabricating ROIC/WACC.
    """
    indicators = indicator_lookup(financials)
    sym = (quote or {}).get("symbol") or ""
    p = (quote or {}).get("last") or 0.0

    roe = financial_value(indicators, "roe")
    net_margin = financial_value(indicators, "net_profit_margin")
    total_assets = financial_value(indicators, "total_assets")
    total_debts = financial_value(indicators, "total_debts")
    revenue = financial_value(indicators, "operating_revenue")
    net_profit = financial_value(indicators, "net_profit")
    bps = financial_value(indicators, "bps")

    # 1. Real Balance Sheet & Debt Ratios
    debt_assets_pct = None
    if total_assets and total_debts is not None and total_assets > 0:
        debt_assets_pct = round((total_debts / total_assets) * 100, 1)

    equity = (total_assets - total_debts) if (total_assets is not None and total_debts is not None) else None
    equity_val = round(equity, 2) if equity is not None else None

    # Detect negative book equity (e.g. MCD, SBUX, HD) caused by massive historical buybacks
    is_negative_equity = (equity is not None and equity <= 0)

    # 2. Real DuPont Decomposition
    nm_val = round(net_margin, 1) if net_margin is not None else (
        round((net_profit / revenue) * 100, 1) if (net_profit and revenue and revenue > 0) else None
    )
    asset_turnover = round(revenue / total_assets, 2) if (revenue and total_assets and total_assets > 0) else None
    
    equity_multiplier = None
    if total_assets and equity and equity > 0:
        equity_multiplier = round(total_assets / equity, 2)

    if is_negative_equity:
        dupont_driver = "负净资产特殊资本结构 (Negative Book Equity)"
        dupont_desc = f"公司账面净资产为负值 (${equity_val}M)，通常源于长期以超过净利的规模大额回购注销普通股。常规权益乘数与账面 ROE ({roe}%) 已失真，应重点考察净利率 ({nm_val}%) 与资产周转率 ({asset_turnover}x)。"
    elif nm_val is not None and nm_val >= 25.0:
        dupont_driver = "高净利率与产品定价权驱动 (Margin-Driven)"
        dupont_desc = f"核心回报引擎源于高达 {nm_val}% 的净利率，体现出较强的产品壁垒与定价护城河。"
    elif asset_turnover is not None and asset_turnover >= 1.2:
        dupont_driver = "高效资产周转驱动 (Turnover-Driven)"
        dupont_desc = f"核心回报由资产周转效率 (年化周转 {asset_turnover} 次) 驱动，体现运营与供应链流转效率。"
    elif equity_multiplier is not None and equity_multiplier >= 2.5:
        dupont_driver = "适度财务杠杆驱动 (Leverage-Amplified)"
        dupont_desc = f"ROE 受到财务杠杆乘数 ({equity_multiplier}x) 放大，资产负债率约 {debt_assets_pct}%，需关注利息与债务安全性。"
    else:
        dupont_driver = "均衡运营型驱动 (Balanced Profile)"
        dupont_desc = f"净利率 ({nm_val or '--'}%) 与周转率 ({asset_turnover or '--'}x) 处于行业稳态区间。"

    # 3. Shareholder Yield (Real Dividend Yield from Longbridge, No Fake Buyback Assumptions)
    dividend_yield_pct = (valuation or {}).get("dividend_yield")
    if dividend_yield_pct is None and (quote or {}).get("dividend_yield"):
        dividend_yield_pct = quote.get("dividend_yield")
    dividend_yield_val = round(float(dividend_yield_pct), 2) if (dividend_yield_pct is not None and float(dividend_yield_pct) >= 0) else None

    # 4. Solvency Assessment Based on Real Balance Sheet (No Fake 45x/16.5x/6.2x Interest Coverage)
    if is_negative_equity:
        safety_grade = "负净资产结构 · 需关注债务再融资"
        safety_badge = "CAUTION"
        stress_test = "账面净资产被回购压缩为负，虽通常伴随充沛经营现金流，但账面资产缓冲垫为零，在信用收紧或利率长期处于高位时需关注债务滚续风险。"
    elif debt_assets_pct is not None:
        if debt_assets_pct <= 35.0:
            safety_grade = "低杠杆健康型资产负债表"
            safety_badge = "FORTRESS"
            stress_test = f"资产负债率仅 {debt_assets_pct}%，债务负担轻，具备充足的抗宏观下行与加息周期安全垫。"
        elif debt_assets_pct <= 60.0:
            safety_grade = "中度适中杠杆"
            safety_badge = "HEALTHY"
            stress_test = f"资产负债率约 {debt_assets_pct}%，处于行业可控中性区间，偿债压力适中。"
        else:
            safety_grade = "高财务杠杆监控"
            safety_badge = "CAUTION"
            stress_test = f"资产负债率达 {debt_assets_pct}%，债务占比较重，若营收增速下滑需关注利息偿付对利润的侵蚀。"
    else:
        safety_grade = "资产负债数据不足"
        safety_badge = "NEUTRAL"
        stress_test = "长桥未返回完整资产负债表快照，偿债压力需复核官方财报。"

    return {
        "title": "资本结构、杜邦拆解与股东回报 (Capital Structure & Shareholder Yield)",
        "summary_verdict": f"资产负债结构评定为【{safety_grade}】(资产负债率 {debt_assets_pct or '--'}%)，杜邦驱动类型为【{dupont_driver}】。{f'长桥当前披露股息率为 {dividend_yield_val}%' if dividend_yield_val is not None else '长桥单期报表未披露股息率'}；由于长桥单期报表未包含现金流量表，回购明细与利息保障倍数未取得。",
        "capital_persona": {
            "name": "真实报表透视型",
            "tagline": "基于长桥最新一期公开财报事实核算，不采用任何经验常数编造数据",
            "badge": safety_badge
        },
        "cash_waterfall": None,  # 严肃买方原则：单期报表未取得现金流量表，绝不凭空捏造瀑布图
        "waterfall_disclaimer": "长桥基础接口未提供多期现金流量表与 Capex 明细，系统已关闭虚拟现金流瀑布图。",
        "economic_spread": {
            "roic_pct": None,
            "wacc_pct": None,
            "spread_pct": None,
            "status": "指标未取得",
            "note": "长桥单期报表未披露 EBIT、所得税率及付息债务结构，系统杜绝用 ROE 盲目反推虚假 ROIC。"
        },
        "dupont_decomposition": {
            "net_margin_pct": nm_val,
            "asset_turnover": asset_turnover,
            "equity_multiplier": equity_multiplier,
            "roe_pct": round(roe, 1) if (roe is not None and not is_negative_equity) else roe,
            "is_negative_equity": is_negative_equity,
            "core_driver": dupont_driver,
            "desc": dupont_desc
        },
        "shareholder_yield": {
            "total_yield_pct": dividend_yield_val,
            "dividend_yield_pct": dividend_yield_val,
            "buyback_yield_pct": None,  # 未取得现金流回购数据，绝不编造
            "buyback_quality": "现金流量表未取得" if dividend_yield_val is None else "仅取得已公布股息率",
            "comment": "长桥未返回完整现金流量表中的股票回购净额与现金流去向，系统仅如实呈现已核实股息率。"
        },
        "balance_sheet_fortress": {
            "debt_to_assets_pct": debt_assets_pct,
            "total_assets": total_assets,
            "total_debts": total_debts,
            "equity": equity_val,
            "is_negative_equity": is_negative_equity,
            "interest_coverage_x": None,  # 绝不硬填 45x/16.5x/6.2x
            "interest_coverage_note": "长桥单期报表未单独披露利息支出，利息保障倍数未取得；以资产负债率评估账面财务杠杆。",
            "grade": safety_grade,
            "badge": safety_badge,
            "stress_test": stress_test,
            "net_margin_pct": nm_val,
            "roe_pct": roe
        }
    }
