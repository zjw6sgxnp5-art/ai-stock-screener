"""
Step 5.5 Portfolio Allocation & Risk Parity Engine:
Institutional sector exposure caps (<= 30%), ATR-based risk parity sizing,
and derivative hedging strategies (Protective Put / Covered Call).
"""
import math
from typing import Any, Dict, List, Optional

from backend.core.utils import clamp, number_from, utc_now_iso


# GICS Sector mapping for candidate stocks
STOCK_SECTOR_MAP = {
    "NVDA.US": {"sector": "半导体与半导体设备", "beta": 1.95, "iv_rank": 68},
    "MU.US": {"sector": "半导体与半导体设备", "beta": 1.72, "iv_rank": 74},
    "AMD.US": {"sector": "半导体与半导体设备", "beta": 1.85, "iv_rank": 70},
    "META.US": {"sector": "互动媒体与数字服务", "beta": 1.45, "iv_rank": 58},
    "GOOGL.US": {"sector": "互动媒体与数字服务", "beta": 1.15, "iv_rank": 42},
    "MSFT.US": {"sector": "基础软件与企业级云", "beta": 1.08, "iv_rank": 38},
    "AAPL.US": {"sector": "消费电子与硬件终端", "beta": 0.95, "iv_rank": 32},
    "TSLA.US": {"sector": "新能源整车与自动驾驶", "beta": 2.25, "iv_rank": 82},
    "PDD.US": {"sector": "全球跨境与电商零售", "beta": 1.35, "iv_rank": 64},
    "AMZN.US": {"sector": "电商与云计算基础设施", "beta": 1.22, "iv_rank": 46},
}


def estimate_atr(last_price: float, technical: Optional[Dict[str, Any]] = None) -> float:
    """Estimate 14-day Average True Range (ATR)."""
    if technical and technical.get("volatility_20d"):
        daily_vol = (technical["volatility_20d"] / math.sqrt(252)) / 100.0
        return max(0.5, round(last_price * daily_vol * 1.25, 2))
    return max(0.5, round(last_price * 0.028, 2))


def generate_derivative_hedge(
    symbol: str,
    last_price: float,
    beta: float,
    iv_rank: int,
    catalyst_days: int = 25
) -> Dict[str, Any]:
    """
    Generate spot-derivative hedging recommendation based on beta, IV rank, and upcoming events.
    """
    if beta >= 1.6 or iv_rank >= 65:
        # High Beta / Volatile stock with near-term catalyst -> Recommend Protective Put
        put_strike = round(last_price * 0.94, 1)  # 6% OTM
        est_premium_pct = round(1.8 + (iv_rank / 100.0) * 1.5, 2)
        est_cost_per_share = round(last_price * (est_premium_pct / 100.0), 2)
        return {
            "strategy": "保护性看跌期权 (Protective Put)",
            "action": "买入虚值 Put (对冲下行尾部风险)",
            "recommended_strike": put_strike,
            "strike_desc": f"${put_strike:.2f} (现价下浮 6% 虚值)",
            "expiry_window": f"{catalyst_days + 15} 天期 (覆盖近期财报/催化窗口)",
            "est_premium_pct": est_premium_pct,
            "est_cost_per_share": est_cost_per_share,
            "rationale": f"标的 Beta 较高 ({beta:.2f}) 且 IV 处于较高分位数 ({iv_rank}%)，建议在建仓同时配置 6% OTM 保护性看跌期权，将单票极端回撤封顶在 6% + 权利金成本。"
        }
    else:
        # Stable / Lower Beta Cash-cow stock -> Recommend Covered Call
        call_strike = round(last_price * 1.08, 1)  # 8% OTM
        est_income_pct = round(1.2 + (iv_rank / 100.0) * 0.8, 2)
        est_income_per_share = round(last_price * (est_income_pct / 100.0), 2)
        return {
            "strategy": "备兑看涨期权 (Covered Call)",
            "action": "持有现货并卖出虚值 Call (增强收益与安全垫)",
            "recommended_strike": call_strike,
            "strike_desc": f"${call_strike:.2f} (现价上浮 8% 虚值)",
            "expiry_window": "30-45 天期滚动卖出",
            "est_premium_pct": est_income_pct,
            "est_income_per_share": est_income_per_share,
            "rationale": f"标的具备稳健基本面与相对适中波动 (Beta {beta:.2f})，可卖出 8% OTM 备兑 Call，单周期增厚约 {est_income_pct}% 确定性现金流以平抑持仓成本。"
        }


def calculate_portfolio_allocation(
    candidates: List[Dict[str, Any]],
    total_capital: float = 100000.0,
    risk_per_trade_pct: float = 1.5,
    max_sector_exposure_pct: float = 30.0,
    max_single_stock_pct: float = 25.0,
    macro_exposure_limit_pct: float = 80.0,
) -> Dict[str, Any]:
    """
    Step 5.5 Portfolio allocation with hard sector caps (<=30%) and ATR-based risk parity.
    """
    total_capital = max(10000.0, float(total_capital))
    risk_budget_per_trade = total_capital * (risk_per_trade_pct / 100.0)
    target_deployable_capital = total_capital * (macro_exposure_limit_pct / 100.0)

    allocations: List[Dict[str, Any]] = []
    sector_exposure_tracker: Dict[str, float] = {}  # sector -> total capital allocated
    total_invested = 0.0

    for item in candidates:
        symbol = item.get("symbol", "")
        last_price = float(item.get("last", 100.0))
        if last_price <= 0:
            continue

        meta = STOCK_SECTOR_MAP.get(symbol, {"sector": "科技综合创新", "beta": 1.25, "iv_rank": 50})
        sector = meta["sector"]
        beta = meta["beta"]
        iv_rank = meta["iv_rank"]

        # Calculate ATR and stop loss
        atr = estimate_atr(last_price, item.get("technical"))
        stop_distance = round(atr * 2.0, 2)
        stop_price = max(0.5, round(last_price - stop_distance, 2))
        stop_loss_pct = round((stop_distance / last_price) * 100, 2)

        # Risk Parity: shares = risk_budget / (2 * ATR)
        raw_shares = math.floor(risk_budget_per_trade / stop_distance) if stop_distance > 0 else 0
        raw_capital = raw_shares * last_price

        # Single stock cap check
        max_allowed_for_stock = total_capital * (max_single_stock_pct / 100.0)
        capped_capital = min(raw_capital, max_allowed_for_stock)

        # Sector exposure cap check (Hard limit <= 30%)
        current_sector_allocated = sector_exposure_tracker.get(sector, 0.0)
        max_allowed_for_sector = total_capital * (max_sector_exposure_pct / 100.0)
        remaining_sector_capacity = max(0.0, max_allowed_for_sector - current_sector_allocated)

        sector_constraint_triggered = False
        if capped_capital > remaining_sector_capacity:
            sector_constraint_triggered = True
            final_capital = remaining_sector_capacity
        else:
            final_capital = capped_capital

        # Macro budget ceiling check
        if total_invested + final_capital > target_deployable_capital:
            final_capital = max(0.0, target_deployable_capital - total_invested)

        final_shares = math.floor(final_capital / last_price) if last_price > 0 else 0
        actual_invested = round(final_shares * last_price, 2)

        if actual_invested > 0:
            sector_exposure_tracker[sector] = current_sector_allocated + actual_invested
            total_invested += actual_invested

        # Generate spot-derivative hedging plan
        hedge_plan = generate_derivative_hedge(symbol, last_price, beta, iv_rank)

        allocations.append({
            "symbol": symbol,
            "name": item.get("name", symbol),
            "last": last_price,
            "sector": sector,
            "beta": beta,
            "atr_14": atr,
            "stop_loss_price": stop_price,
            "stop_loss_pct": stop_loss_pct,
            "stop_distance": stop_distance,
            "shares": final_shares,
            "invested_amount": actual_invested,
            "portfolio_weight_pct": round((actual_invested / total_capital) * 100, 2),
            "sector_cap_triggered": sector_constraint_triggered,
            "max_dollar_risk": round(final_shares * stop_distance, 2),
            "derivative_hedge": hedge_plan,
        })

    # Sector summary
    sector_summary = []
    for sec_name, sec_amt in sector_exposure_tracker.items():
        weight = round((sec_amt / total_capital) * 100, 2)
        sector_summary.append({
            "sector": sec_name,
            "amount": round(sec_amt, 2),
            "weight_pct": weight,
            "is_capped": weight >= (max_sector_exposure_pct - 0.5),
            "cap_limit_pct": max_sector_exposure_pct
        })
    sector_summary.sort(key=lambda x: x["amount"], reverse=True)

    cash_reserve = round(max(0.0, total_capital - total_invested), 2)
    cash_pct = round((cash_reserve / total_capital) * 100, 2)
    total_exposure_pct = round((total_invested / total_capital) * 100, 2)

    return {
        "generated_at": utc_now_iso(),
        "total_capital": total_capital,
        "total_invested": round(total_invested, 2),
        "total_exposure_pct": total_exposure_pct,
        "cash_reserve": cash_reserve,
        "cash_pct": cash_pct,
        "target_exposure_pct": macro_exposure_limit_pct,
        "risk_per_trade_pct": risk_per_trade_pct,
        "max_sector_exposure_pct": max_sector_exposure_pct,
        "max_single_stock_pct": max_single_stock_pct,
        "allocations": allocations,
        "sectors": sector_summary,
        "risk_summary": {
            "max_portfolio_drawdown_risk_pct": round(sum(a["max_dollar_risk"] for a in allocations) / total_capital * 100, 2),
            "diversification_status": "良好 (行业硬上限 30% 已受约束)" if len(sector_summary) >= 3 else "集中度中等，建议补充跨行业标的",
            "hedging_coverage_pct": 100.0 if allocations else 0.0,
        }
    }
