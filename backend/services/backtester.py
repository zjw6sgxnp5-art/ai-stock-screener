"""
Backtest Engine Service:
Multi-factor historical replay, discrete macro regime switching,
ATR risk parity simulation, and performance metrics (Sharpe, MDD, Alpha).
"""
import json
import math
import ssl
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.core.utils import utc_now_iso


def fetch_yahoo_history(symbol: str, range_str: str = "2y") -> Dict[str, Dict[str, float]]:
    """
    Fetch daily OHLCV historical series from Yahoo Finance without external dependencies.
    """
    ctx = ssl._create_unverified_context()
    clean_sym = symbol.replace("^", "%5E")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{clean_sym}?interval=1d&range={range_str}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=12)
        payload = json.loads(resp.read().decode("utf-8"))
        result = payload.get("chart", {}).get("result", [])
        if not result:
            return {}
        data = result[0]
        timestamps = data.get("timestamp", [])
        quote = data.get("indicators", {}).get("quote", [{}])[0]
        closes = quote.get("close", [])
        highs = quote.get("high", closes)
        lows = quote.get("low", closes)
        volumes = quote.get("volume", [])

        series = {}
        for ts, c, h, l, v in zip(timestamps, closes, highs, lows, volumes):
            if c is not None:
                dt_str = datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")
                series[dt_str] = {
                    "close": float(c),
                    "high": float(h if h is not None else c),
                    "low": float(l if l is not None else c),
                    "volume": float(v if v is not None else 0),
                }
        return series
    except Exception as exc:
        print(f"[Backtester] Fetch error for {symbol}: {exc}")
        return {}


def calculate_max_drawdown(equity_series: List[float]) -> float:
    """Calculate maximum drawdown percentage from equity curve."""
    if not equity_series:
        return 0.0
    peak = equity_series[0]
    max_dd = 0.0
    for val in equity_series:
        if val > peak:
            peak = val
        dd = (val - peak) / peak * 100.0
        if dd < max_dd:
            max_dd = dd
    return round(max_dd, 2)


def run_quantitative_backtest(
    symbols: Optional[List[str]] = None,
    benchmark_symbol: str = "SPY",
    range_str: str = "2y",
    initial_capital: float = 100000.0,
    rebalance_freq: int = 15,
    top_n: int = 3,
    max_sector_cap: float = 0.30,
    friction_pct: float = 0.001,
) -> Dict[str, Any]:
    """
    Run multi-factor quantitative backtest strictly using point-in-time sliding windows.
    """
    if not symbols:
        symbols = ["NVDA", "MSFT", "AAPL", "AMZN", "GOOGL", "META", "TSLA", "AMD"]

    # 1. Fetch benchmark, VIX, and candidate histories
    print(f"[Backtester] Downloading historical data for {len(symbols)} candidates + benchmark...")
    spy_data = fetch_yahoo_history(benchmark_symbol, range_str)
    vix_data = fetch_yahoo_history("^VIX", range_str)

    stock_data: Dict[str, Dict[str, Dict[str, float]]] = {}
    for sym in symbols:
        stock_data[sym] = fetch_yahoo_history(sym, range_str)

    # 2. Synchronize trading dates
    common_dates = sorted([d for d in spy_data.keys() if d in vix_data])
    if len(common_dates) < 80:
        return {"ok": False, "error": "历史交易日数据不足，无法完成统计有效性回测。"}

    warmup = 60
    sim_dates = common_dates[warmup:]
    spy_base_price = spy_data[sim_dates[0]]["close"]

    cash = float(initial_capital)
    positions: Dict[str, Dict[str, Any]] = {}
    portfolio_equity: List[float] = []
    benchmark_equity: List[float] = []

    last_rebalance_idx = -999
    trades_count = 0
    winning_trades = 0

    for idx, dt in enumerate(sim_dates):
        # A. Daily Mark-to-Market & Trailing Stop Check
        closed_syms = []
        for sym, pos in list(positions.items()):
            if dt in stock_data[sym]:
                bar = stock_data[sym][dt]
                if bar["high"] > pos["highest_price"]:
                    pos["highest_price"] = bar["high"]
                    trail_stop = pos["highest_price"] - (pos["entry_price"] - pos["initial_stop"])
                    if trail_stop > pos["stop_loss"]:
                        pos["stop_loss"] = trail_stop

                # Trigger Stop Loss
                if bar["low"] <= pos["stop_loss"]:
                    exit_price = pos["stop_loss"]
                    cash += pos["shares"] * exit_price * (1.0 - friction_pct)
                    pnl = (exit_price - pos["entry_price"]) / pos["entry_price"]
                    trades_count += 1
                    if pnl > 0:
                        winning_trades += 1
                    closed_syms.append(sym)

        for sym in closed_syms:
            del positions[sym]

        # B. Rebalance Window
        if (idx - last_rebalance_idx) >= rebalance_freq:
            last_rebalance_idx = idx

            # 1. Macro Regime via VIX
            vix_val = vix_data[dt]["close"]
            if vix_val < 17.5:
                regime = "RISK_ON"
                target_exposure = 0.90
            elif vix_val <= 22.0:
                regime = "NEUTRAL"
                target_exposure = 0.70
            elif vix_val <= 28.0:
                regime = "CAUTION"
                target_exposure = 0.40
            else:
                regime = "PANIC"
                target_exposure = 0.15

            # 2. Point-in-time scoring for candidates
            hist_idx = common_dates.index(dt)
            scores = []
            for sym in symbols:
                if sym not in stock_data or dt not in stock_data[sym]:
                    continue
                past_bars = [stock_data[sym][common_dates[i]] for i in range(hist_idx - 60, hist_idx + 1) if common_dates[i] in stock_data[sym]]
                if len(past_bars) < 40:
                    continue

                closes = [b["close"] for b in past_bars]
                ret20 = (closes[-1] / closes[-20] - 1.0) * 100.0 if len(closes) >= 20 else 0.0
                ret60 = (closes[-1] / closes[0] - 1.0) * 100.0
                spy_closes = [spy_data[common_dates[i]]["close"] for i in range(hist_idx - 20, hist_idx + 1) if common_dates[i] in spy_data]
                spy_ret20 = (spy_closes[-1] / spy_closes[0] - 1.0) * 100.0 if len(spy_closes) >= 20 else 0.0
                rs = ret20 - spy_ret20

                # ATR(14) calculation
                trs = []
                for k in range(1, min(15, len(past_bars))):
                    h, l, pc = past_bars[-k]["high"], past_bars[-k]["low"], past_bars[-k - 1]["close"]
                    trs.append(max(h - l, abs(h - pc), abs(l - pc)))
                atr = sum(trs) / len(trs) if trs else closes[-1] * 0.03

                # Multi-factor formula based on regime
                if regime == "RISK_ON":
                    score = rs * 1.5 + ret60 * 0.5 + (12.0 if closes[-1] > max(closes[-20:]) else 0.0)
                elif regime == "NEUTRAL":
                    score = rs * 1.0 + (10.0 if closes[-1] > (sum(closes[-20:]) / 20.0) else -10.0)
                else:
                    score = -atr / closes[-1] * 100.0 + (10.0 if rs > 0 else -10.0)

                scores.append({"sym": sym, "score": score, "price": closes[-1], "atr": atr})

            scores.sort(key=lambda x: x["score"], reverse=True)
            top_picks = scores[:top_n]
            top_syms = set(x["sym"] for x in top_picks)

            # 3. Buffer Zone: Sell positions falling out of Top N
            for sym in list(positions.keys()):
                if sym not in top_syms and dt in stock_data[sym]:
                    cp = stock_data[sym][dt]["close"]
                    cash += positions[sym]["shares"] * cp * (1.0 - friction_pct)
                    pnl = (cp - positions[sym]["entry_price"]) / positions[sym]["entry_price"]
                    trades_count += 1
                    if pnl > 0:
                        winning_trades += 1
                    del positions[sym]

            # 4. Allocate capital to new Top N picks
            total_equity = cash + sum(pos["shares"] * stock_data[s][dt]["close"] for s, pos in positions.items() if dt in stock_data[s])
            target_alloc_per_stock = min((total_equity * target_exposure) / top_n, total_equity * max_sector_cap)

            for pick in top_picks:
                sym = pick["sym"]
                if sym not in positions:
                    alloc = min(target_alloc_per_stock, cash)
                    shares = math.floor(alloc / pick["price"])
                    if shares > 0:
                        cost = shares * pick["price"] * (1.0 + friction_pct)
                        cash -= cost
                        positions[sym] = {
                            "shares": shares,
                            "entry_price": pick["price"],
                            "highest_price": pick["price"],
                            "initial_stop": round(pick["price"] - 2.5 * pick["atr"], 2),
                            "stop_loss": round(pick["price"] - 2.5 * pick["atr"], 2),
                        }

        # C. End-of-day equity logging
        cur_val = cash + sum(pos["shares"] * stock_data[s][dt]["close"] for s, pos in positions.items() if dt in stock_data[s])
        portfolio_equity.append(round(cur_val, 2))
        benchmark_equity.append(round(initial_capital * (spy_data[dt]["close"] / spy_base_price), 2))

    # 3. Performance Metrics
    total_strat_return = (portfolio_equity[-1] / initial_capital - 1.0) * 100.0
    total_spy_return = (benchmark_equity[-1] / initial_capital - 1.0) * 100.0
    alpha = total_strat_return - total_spy_return

    years = len(sim_dates) / 252.0
    cagr_strat = ((portfolio_equity[-1] / initial_capital) ** (1.0 / max(years, 0.1)) - 1.0) * 100.0
    cagr_spy = ((benchmark_equity[-1] / initial_capital) ** (1.0 / max(years, 0.1)) - 1.0) * 100.0

    daily_rets = [(portfolio_equity[i] / portfolio_equity[i - 1] - 1.0) for i in range(1, len(portfolio_equity))]
    mean_r = (sum(daily_rets) / len(daily_rets)) * 252.0 if daily_rets else 0.0
    vol = math.sqrt(sum((r - mean_r / 252.0) ** 2 for r in daily_rets) / max(len(daily_rets) - 1, 1)) * math.sqrt(252.0)
    sharpe = (mean_r - 0.04) / vol if vol > 0.0 else 0.0

    mdd_strat = calculate_max_drawdown(portfolio_equity)
    mdd_spy = calculate_max_drawdown(benchmark_equity)
    calmar = abs(cagr_strat / mdd_strat) if mdd_strat < 0 else 0.0
    win_rate = (winning_trades / trades_count * 100.0) if trades_count > 0 else 0.0

    return {
        "ok": True,
        "generated_at": utc_now_iso(),
        "period": {
            "start_date": sim_dates[0],
            "end_date": sim_dates[-1],
            "trading_days": len(sim_dates),
            "years": round(years, 2),
        },
        "performance": {
            "strategy_total_return_pct": round(total_strat_return, 2),
            "benchmark_total_return_pct": round(total_spy_return, 2),
            "alpha_pct": round(alpha, 2),
            "strategy_cagr_pct": round(cagr_strat, 2),
            "benchmark_cagr_pct": round(cagr_spy, 2),
            "strategy_max_drawdown_pct": mdd_strat,
            "benchmark_max_drawdown_pct": mdd_spy,
            "annualized_volatility_pct": round(vol * 100.0, 2),
            "sharpe_ratio": round(sharpe, 2),
            "calmar_ratio": round(calmar, 2),
            "total_trades": trades_count,
            "win_rate_pct": round(win_rate, 1),
        },
        "equity_curve": {
            "dates": sim_dates[::5],
            "strategy": portfolio_equity[::5],
            "benchmark": benchmark_equity[::5],
        },
    }


if __name__ == "__main__":
    res = run_quantitative_backtest()
    perf = res.get("performance", {})
    print("=" * 60)
    print("  📊 AI 选股量化回测引擎实测报告 (2024 - 2026)")
    print("=" * 60)
    for k, v in perf.items():
        print(f"  {k:30}: {v}")
    print("=" * 60)
