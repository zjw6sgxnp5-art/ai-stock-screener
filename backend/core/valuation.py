"""
Institutional Multi-Model Valuation Engine.
Provides DCF (Discounted Cash Flow), Relative Multiples, Historical Valuation Band,
and Reverse DCF (Market Implied Growth Rate) with Margin of Safety analysis.
"""
from typing import Any, Dict, List, Optional
import math


def calculate_dcf_value(
    base_fcf_per_share: float,
    growth_rate: float,
    discount_rate: float = 0.09,
    terminal_growth_rate: float = 0.025,
    forecast_years: int = 5,
) -> float:
    """Calculate intrinsic per-share value using multi-stage DCF."""
    if base_fcf_per_share <= 0:
        return 0.0
    
    # 5-year discrete cash flow projection
    pv_forecast = 0.0
    curr_fcf = base_fcf_per_share
    for t in range(1, forecast_years + 1):
        curr_fcf *= (1.0 + growth_rate)
        pv_forecast += curr_fcf / ((1.0 + discount_rate) ** t)
    
    # Terminal value calculation (Gordon Growth Model)
    if discount_rate <= terminal_growth_rate:
        discount_rate = terminal_growth_rate + 0.02
    
    terminal_fcf = curr_fcf * (1.0 + terminal_growth_rate)
    terminal_value = terminal_fcf / (discount_rate - terminal_growth_rate)
    pv_terminal = terminal_value / ((1.0 + discount_rate) ** forecast_years)
    
    return round(pv_forecast + pv_terminal, 2)


def calculate_reverse_dcf_implied_growth(
    current_price: float,
    base_fcf_per_share: float,
    discount_rate: float = 0.09,
    terminal_growth_rate: float = 0.025,
    forecast_years: int = 5,
) -> float:
    """
    Binary search for market implied growth rate.
    What 5-year CAGR does the current market price price-in?
    """
    if base_fcf_per_share <= 0 or current_price <= 0:
        return 0.0
    
    low = -0.30  # -30% CAGR
    high = 1.00  # +100% CAGR
    implied_g = 0.0
    
    for _ in range(35):
        mid = (low + high) / 2.0
        val = calculate_dcf_value(
            base_fcf_per_share=base_fcf_per_share,
            growth_rate=mid,
            discount_rate=discount_rate,
            terminal_growth_rate=terminal_growth_rate,
            forecast_years=forecast_years,
        )
        if abs(val - current_price) < 0.1:
            implied_g = mid
            break
        elif val < current_price:
            low = mid
        else:
            high = mid
        implied_g = mid
    
    return round(implied_g * 100, 1)


def calculate_dcf_sensitivity_table(
    base_fcf_per_share: float,
    base_growth_rate: float,
    current_price: float,
    wacc_rates: Optional[List[float]] = None,
    terminal_rates: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """
    Generate WACC vs Terminal Growth Rate 2D sensitivity matrix.
    WACC: 8.0%, 8.5%, 9.0%, 9.5%, 10.0%
    Terminal g: 2.0%, 2.5%, 3.0%
    """
    if wacc_rates is None:
        wacc_rates = [0.080, 0.085, 0.090, 0.095, 0.100]
    if terminal_rates is None:
        terminal_rates = [0.020, 0.025, 0.030]

    matrix_rows = []
    for w in wacc_rates:
        row_cells = []
        for tg in terminal_rates:
            val = calculate_dcf_value(
                base_fcf_per_share=base_fcf_per_share,
                growth_rate=base_growth_rate,
                discount_rate=w,
                terminal_growth_rate=tg,
            )
            delta_pct = round(((val - current_price) / current_price) * 100, 1) if current_price > 0 else 0.0
            row_cells.append({
                "wacc": round(w * 100, 1),
                "terminal_g": round(tg * 100, 1),
                "fair_price": val,
                "delta_pct": delta_pct,
                "is_undervalued": delta_pct >= 0,
            })
        matrix_rows.append({
            "wacc_pct": round(w * 100, 1),
            "cells": row_cells
        })

    return {
        "wacc_header": [f"{round(w * 100, 1)}%" for w in wacc_rates],
        "terminal_g_header": [f"{round(tg * 100, 1)}%" for tg in terminal_rates],
        "rows": matrix_rows
    }


def build_valuation_matrix(
    symbol: str,
    quote: Dict[str, Any],
    valuation: Optional[Dict[str, Any]],
    financials: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Institutional Relative Valuation Engine.
    Strictly adheres to buy-side ground-truth principles:
    1. Only uses verified Longbridge live multiples (PE, PS, PB, dividend yield, peer median, peer rank).
    2. Does NOT fabricate Free Cash Flow (FCF) proxies from stock price or PE multiples.
    3. Does NOT output pseudo-DCF corridors or fake margins of safety when cash flow statements are absent.
    4. Does NOT invert peer rank to misrepresent it as historical percentile (prevents PLTR bug).
    """
    price = quote.get("last") or 0.0
    val_dict = valuation if isinstance(valuation, dict) else {}
    
    pe_raw = val_dict.get("pe_raw")
    ps_raw = val_dict.get("ps_raw")
    pb_raw = val_dict.get("pb_raw")
    dividend_yield = val_dict.get("dividend_yield")
    
    ind_type = (val_dict.get("indicator") or "pe").lower()
    ind_label = val_dict.get("indicator_label") or ("P/S" if ind_type == "ps" else ("P/B" if ind_type == "pb" else "P/E"))
    metric_val = val_dict.get("metric_value") or pe_raw or ps_raw or pb_raw
    
    industry_median = val_dict.get("industry_median")
    peer_rank = val_dict.get("peer_rank")
    peer_total = val_dict.get("peer_total")

    # 1. Relative Peer Comparison (Longbridge Ground Truth)
    peer_premium_pct = None
    if metric_val is not None and industry_median is not None and industry_median > 0:
        peer_premium_pct = round(((metric_val - industry_median) / industry_median) * 100, 1)

    # 2. Honest Peer Ranking Direction & Distribution Analysis
    rank_ratio_pct = None
    rank_tier = "同业排位数据不足"
    rank_desc = "长桥单期同业对比样本未完整披露排位。"
    if peer_rank is not None and peer_total is not None and peer_total > 0:
        # peer_rank is 1-indexed from lowest multiple (cheapest) to highest multiple (most expensive)
        rank_ratio_pct = round((peer_rank / peer_total) * 100, 1)
        expensive_pct = round(100.0 - rank_ratio_pct, 1)
        if rank_ratio_pct >= 85.0:
            rank_tier = f"同业最高估值头部梯队 (前 {max(0.1, expensive_pct)}% 昂贵区)"
            rank_desc = f"在同业 {peer_total} 家公司中估值从低到高排第 {peer_rank} 名。仅有 {expensive_pct}% 的同业比该标的更贵，处于行业高溢价梯队，需持续超预期业绩支撑。"
        elif rank_ratio_pct >= 60.0:
            rank_tier = "同业偏高估值梯队 (60%~85% 分位)"
            rank_desc = f"在同业 {peer_total} 家公司中位列第 {peer_rank} 名，估值高于 {rank_ratio_pct}% 的同业，存在成长溢价。"
        elif rank_ratio_pct >= 40.0:
            rank_tier = "同业合理中枢梯队 (40%~60% 分位)"
            rank_desc = f"在同业 {peer_total} 家公司中位列第 {peer_rank} 名，估值贴近行业中位数中枢。"
        elif rank_ratio_pct >= 15.0:
            rank_tier = "同业中低估值梯队 (15%~40% 分位)"
            rank_desc = f"在同业 {peer_total} 家公司中位列第 {peer_rank} 名，估值低于行业 {expensive_pct}% 的同业，具备相对防守性价比。"
        else:
            rank_tier = "同业深度折价梯队 (<15% 极低分位)"
            rank_desc = f"在同业 {peer_total} 家公司中位列第 {peer_rank} 名，处于行业最低估值带，需警惕周期性行业下行或单季亏损导致的价值陷阱。"

    # 3. Status Classification Based on Relative Premium & Multiples (No Fake Margin of Safety)
    if peer_premium_pct is not None:
        if peer_premium_pct > 100.0:
            status_label = f"显著同业高溢价 (+{peer_premium_pct}%)"
            status_badge = "HIGH_PREMIUM"
            status_color = "red"
        elif peer_premium_pct > 25.0:
            status_label = f"相对同业溢价 (+{peer_premium_pct}%)"
            status_badge = "PREMIUM"
            status_color = "yellow"
        elif peer_premium_pct >= -15.0:
            status_label = "贴近同业中位数 (平价合理)"
            status_badge = "FAIR"
            status_color = "blue"
        elif peer_premium_pct >= -45.0:
            status_label = f"相对同业折价 ({peer_premium_pct}%)"
            status_badge = "DISCOUNT"
            status_color = "green"
        else:
            status_label = f"大幅同业折价 ({peer_premium_pct}%)"
            status_badge = "DEEP_DISCOUNT"
            status_color = "green"
    elif metric_val is not None and metric_val > 0:
        status_label = f"绝对估值 {ind_label} {metric_val:.1f}x"
        status_badge = "RECORDED"
        status_color = "blue"
    else:
        status_label = "估值指标未取得或为负"
        status_badge = "UNAVAILABLE"
        status_color = "gray"

    return {
        "status": status_label,
        "status_badge": status_badge,
        "status_color": status_color,
        "current_price": price,
        "has_dcf_corridor": False,
        "margin_of_safety_pct": None,  # 严肃买方原则：缺少真实多期现金流，绝不编造公允价与安全边际
        "dcf_disclaimer": "长桥基础接口未返回多期现金流量表（缺少经营现金流与 Capex），系统杜绝通过市盈率倒数编造自由现金流(FCF)与绝对公允价走廊，以确保研究结论的严肃性。",
        "historical_percentile_disclaimer": "系统未接入连续 3~5 年历史日频估值序列；已停用横向同业排位倒数冒充历史分位的虚构逻辑。",
        "multiples": {
            "indicator": ind_label,
            "metric_value": metric_val,
            "pe_raw": pe_raw,
            "ps_raw": ps_raw,
            "pb_raw": pb_raw,
            "dividend_yield": dividend_yield,
            "industry_median": industry_median,
            "peer_premium_pct": peer_premium_pct,
            "peer_rank": peer_rank,
            "peer_total": peer_total,
            "rank_ratio_pct": rank_ratio_pct,
            "rank_tier": rank_tier,
            "rank_desc": rank_desc,
        },
        "trade_zones": None,  # 废除基于假公允价值算出的买入区间
        "sensitivity_table": None,  # 废除基于假 FCF 的二维折现表
    }
