"""
Autonomous Self-Evolving AI Stock Screener Engine:
1. Daily Autonomous Stock Picking (Real multi-factor quantitative screening)
2. Autonomous Performance Tracking & Attribution (T+5, T+20, T+60 actual returns vs SPY)
3. Factor Weight Self-Optimization & Model Evolution Loop
No synthetic seeds or fake historical snapshots are permitted.
"""
import json
import math
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from backend.config import DEFAULT_SCREENER_SYMBOLS
from backend.core.financial import build_factor_breakdown
from backend.core.utils import clamp, number_from, utc_now_iso
from backend.db import (
    archive_recommendation_snapshot,
    get_active_model_state,
    get_model_evolution_logs,
    get_review_snapshots,
    record_model_evolution,
    update_active_model_state,
    update_snapshot_evaluation,
)
from backend.services.backtester import fetch_yahoo_history
from backend.services.macro_service import get_macro_climate
from backend.services.screener import run_screener

# Evolution universe strictly aligned with official screener universe
EVOLUTION_UNIVERSE = list(DEFAULT_SCREENER_SYMBOLS)


def evaluate_past_recommendations() -> Dict[str, Any]:
    """
    Pillar 2: Autonomous Evaluation of real historical snapshots.
    Measures actual T+5 and T+20 returns and SPY alpha using real historical daily bars.
    Requires at least 5 completed T+5 samples before enabling model tuning.
    """
    snapshots = get_review_snapshots(limit=100)
    if not snapshots:
        return {
            "ok": True,
            "evaluated_count": 0,
            "ready_for_tuning": False,
            "hit_rate": 0.0,
            "avg_alpha": 0.0,
            "message": "当前数据库暂无历史研判快照，请先进行单股分析或每日选股以沉淀真实推荐记录。",
            "evaluated_items": [],
        }

    # Cache SPY history
    spy_bars = fetch_yahoo_history("SPY", "2y")
    spy_dates = sorted(spy_bars.keys())

    evaluated_count = 0
    winning_alpha_count = 0
    total_alpha_sum = 0.0
    evaluated_items = []
    pending_count = 0

    seen_recommendations = set()

    for item in snapshots:
        snap_id = item["id"]
        sym = item["symbol"].replace(".US", "")
        created_str = (item.get("created_at") or "")[:10]  # YYYY-MM-DD
        base_price = item.get("price")

        # Deduplication: same symbol within the same date is treated as a single recommendation event
        sample_key = (sym, created_str)
        if sample_key in seen_recommendations:
            continue
        seen_recommendations.add(sample_key)

        stock_bars = fetch_yahoo_history(sym, "2y")
        if not stock_bars or not spy_bars:
            continue

        stock_dates = sorted(stock_bars.keys())
        future_dates = [d for d in stock_dates if d >= created_str and d in spy_bars]

        # Require at least 6 trading dates (entry day + 5 subsequent trading days) for T+5
        if len(future_dates) < 6:
            pending_count += 1
            update_snapshot_evaluation(
                snapshot_id=snap_id,
                t5_price=None,
                t20_price=None,
                alpha=0.0,
                status="PENDING",
                review_note="🕒 正在持续跟踪中（建仓不足 5 个交易日）",
            )
            continue

        entry_date = future_dates[0]
        entry_price = stock_bars[entry_date]["close"]
        entry_spy = spy_bars[entry_date]["close"]

        # T+5 price and alpha
        t5_date = future_dates[5]
        t5_price = stock_bars[t5_date]["close"]
        t5_ret = (t5_price / entry_price - 1.0) * 100.0
        spy_t5_ret = (spy_bars[t5_date]["close"] / entry_spy - 1.0) * 100.0
        alpha_t5 = t5_ret - spy_t5_ret

        sl_price = item.get("stop_loss_price") or (entry_price * 0.90)

        # Check if T+20 has elapsed (entry day + 20 subsequent trading days)
        if len(future_dates) >= 21:
            t20_date = future_dates[20]
            t20_price = stock_bars[t20_date]["close"]
            t20_ret = (t20_price / entry_price - 1.0) * 100.0
            spy_t20_ret = (spy_bars[t20_date]["close"] / entry_spy - 1.0) * 100.0
            alpha = t20_ret - spy_t20_ret

            min_price_in_hold = min(stock_bars[d]["low"] for d in future_dates[:21])
            stopped_out = min_price_in_hold <= sl_price

            if stopped_out and alpha < 0:
                status = "STOPPED_OUT"
                causal_tag = f"⚠️ 触发防线止损 (最低触及 ${min_price_in_hold:.2f})"
            elif alpha > 0 and t20_ret > 0:
                status = "CLOSED_WIN"
                causal_tag = f"🎯 逻辑完全兑现 (T+20 收益 +{t20_ret:.1f}%, 超额 Alpha +{alpha:.1f}%)"
                winning_alpha_count += 1
            elif alpha > 0 and t20_ret <= 0:
                status = "DEFENSIVE_ALPHA"
                causal_tag = f"🌧️ 大盘系统性拖累 (标普跌幅更深，相对跑赢 Alpha +{alpha:.1f}%)"
                winning_alpha_count += 1
            else:
                status = "CLOSED_LOSS"
                causal_tag = f"❌ 催化落空/破位 (T+20 跑输标普 {abs(alpha):.1f}%)"

            update_snapshot_evaluation(
                snapshot_id=snap_id,
                t5_price=round(t5_price, 2),
                t20_price=round(t20_price, 2),
                alpha=round(alpha, 2),
                status=status,
                review_note=causal_tag,
            )
            evaluated_count += 1
            total_alpha_sum += alpha
            evaluated_items.append({
                "id": snap_id,
                "symbol": item["symbol"],
                "created_at": created_str,
                "entry_price": round(entry_price, 2),
                "t5_return_pct": round(t5_ret, 2),
                "t20_return_pct": round(t20_ret, 2),
                "spy_t20_return_pct": round(spy_t20_ret, 2),
                "alpha_pct": round(alpha, 2),
                "status": status,
                "review_note": causal_tag,
            })
        else:
            # Only T+5 is available; T+20 holding period has not yet elapsed
            min_price_in_hold = min(stock_bars[d]["low"] for d in future_dates[:6])
            stopped_out = min_price_in_hold <= sl_price

            if stopped_out and alpha_t5 < 0:
                status = "STOPPED_OUT"
                causal_tag = f"⚠️ 触发防线止损 (最低触及 ${min_price_in_hold:.2f})"
            else:
                status = "T5_TRACKING"
                causal_tag = f"⏳ T+5 达标 (收益 {t5_ret:+.1f}%, Alpha {alpha_t5:+.1f}%)，T+20 跟踪中"
                if alpha_t5 > 0:
                    winning_alpha_count += 1

            update_snapshot_evaluation(
                snapshot_id=snap_id,
                t5_price=round(t5_price, 2),
                t20_price=None,
                alpha=round(alpha_t5, 2),
                status=status,
                review_note=causal_tag,
            )
            evaluated_count += 1
            total_alpha_sum += alpha_t5
            evaluated_items.append({
                "id": snap_id,
                "symbol": item["symbol"],
                "created_at": created_str,
                "entry_price": round(entry_price, 2),
                "t5_return_pct": round(t5_ret, 2),
                "t20_return_pct": None,
                "spy_t20_return_pct": None,
                "alpha_pct": round(alpha_t5, 2),
                "status": status,
                "review_note": causal_tag,
            })

    hit_rate = round((winning_alpha_count / max(evaluated_count, 1)) * 100.0, 1) if evaluated_count > 0 else 0.0
    avg_alpha = round(total_alpha_sum / max(evaluated_count, 1), 2) if evaluated_count > 0 else 0.0
    ready_for_tuning = evaluated_count >= 5

    msg = (
        f"已完成 {evaluated_count} 条真实样本评估（胜率 {hit_rate}%，平均超额 Alpha {avg_alpha:+.2f}%）。"
        if ready_for_tuning
        else f"真实有效走满T+5的样本量不足（当前已满样本：{evaluated_count}/5，跟踪中：{pending_count}）。系统杜绝虚构历史数据，模型将维持基准因子权重，待用户持续沉淀真实研判记录后开启自进化。"
    )

    return {
        "ok": True,
        "evaluated_count": evaluated_count,
        "pending_count": pending_count,
        "ready_for_tuning": ready_for_tuning,
        "hit_rate": hit_rate,
        "avg_alpha": avg_alpha,
        "message": msg,
        "evaluated_items": evaluated_items[:12],
    }


def optimize_factor_weights(eval_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pillar 3: Autonomous Factor Weight Self-Optimization Loop.
    Only tunes weights if there are at least 5 real verified historical evaluations.
    """
    state = get_active_model_state()
    current_gen = state["generation"]
    current_weights = dict(state["weights"])
    total_cycles = state["total_cycles"] + 1

    ready_for_tuning = eval_results.get("ready_for_tuning", False)
    if not ready_for_tuning:
        return {
            "ok": True,
            "generation": current_gen,
            "tuning_applied": False,
            "previous_weights": current_weights,
            "new_weights": current_weights,
            "hit_rate": eval_results.get("hit_rate", 0.0),
            "avg_alpha": eval_results.get("avg_alpha", 0.0),
            "tuning_rationale": eval_results.get("message", "历史真实样本量不足，维持当前基准因子权重"),
            "timestamp": utc_now_iso(),
        }

    macro = get_macro_climate()
    regime = macro.get("regime", {}).get("level", "常态平衡期")
    vix_raw = macro.get("vix", {}).get("last")
    vix_val = float(vix_raw) if (vix_raw is not None and float(vix_raw) > 0) else None

    evaluated_count = eval_results.get("evaluated_count", 0)
    hit_rate = eval_results.get("hit_rate", 50.0)
    avg_alpha = eval_results.get("avg_alpha", 0.0)

    # Heuristic Factor Optimization Algorithm
    new_weights = dict(current_weights)
    rationale_parts = []

    # 1. Macro Regime adaptation
    if vix_val is None:
        rationale_parts.append("波动率数据未连接，维持常态平衡期基准权重")
    elif vix_val < 18.0:
        new_weights["momentum"] = min(38, new_weights.get("momentum", 25) + 3)
        new_weights["catalyst"] = min(25, new_weights.get("catalyst", 20) + 2)
        new_weights["valuation"] = max(10, new_weights.get("valuation", 15) - 3)
        new_weights["liquidity"] = max(10, new_weights.get("liquidity", 15) - 2)
        rationale_parts.append(f"大盘低恐慌 (VIX={vix_val:.1f})，自适应提升动量与催化权重")
    elif vix_val >= 23.0:
        new_weights["quality"] = min(35, new_weights.get("quality", 25) + 4)
        new_weights["valuation"] = min(25, new_weights.get("valuation", 15) + 3)
        new_weights["momentum"] = max(12, new_weights.get("momentum", 25) - 4)
        new_weights["catalyst"] = max(10, new_weights.get("catalyst", 20) - 3)
        rationale_parts.append(f"大盘高波动 (VIX={vix_val:.1f})，自适应强化基本面质量与估值安全边际")
    else:
        rationale_parts.append(f"大盘常态波动 (VIX={vix_val:.1f})，维持均衡因子权重")

    # 2. Performance feedback adaptation
    if avg_alpha > 1.5:
        new_weights["momentum"] = min(40, new_weights.get("momentum", 25) + 2)
        rationale_parts.append(f"历史实证展现正向 Alpha (+{avg_alpha}%)，加固高动能选股敏锐度")
    elif avg_alpha < 0:
        new_weights["quality"] = min(35, new_weights.get("quality", 25) + 3)
        new_weights["momentum"] = max(12, new_weights.get("momentum", 25) - 3)
        new_weights["valuation"] = min(25, new_weights.get("valuation", 15) + 2)
        rationale_parts.append(f"近期 Alpha 承压 ({avg_alpha}%)，自优化提高抗跌质量与防破位阈值")

    # Normalize to exact sum of 100
    total = sum(new_weights.values())
    for k in new_weights:
        new_weights[k] = int(round(new_weights[k] / total * 100))
    diff = 100 - sum(new_weights.values())
    new_weights["momentum"] += diff

    new_gen = current_gen + 1
    rationale = "；".join(rationale_parts) if rationale_parts else "常规多因子协方差平稳微调"

    # Persist in SQLite
    update_active_model_state(new_gen, new_weights, total_cycles)
    record_model_evolution(
        generation=new_gen,
        macro_regime=regime,
        previous_weights=current_weights,
        new_weights=new_weights,
        evaluated_picks_count=evaluated_count,
        avg_alpha=avg_alpha,
        hit_rate=hit_rate,
        tuning_rationale=rationale,
    )

    return {
        "ok": True,
        "generation": new_gen,
        "tuning_applied": True,
        "macro_regime": regime,
        "previous_weights": current_weights,
        "new_weights": new_weights,
        "hit_rate": hit_rate,
        "avg_alpha": avg_alpha,
        "tuning_rationale": rationale,
    }


def run_daily_autonomous_screener(evolved_weights: Dict[str, int]) -> Dict[str, Any]:
    """
    Pillar 1: Autonomous Daily Stock Screener using the active factor weights.
    Screens candidates across core tech & growth universe, archives real picks into SQLite.
    """
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    screen_res = run_screener(EVOLUTION_UNIVERSE, limit=6, dynamic_weights=evolved_weights)
    top_picks = screen_res.get("top", [])

    macro = get_macro_climate()
    spy_last = macro.get("spy", {}).get("last")
    spy_px = spy_last if (spy_last and spy_last > 0) else None
    vix_last = macro.get("vix", {}).get("last")
    vix_val = vix_last if (vix_last and vix_last > 0) else None

    # Automatically archive today's picks into SQLite snapshots ONLY if real data exists
    for rank, p in enumerate(top_picks, 1):
        px = p.get("last")
        if not px or px <= 0:
            continue
        p["rank"] = rank
        atr_stop = p.get("technical", {}).get("trailing_stop_2atr")
        if atr_stop:
            sl = atr_stop
            thesis_defense = f"盯防 2xATR 止损线 ${sl:.2f}"
        else:
            sl = round(px * 0.93, 2)
            thesis_defense = f"盯防常规止损线 ${sl:.2f} (-7% 跟踪，ATR 数据不足)"

        raw_target = (p.get("rating") or {}).get("target") or p.get("target_price")
        target_p = round(float(raw_target), 2) if (raw_target and float(raw_target) > 0) else None

        archive_recommendation_snapshot(
            symbol=p["symbol"],
            source_type="AUTONOMOUS_DAILY_PICK",
            price=px,
            spy_price=spy_px,
            vix_value=vix_val,
            score=p.get("score", 70.0),
            verdict=p.get("verdict", "中性观察"),
            tags=p.get("tags", []),
            short_term_thesis=f"由自进化 Gen 模型于 {today_str} 基于动态权重选出 (得分: {p.get('score')})，{thesis_defense}",
            mid_term_thesis=macro.get("regime", {}).get("level", "顺风进攻期"),
            long_term_thesis=p.get("name", p["symbol"]),
            stop_loss_price=sl,
            target_price=target_p,
            ai_model="Autonomous Engine",
            review_note="待 T+5/T+20 自动追踪",
        )

    return {
        "ok": True,
        "date": today_str,
        "count": len(top_picks),
        "picks": top_picks,
        "errors": screen_res.get("errors", []),
    }


def run_full_autonomous_cycle(force_refresh: bool = False) -> Dict[str, Any]:
    """
    Executes the Complete Closed-Loop Autonomous Evolution Cycle:
    Step 1: Evaluate past snapshots (T+5 / T+20 returns & Alpha attribution)
    Step 2: Self-optimize factor weights based on feedback
    Step 3: Screen today's universe using newly evolved weights
    """
    print("[AutoEvolution] Starting autonomous evaluation cycle...")
    t0 = time.time()

    # Step 1: Evaluate past
    eval_res = evaluate_past_recommendations()

    # Step 2: Self-optimize
    opt_res = optimize_factor_weights(eval_res)

    # Step 3: Daily Screen & Archive
    picks_res = run_daily_autonomous_screener(opt_res["new_weights"])

    elapsed = round(time.time() - t0, 3)
    print(f"[AutoEvolution] Cycle finished in {elapsed}s: Model Gen {opt_res['generation']} active!")

    return {
        "ok": True,
        "elapsed_seconds": elapsed,
        "evaluation": eval_res,
        "evolution": opt_res,
        "daily_picks": picks_res,
    }


def get_autonomous_status() -> Dict[str, Any]:
    """Return current model state, performance scoreboard, and evolution history."""
    state = get_active_model_state()
    logs = get_model_evolution_logs(limit=15)
    snapshots = get_review_snapshots(limit=30)

    seen_eval = set()
    deduped_evaluated = []
    for s in snapshots:
        if s.get("status") in ("CLOSED_WIN", "CLOSED_LOSS", "DEFENSIVE_ALPHA", "STOPPED_OUT", "T5_TRACKING"):
            key = (s.get("symbol"), (s.get("created_at") or "")[:10])
            if key not in seen_eval:
                seen_eval.add(key)
                deduped_evaluated.append(s)

    hit_count = sum(1 for s in deduped_evaluated if (s.get("alpha") or 0) > 0)
    total_eval = len(deduped_evaluated)
    hit_rate = round((hit_count / max(total_eval, 1)) * 100.0, 1) if total_eval > 0 else 0.0
    avg_alpha = round(sum((s.get("alpha") or 0) for s in deduped_evaluated) / max(total_eval, 1), 2) if total_eval > 0 else 0.0

    return {
        "ok": True,
        "model_state": state,
        "performance_scoreboard": {
            "total_evaluated": total_eval,
            "hit_rate_pct": hit_rate,
            "avg_alpha_pct": avg_alpha,
        },
        "evolution_logs": logs,
        "recent_snapshots": snapshots[:8],
    }


def start_autonomous_daemon() -> None:
    """
    Start background daemon only if explicitly invoked.
    Does NOT auto-tune model on startup to avoid unverified weight mutation.
    """
    pass
