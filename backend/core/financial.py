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
    return value * 100 if abs(value) <= 2 else value


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
            "score": 40,
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
    if score >= 78:
        verdict = "财务质量强"
    elif score >= 62:
        verdict = "财务质量较好"
    elif score >= 45:
        verdict = "财务质量中性"
    else:
        verdict = "财务质量承压"

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
    if any(term in filing_titles for term in ("8-k", "investigation", "litigation", "risk", "10-k")):
        risk_score += 8
        key_risks.append("近期公告/SEC 文件中存在需要精读的风险类文件。")

    news_titles = " ".join(item.get("title", "") or "" for item in news[:12]).lower()
    if any(term in news_titles for term in ("cuts guidance", "probe", "lawsuit", "misses", "recall", "downgrade")):
        risk_score += 8
        key_risks.append("近期新闻标题出现负面催化词，需要复核影响范围。")

    if not key_risks:
        key_risks.append("规则未发现强风险信号，但不等于风险不存在。")
    thesis_breakers.extend(
        [
            "下一份财报或管理层指引显著低于市场预期。",
            "核心业务增长放缓但估值仍依赖高增长假设。",
            "监管调查、重大诉讼或内部控制问题升级。",
        ]
    )

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

    quality_score = 45.0
    quality_evidence: List[str] = []
    if financials and financials.get("indicators"):
        quality_score += 8
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
    else:
        quality_evidence.append("财务快照缺失，质量评分降权")
    factors.append(
        {
            "key": "quality",
            "name": "基本面质量",
            "score": round(clamp(quality_score), 1),
            "weight": weights.get("quality", 20),
            "evidence": quality_evidence[:3],
        }
    )

    valuation_score = 50.0
    valuation_evidence: List[str] = []
    pe = valuation.get("pe_raw") if valuation else None
    if pe is not None:
        if pe <= 0:
            valuation_score -= 18
            valuation_evidence.append("PE 为负或异常，估值解释难度较高")
        elif pe <= 25:
            valuation_score += 15
            valuation_evidence.append(f"PE {pe:.1f}，相对不激进")
        elif pe <= 60:
            valuation_score += 2
            valuation_evidence.append(f"PE {pe:.1f}，需要增长兑现")
        else:
            valuation_score -= 15
            valuation_evidence.append(f"PE {pe:.1f}，估值对预期敏感")
    else:
        valuation_evidence.append("估值数据缺失")
    if rating and rating.get("target") and quote.get("last"):
        upside = (rating["target"] / quote["last"] - 1) * 100
        valuation_score += max(min(upside * 0.35, 12), -12)
        valuation_evidence.append(f"机构目标价隐含 {upside:.1f}% 空间")
    factors.append(
        {
            "key": "valuation",
            "name": "估值合理性",
            "score": round(clamp(valuation_score), 1),
            "weight": weights.get("valuation", 15),
            "evidence": valuation_evidence[:3],
        }
    )

    catalyst_score = 45.0 + min(len(news) * 3, 24)
    catalyst_evidence = [f"近期新闻 {len(news)} 条"]
    if rating and rating.get("recommend"):
        catalyst_score += 6
        catalyst_evidence.append(f"机构建议 {rating['recommend']}")
    catalyst_terms = " ".join(item.get("title", "") for item in news[:8]).lower()
    if any(term in catalyst_terms for term in ("earnings", "guidance", "launch", "approval", "ai", "财报", "指引")):
        catalyst_score += 8
        catalyst_evidence.append("新闻中出现财报/产品/AI 等潜在催化词")

    if capex_verified is False:
        catalyst_score -= 14.0
        catalyst_evidence.append("⚠️ 另类数据未获财报 Capex/研发验证，扣除冲榜虚火分")
    elif capex_verified is True:
        catalyst_score += 6.0
        catalyst_evidence.append("✅ 另类爆款获资本开支/研发费用真实财务支撑")

    factors.append(
        {
            "key": "catalyst",
            "name": "消息与催化",
            "score": round(clamp(catalyst_score), 1),
            "weight": weights.get("catalyst", 20),
            "evidence": catalyst_evidence[:3],
        }
    )

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

    weighted_positive = sum(item["score"] * item["weight"] for item in factors if item["weight"] > 0)
    positive_weight = sum(item["weight"] for item in factors if item["weight"] > 0)
    composite = weighted_positive / positive_weight if positive_weight else 50.0
    composite += risk_penalty
    for item in factors:
        if item["weight"] > 0 and positive_weight:
            item["contribution"] = round(item["score"] * item["weight"] / positive_weight, 2)
        else:
            item["contribution"] = round(item["score"], 2)
    return {
        "composite": round(clamp(composite), 1),
        "factors": factors,
        "formula": "多因子分 = Σ(正向因子分 × 权重) / Σ正向权重 + 风险惩罚",
        "positive_weight": positive_weight,
        "weighted_positive": round(weighted_positive, 2),
        "risk_penalty": round(risk_penalty, 2),
    }
