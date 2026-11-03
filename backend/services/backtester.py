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

from backend.config import (
    ATR_PERIOD,
    ATR_STOP_MULTIPLIER,
    BACKTEST_COST_BPS,
    BACKTEST_SLIPPAGE_BPS,
    DEFAULT_BACKTEST_UNIVERSE,
    SENSITIVITY_IS_FRACTION,
)
from backend.core.indicators import average_true_range
from backend.core.utils import utc_now_iso
from backend.db import get_cache, set_cache


def calmar_ratio(cagr_pct: float, max_drawdown_pct: float) -> float:
    """Calmar = CAGR / |MaxDrawdown|. Sign follows CAGR; 0.0 when there is no drawdown."""
    if not max_drawdown_pct or max_drawdown_pct >= 0:
        return 0.0
    return cagr_pct / abs(max_drawdown_pct)


def wilder_atr_from_bars(bars: List[Dict[str, float]], period: int = ATR_PERIOD) -> Optional[float]:
    """Wilder-smoothed ATR, same implementation as live technicals (core.indicators.average_true_range)."""
    if len(bars) < period + 1:
        return None
    val = average_true_range([b["high"] for b in bars], [b["low"] for b in bars], [b["close"] for b in bars], period)
    return float(val) if val else None


def survivorship_warning(symbols: List[str], is_default_universe: bool) -> Dict[str, Any]:
    """Structured survivorship-bias warning returned with every backtest (shown by the frontend)."""
    return {
        "has_bias": True,
        "level": "HIGH" if is_default_universe else "MEDIUM",
        "universe_size": len(symbols),
        "is_default_universe": is_default_universe,
        "message": (
            "⚠️ 幸存者偏差：回测标的池为【今天】挑选的固定名单（"
            + ("默认 12 只当今大盘龙头" if is_default_universe else f"自定义 {len(symbols)} 只")
            + "），未包含区间内退市、被剔除或大幅下跌的公司，历史收益存在系统性高估。"
            "可通过 symbols 参数或 AI_STOCK_BT_UNIVERSE 环境变量更换标的池。"
        ),
    }


def fetch_yahoo_history(symbol: str, range_str: str = "2y", force_refresh: bool = False) -> Dict[str, Dict[str, float]]:
    """
    Fetch daily OHLCV historical series from Yahoo Finance without external dependencies.
    Caches raw bars in SQLite for 24 hours to accelerate backtest grid parameter exploration.
    """
    clean_sym = symbol.replace("^", "%5E")
    cache_key = f"raw_yahoo:{clean_sym}:{range_str}"
    if not force_refresh:
        cached = get_cache(cache_key)
        if cached is not None and isinstance(cached, dict) and len(cached) > 0:
            return cached

    ctx = ssl._create_unverified_context()
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
        opens = quote.get("open", closes)
        highs = quote.get("high", closes)
        lows = quote.get("low", closes)
        volumes = quote.get("volume", [])

        series = {}
        for ts, o, c, h, l, v in zip(timestamps, opens, closes, highs, lows, volumes):
            if c is not None:
                dt_str = datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")
                series[dt_str] = {
                    "open": float(o if o is not None else c),
                    "close": float(c),
                    "high": float(h if h is not None else c),
                    "low": float(l if l is not None else c),
                    "volume": float(v if v is not None else 0),
                }
        if series:
            set_cache(cache_key, series, 86400)
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
    friction_pct: Optional[float] = None,
    atr_mult: Optional[float] = None,
    force_refresh: bool = False,
    cost_bps: Optional[float] = None,
    slippage_bps: Optional[float] = None,
    window: Optional[tuple] = None,
) -> Dict[str, Any]:
    """
    Run multi-factor quantitative backtest strictly using point-in-time sliding windows.

    Execution model:
      - Signals use data up to and including day-T close; orders fill at day T+1 open.
      - Stops: if a bar's low touches the stop, fill at min(open, stop) (gap-downs fill at the open).
      - Costs: (cost_bps + slippage_bps) per side; `friction_pct` (legacy) overrides both if given.
      - ATR: Wilder ATR(14), identical to live technicals; default multiplier = config.ATR_STOP_MULTIPLIER.
      - window=(start_frac, end_frac) restricts the simulated period (used for in/out-of-sample splits);
        bars before the window are still used as indicator warm-up.
    """
    is_default_universe = not symbols
    if not symbols:
        symbols = list(DEFAULT_BACKTEST_UNIVERSE)
    symbols = [s.upper().replace(".US", "") for s in symbols]
    if atr_mult is None:
        atr_mult = ATR_STOP_MULTIPLIER
    if cost_bps is None:
        cost_bps = BACKTEST_COST_BPS
    if slippage_bps is None:
        slippage_bps = BACKTEST_SLIPPAGE_BPS
    if friction_pct is None:
        friction_pct = (float(cost_bps) + float(slippage_bps)) / 10000.0
    else:
        cost_bps, slippage_bps = friction_pct * 10000.0, 0.0

    win_key = f"{window[0]:.3f}-{window[1]:.3f}" if window else "full"
    cache_key = (
        f"backtest_v3:{range_str}:{benchmark_symbol}:{rebalance_freq}:{top_n}:{atr_mult}:"
        f"{friction_pct:.6f}:{win_key}:{','.join(sorted(symbols))}"
    )
    if not force_refresh:
        cached = get_cache(cache_key)
        if cached is not None:
            return cached

    # 1. Fetch benchmark, VIX, and candidate histories
    print(f"[Backtester] Loading historical data for {len(symbols)} candidates + benchmark...")
    spy_data = fetch_yahoo_history(benchmark_symbol, range_str, force_refresh=force_refresh)
    vix_data = fetch_yahoo_history("^VIX", range_str, force_refresh=force_refresh)

    stock_data: Dict[str, Dict[str, Dict[str, float]]] = {}
    for sym in symbols:
        stock_data[sym] = fetch_yahoo_history(sym, range_str, force_refresh=force_refresh)

    # 2. Synchronize trading dates
    common_dates = sorted([d for d in spy_data.keys() if d in vix_data])
    if len(common_dates) < 80:
        return {"ok": False, "error": "历史交易日数据不足，无法完成统计有效性回测。"}

    warmup = 60
    sim_dates = common_dates[warmup:]
    if window:
        n = len(sim_dates)
        lo, hi = int(n * max(0.0, window[0])), int(n * min(1.0, window[1]))
        sim_dates = sim_dates[lo:hi]
        if len(sim_dates) < 20:
            return {"ok": False, "error": "样本窗口过短，无法回测。"}
    spy_base_price = spy_data[sim_dates[0]]["close"]

    cash = float(initial_capital)
    positions: Dict[str, Dict[str, Any]] = {}
    portfolio_equity: List[float] = []
    benchmark_equity: List[float] = []

    last_rebalance_idx = -999
    trades_count = 0
    winning_trades = 0
    pending_rebalance: Optional[Dict[str, Any]] = None
    trade_log: List[Dict[str, Any]] = []

    for idx, dt in enumerate(sim_dates):
        # A. Execute Pending Orders from Previous Day's Rebalance Signal (Next-Day Open Execution - No Lookahead Bias)
        if pending_rebalance:
            # 1. Execute sells at Open
            for sym in pending_rebalance.get("sells", []):
                if sym in positions and dt in stock_data[sym]:
                    bar = stock_data[sym][dt]
                    open_p = bar.get("open", bar["close"])
                    cash += positions[sym]["shares"] * open_p * (1.0 - friction_pct)
                    pnl = (open_p - positions[sym]["entry_price"]) / positions[sym]["entry_price"]
                    trade_log.append({"date": dt, "symbol": sym, "side": "SELL", "price": round(open_p, 4),
                                      "reason": "rebalance", "signal_date": pending_rebalance.get("signal_date"),
                                      "pnl_pct": round(pnl * 100, 2)})
                    trades_count += 1
                    if pnl > 0:
                        winning_trades += 1
                    del positions[sym]

            # 2. Execute buys at Open
            for buy in pending_rebalance.get("buys", []):
                sym = buy["sym"]
                if sym not in positions and dt in stock_data[sym]:
                    bar = stock_data[sym][dt]
                    open_p = bar.get("open", bar["close"])
                    if open_p > 0:
                        alloc = min(buy["alloc"], cash)
                        shares = math.floor(alloc / open_p)
                        if shares > 0:
                            cost = shares * open_p * (1.0 + friction_pct)
                            cash -= cost
                            atr_val = buy.get("atr") or (open_p * 0.03)
                            init_stop = round(open_p - atr_mult * atr_val, 2)
                            trade_log.append({"date": dt, "symbol": sym, "side": "BUY", "price": round(open_p, 4),
                                              "reason": "rebalance", "signal_date": pending_rebalance.get("signal_date"),
                                              "stop": init_stop})
                            positions[sym] = {
                                "shares": shares,
                                "entry_price": open_p,
                                "highest_price": max(open_p, bar.get("high", open_p)),
                                "initial_stop": init_stop,
                                "stop_loss": init_stop,
                                "atr": atr_val,
                            }
            pending_rebalance = None

        # B. Intraday Mark-to-Market & Trailing Stop Check (Realistic Gap-Down Slippage)
        closed_syms = []
        for sym, pos in list(positions.items()):
            if dt in stock_data[sym]:
                bar = stock_data[sym][dt]
                if bar["high"] > pos["highest_price"]:
                    pos["highest_price"] = bar["high"]
                    gain = (pos["highest_price"] - pos["entry_price"]) / pos["entry_price"]
                    # 1. Breakeven profit lock (Gain >= 10% -> stop to cost + 1% fee cushion)
                    if gain >= 0.10:
                        be_stop = pos["entry_price"] * 1.01
                        if be_stop > pos["stop_loss"]:
                            pos["stop_loss"] = be_stop
                    # 2. Dynamic trailing profit lock (Gain >= 20% -> trail by atr_mult * ATR)
                    if gain >= 0.20:
                        trail_stop = pos["highest_price"] - (atr_mult * pos["atr"])
                        if trail_stop > pos["stop_loss"]:
                            pos["stop_loss"] = trail_stop

                # Trigger Stop Loss: if low <= stop_loss, exit at min(stop_loss, open) to penalize gap downs
                if bar["low"] <= pos["stop_loss"]:
                    open_p = bar.get("open", bar["close"])
                    # If opened below stop loss (gap-down), fill at open price instead of fictitious stop level
                    exit_price = min(pos["stop_loss"], open_p)
                    cash += pos["shares"] * exit_price * (1.0 - friction_pct)
                    pnl = (exit_price - pos["entry_price"]) / pos["entry_price"]
                    trade_log.append({"date": dt, "symbol": sym, "side": "SELL", "price": round(exit_price, 4),
                                      "reason": "stop_gap" if open_p < pos["stop_loss"] else "stop",
                                      "stop": round(pos["stop_loss"], 4), "pnl_pct": round(pnl * 100, 2)})
                    trades_count += 1
                    if pnl > 0:
                        winning_trades += 1
                    closed_syms.append(sym)

        for sym in closed_syms:
            if sym in positions:
                del positions[sym]

        # C. Rebalance Window at End-of-Day (Signals generated for next trading day)
        if (idx - last_rebalance_idx) >= rebalance_freq and idx < len(sim_dates) - 1:
            last_rebalance_idx = idx

            # 1. Macro Regime via VIX (aligned with macro_service)
            vix_val = vix_data[dt]["close"]
            if vix_val < 18.0:
                regime = "LOW_VIX_EXPANSION"
                target_exposure = 0.85
            elif vix_val <= 23.0:
                regime = "MODERATE_VIX_CONSOLIDATION"
                target_exposure = 0.65
            elif vix_val <= 28.0:
                regime = "ELEVATED_VIX_CORRECTION"
                target_exposure = 0.40
            else:
                regime = "EXTREME_VOLATILITY"
                target_exposure = 0.0

            # 2. Point-in-time scoring for candidates at close
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

                ma20 = sum(closes[-20:]) / 20.0
                ma60 = sum(closes[-60:]) / len(closes[-60:])
                
                # Trend Filter: Reject structural downtrends
                if closes[-1] < ma60 * 0.95:
                    continue

                # Wilder ATR(14) — identical to live technicals
                atr = wilder_atr_from_bars(past_bars) or closes[-1] * 0.03

                # Multi-factor score with trend and relative strength
                score = rs * 1.5 + ret60 * 0.8 + (15.0 if closes[-1] > ma20 else -10.0)
                scores.append({"sym": sym, "score": score, "price": closes[-1], "atr": atr})

            scores.sort(key=lambda x: x["score"], reverse=True)
            ranks = {item["sym"]: r for r, item in enumerate(scores, 1)}

            # 3. Hysteresis Buffer: plan sells for next open if rank > 5
            buffer_sell_rank = max(top_n + 2, 5)
            sells_plan = []
            for sym in list(positions.keys()):
                rank = ranks.get(sym, 999)
                if rank > buffer_sell_rank:
                    sells_plan.append(sym)

            # 4. Plan buys for next open
            total_equity = cash + sum(pos["shares"] * stock_data[s][dt]["close"] for s, pos in positions.items() if dt in stock_data[s])
            base_alloc = (total_equity * target_exposure) / top_n
            buys_plan = []

            for r, pick in enumerate(scores[:top_n], 1):
                sym = pick["sym"]
                if sym not in positions and sym not in sells_plan:
                    weight_mult = 1.25 if r == 1 else 1.0
                    target_alloc = min(base_alloc * weight_mult, total_equity * max_sector_cap)
                    buys_plan.append({
                        "sym": sym,
                        "alloc": target_alloc,
                        "atr": pick["atr"],
                    })

            pending_rebalance = {
                "signal_date": dt,
                "sells": sells_plan,
                "buys": buys_plan,
            }

        # D. End-of-day equity logging
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
    calmar = calmar_ratio(cagr_strat, mdd_strat)
    win_rate = (winning_trades / trades_count * 100.0) if trades_count > 0 else 0.0

    sampled_dates = list(sim_dates[::5])
    sampled_strat = list(portfolio_equity[::5])
    sampled_spy = list(benchmark_equity[::5])
    if sampled_dates and sampled_dates[-1] != sim_dates[-1]:
        sampled_dates.append(sim_dates[-1])
        sampled_strat.append(portfolio_equity[-1])
        sampled_spy.append(benchmark_equity[-1])

    equity_curve_list = [
        {
            "date": d,
            "strategy_nav": s,
            "benchmark_nav": b
        }
        for d, s, b in zip(sampled_dates, sampled_strat, sampled_spy)
    ]

    perf_dict = {
        "strategy_total_return_pct": round(total_strat_return, 2),
        "benchmark_total_return_pct": round(total_spy_return, 2),
        "alpha_pct": round(alpha, 2),
        "strategy_cagr_pct": round(cagr_strat, 2),
        "benchmark_cagr_pct": round(cagr_spy, 2),
        "max_drawdown_pct": mdd_strat,
        "strategy_max_drawdown_pct": mdd_strat,
        "benchmark_max_drawdown_pct": mdd_spy,
        "annualized_volatility_pct": round(vol * 100.0, 2),
        "sharpe_ratio": round(sharpe, 2),
        "calmar_ratio": round(calmar, 2),
        "total_trades": trades_count,
        "total_rebalance_events": trades_count,
        "win_rate_pct": round(win_rate, 1),
    }

    backtest_bundle = {
        **perf_dict,
        "period": {
            "start_date": sim_dates[0],
            "end_date": sim_dates[-1],
            "trading_days": len(sim_dates),
            "years": round(years, 2),
        },
        "performance": perf_dict,
        "strategy_type": f"动量相对强弱与 {atr_mult:g}xATR(Wilder {ATR_PERIOD}) 跟踪止损量化轮动 (T 日收盘出信号，T+1 开盘成交)",
        "assumptions": {
            "signal": "T 日收盘",
            "execution": "T+1 开盘价",
            "stop_fill": "min(开盘价, 止损价)",
            "atr": f"Wilder ATR({ATR_PERIOD})",
            "atr_mult": atr_mult,
            "cost_bps_per_side": round(float(cost_bps), 2),
            "slippage_bps_per_side": round(float(slippage_bps), 2),
            "universe": symbols,
            "benchmark": benchmark_symbol,
            "window": list(window) if window else None,
        },
        "survivorship_warning": survivorship_warning(symbols, is_default_universe),
        "disclaimer": "⚠️ 严肃买方准则说明：本历史回测严格采用【次日开盘执行】（杜绝同日收盘未来函数）与【跳空低开滑点成交】（低开跌破止损线以开盘价成交）。固定历史标的池存在幸存者偏差，低胜率与跑输基准反映了动量策略在震荡市频繁止损的摩擦成本，绝不作为实盘收益承诺！",
        "survivorship_disclaimer": survivorship_warning(symbols, is_default_universe)["message"],
        "equity_curve": equity_curve_list,
        "trade_log": trade_log[-200:],
        "raw_equity_curve": {
            "dates": sampled_dates,
            "strategy": sampled_strat,
            "benchmark": sampled_spy,
        }
    }

    result = {
        "ok": True,
        "generated_at": utc_now_iso(),
        "backtest": backtest_bundle,
        **backtest_bundle,
    }
    set_cache(cache_key, result, 7200)
    return result


def _cell_metrics(bt: Dict[str, Any]) -> Dict[str, Any]:
    perf = bt.get("performance", {}) if bt.get("ok") else {}
    strat_ret = perf.get("strategy_total_return_pct", 0.0)
    spy_ret = perf.get("benchmark_total_return_pct", 0.0)
    return {
        "ok": bool(bt.get("ok")),
        "total_return": strat_ret,
        "spy_return_pct": spy_ret,
        "alpha": perf.get("alpha_pct", round(strat_ret - spy_ret, 2)),
        "sharpe": perf.get("sharpe_ratio", 0.0),
        "max_drawdown_pct": perf.get("strategy_max_drawdown_pct", 0.0),
        "win_rate_pct": perf.get("win_rate_pct", 0.0),
        "total_trades": perf.get("total_trades", 0),
        "period": bt.get("period"),
    }


def run_sensitivity_analysis(
    range_str: str = "2y",
    top_n: int = 2,
    frequencies: Optional[List[int]] = None,
    atr_multipliers: Optional[List[float]] = None,
    force_refresh: bool = False,
    symbols: Optional[List[str]] = None,
    is_fraction: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Hyperparameter sensitivity grid with an in-sample / out-of-sample split.

    The simulation window is split chronologically: the first `is_fraction` is IN-SAMPLE (IS) and is the
    only part used to pick the "optimal" combo; the remainder is OUT-OF-SAMPLE (OOS) and is reported for
    every cell so overfitting is visible. Top-level cell metrics are IS metrics; `cell["oos"]` holds OOS.
    """
    if frequencies is None:
        frequencies = [5, 10, 15, 20]
    if atr_multipliers is None:
        atr_multipliers = sorted({ATR_STOP_MULTIPLIER, 2.0, 2.5, 3.0})
    if is_fraction is None:
        is_fraction = SENSITIVITY_IS_FRACTION
    is_fraction = min(max(float(is_fraction), 0.3), 0.9)
    is_window, oos_window = (0.0, is_fraction), (is_fraction, 1.0)

    cache_key = (
        f"sensitivity_v2:{range_str}:{top_n}:{is_fraction:.2f}:{','.join(map(str, frequencies))}:"
        f"{','.join(map(str, atr_multipliers))}:{','.join(sorted(symbols or []))}"
    )
    if not force_refresh:
        cached = get_cache(cache_key)
        if cached is not None:
            return cached

    matrix = []
    best_alpha = {"alpha": -9999.0, "combo": None}
    best_sharpe = {"sharpe": -9999.0, "combo": None}
    min_drawdown = {"max_dd": -9999.0, "combo": None}
    is_period = oos_period = None

    for mult in atr_multipliers:
        row = []
        for freq in frequencies:
            common = dict(symbols=symbols, range_str=range_str, rebalance_freq=freq, top_n=top_n,
                          atr_mult=mult, force_refresh=False)
            ins = _cell_metrics(run_quantitative_backtest(window=is_window, **common))
            oos = _cell_metrics(run_quantitative_backtest(window=oos_window, **common))
            is_period = is_period or ins.get("period")
            oos_period = oos_period or oos.get("period")
            strat_ret, alpha, sharpe, max_dd = ins["total_return"], ins["alpha"], ins["sharpe"], ins["max_drawdown_pct"]

            cell = {
                "sample": "in_sample",
                "freq": freq,
                "rebal_days": freq,
                "rebalance_freq": freq,
                "atr_mult": mult,
                "atr_multiplier": mult,
                "total_return": strat_ret,
                "strategy_return": strat_ret,
                "strat_return_pct": strat_ret,
                "spy_return_pct": ins["spy_return_pct"],
                "alpha": alpha,
                "alpha_pct": alpha,
                "sharpe": sharpe,
                "sharpe_ratio": sharpe,
                "max_drawdown": abs(max_dd),
                "max_drawdown_pct": max_dd,
                "win_rate_pct": ins["win_rate_pct"],
                "win_rate": ins["win_rate_pct"],
                "total_trades": ins["total_trades"],
                "oos": {k: v for k, v in oos.items() if k != "period"},
            }
            row.append(cell)

            if alpha > best_alpha["alpha"]:
                best_alpha = {"alpha": alpha, "combo": cell}
            if sharpe > best_sharpe["sharpe"]:
                best_sharpe = {"sharpe": sharpe, "combo": cell}
            if min_drawdown["combo"] is None or max_dd > min_drawdown["max_dd"]:
                min_drawdown = {"max_dd": max_dd, "combo": cell}

        matrix.append(row)

    grid = {}
    for r in matrix:
        for cell in r:
            grid[f"{cell['rebal_days']}d_{cell['atr_mult']}x"] = cell

    opt_combo = best_sharpe["combo"] or {}
    optimal_dict = {
        "selected_on": "in_sample",
        "best_alpha": best_alpha["combo"],
        "best_sharpe": best_sharpe["combo"],
        "min_drawdown": min_drawdown["combo"],
        "rebalance_freq": opt_combo.get("freq", 15),
        "atr_multiplier": opt_combo.get("atr_mult", ATR_STOP_MULTIPLIER),
        "freq": opt_combo.get("freq", 15),
        "atr": opt_combo.get("atr_mult", ATR_STOP_MULTIPLIER),
        "in_sample_sharpe": opt_combo.get("sharpe"),
        "out_of_sample": opt_combo.get("oos"),
    }

    sensitivity_bundle = {
        "range": range_str,
        "top_n": top_n,
        "rebalance_freqs": frequencies,
        "frequencies": frequencies,
        "atr_multipliers": atr_multipliers,
        "grid": grid,
        "matrix": matrix,
        "optimal": optimal_dict,
        "optimal_frontier": optimal_dict,
        "sample_split": {
            "in_sample_fraction": is_fraction,
            "in_sample_period": is_period,
            "out_of_sample_period": oos_period,
            "note": "表格数值为样本内(IS)结果，最优参数仅在样本内选出；每格 oos 字段为样本外(OOS)验证。"
                    "IS 好而 OOS 差即为过拟合信号。",
        },
    }

    result = {
        "ok": True,
        "generated_at": utc_now_iso(),
        "sensitivity": sensitivity_bundle,
        **sensitivity_bundle
    }
    set_cache(cache_key, result, 7200)
    return result


if __name__ == "__main__":
    res = run_quantitative_backtest()
    perf = res.get("performance", {})
    print("=" * 60)
    print("  📊 AI 选股量化回测引擎实测报告 (2024 - 2026)")
    print("=" * 60)
    for k, v in perf.items():
        print(f"  {k:30}: {v}")
    print("=" * 60)
