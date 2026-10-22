"""
Stock Screener Service:
Multi-universe scanning (NDX 100 ∪ S&P 500 ∪ Top Volume ∪ Anomalies),
multi-factor evaluation, cross-stock comparison, and daily top-6 recommendations.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

from backend.config import DEFAULT_SCREENER_SYMBOLS, DEFAULT_TIMEOUT, AppError
from backend.core.financial import build_factor_breakdown
from backend.core.indicators import compute_technical_summary
from backend.core.utils import clamp, normalize_symbol, number_from, utc_now_iso
from backend.db import get_active_model_state, get_cache, latest_analysis_payload, list_watchlist, set_cache
from backend.services.macro_service import get_active_factor_config, get_macro_climate
from backend.services.market_data import (
    extract_financials,
    extract_klines,
    extract_news,
    extract_quote,
    extract_rating,
    extract_short_positions,
    extract_valuation,
    fetch_batch_quotes,
    fetch_longbridge_modules,
    run_longbridge,
)


from backend.core.stock_registry import (
    COMPANY_NAMES_ZH,
    get_company_zh_name,
    get_stock_sector,
)
import time
from datetime import datetime, timezone

# Cold start real-time progress tracker
_SCREENER_PROGRESS: Dict[str, Any] = {
    "running": False,
    "total": 0,
    "current": 0,
    "current_symbol": "",
    "updated_at": 0.0,
}


def get_screener_progress() -> Dict[str, Any]:
    """Retrieve current cold-start scanning progress."""
    global _SCREENER_PROGRESS
    return dict(_SCREENER_PROGRESS)


def verdict_for_score(score: Optional[float]) -> str:
    """Map a composite to a label. Missing scores stay unlabeled."""
    if score is None:
        return "数据不足，不能评级"
    if score >= 75:
        return "值得重点研究"
    if score >= 60:
        return "可加入观察"
    return "中性观察"


def _numeric_score(value: Any) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _weakest_factor_text(factor_breakdown: Optional[Dict[str, Any]]) -> str:
    factors = (factor_breakdown or {}).get("factors") or []
    scored = [
        item for item in factors
        if item.get("key") not in ("risk", "catalyst") and _numeric_score(item.get("score")) is not None
    ]
    if not scored:
        return ""
    weakest = min(scored, key=lambda item: _numeric_score(item.get("score")))
    text = f"【{weakest.get('name')}】{_numeric_score(weakest.get('score'))} 分"
    evidence = weakest.get("evidence") or []
    if evidence:
        text += f" ({evidence[0]})"
    return text



def tags_for_candidate(
    technical: Dict[str, Any],
    score: Dict[str, Any],
    valuation: Optional[Dict[str, Any]],
    rating: Optional[Dict[str, Any]],
    news: List[Dict[str, Any]],
) -> List[str]:
    """Generate differentiated highlight opportunity and risk tags."""
    tags: List[str] = []
    ret20 = technical.get("returns", {}).get("20d")
    volume_ratio = technical.get("volume_ratio_20d")
    rsi14 = technical.get("rsi14")
    above_ma20 = technical.get("above_ma20", False)

    # 1. 动量与量能标签
    if ret20 is not None:
        if ret20 >= 10:
            tags.append("强动量")
        elif ret20 <= -10:
            tags.append("弱势整理")
        elif 0 < ret20 < 10 and above_ma20:
            tags.append("稳健上行")
    if volume_ratio is not None and volume_ratio >= 1.5:
        tags.append("放量突破")
    if rsi14 is not None and rsi14 >= 72:
        tags.append("短线过热")

    # 2. 估值标签判定 (支持 PE/PS/PB，彻底杜绝虚假标签)
    if valuation:
        ind = (valuation.get("indicator") or "pe").lower()
        val_num = valuation.get("metric_value") or valuation.get("pe_raw") or valuation.get("ps_raw") or valuation.get("pb_raw")
        peer_premium = valuation.get("peer_premium_pct")
        val_factors = (score.get("factor_breakdown") or {}).get("factors") or []
        val_f = next((f for f in val_factors if f.get("key") == "valuation"), None)
        val_score = val_f.get("score", 50.0) if val_f else 50.0

        if ind == "pe" and val_num is not None and val_num > 0:
            if val_num <= 30 and (peer_premium is None or peer_premium <= 15) and val_score >= 60:
                tags.append("估值不激进")
            elif (peer_premium is not None and peer_premium > 25 and val_num > 35) or val_num >= 60:
                tags.append("相对溢价承压")
            elif val_num <= 20:
                tags.append("估值安全边际")
        elif ind == "ps" and val_num is not None:
            if val_num > 35:
                tags.append("高成长估值承压")
            elif val_num <= 8:
                tags.append("PS估值稳健")
        elif ind == "pb" and val_num is not None:
            if val_num > 10:
                tags.append("高PB溢价")
            elif val_num <= 4:
                tags.append("账面资产安全")

    # 3. 机构与目标价空间标签
    if rating and rating.get("target") and score.get("score"):
        raw_target = number_from(rating.get("target"))
        cur_px = technical.get("last_close") or technical.get("last") or (score.get("last") if isinstance(score, dict) else None)
        if raw_target and cur_px and cur_px > 0 and (raw_target / cur_px - 1) >= 0.15:
            tags.append("目标价空间充裕")
        else:
            tags.append("有机构目标价锚")

    # 4. 财报催化
    news_text = " ".join(item.get("title", "") for item in news[:8]).lower()
    if any(term in news_text for term in ("earnings", "guidance", "财报", "指引", "beat", "revenue")):
        tags.append("财报催化")

    return tags[:4]


def fetch_screener_candidate(
    symbol: str,
    dynamic_weights: Optional[Dict[str, int]] = None,
    risk_multiplier: float = 1.0,
    prefetched_quote: Optional[Dict[str, Any]] = None,
    prefetched_kline: Optional[Dict[str, Any]] = None,
    prefetched_technical: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Fetch and score a candidate symbol for the screener."""
    symbol = normalize_symbol(symbol)
    sym_clean = symbol.replace(".US", "").upper()
    zh_name = COMPANY_NAMES_ZH.get(symbol) or COMPANY_NAMES_ZH.get(sym_clean)

    specs = {
        "news": (["news", symbol, "--count", "20", "--format", "json"], 600),
        "valuation": (["valuation", symbol, "--format", "json"], 21600),
        "rating": (["institution-rating", symbol, "--format", "json"], 21600),
        "financials": (["financial-report", symbol, "--latest", "--format", "json"], 86400),
    }
    if not prefetched_kline:
        specs["kline"] = (["kline", symbol, "--period", "day", "--count", "260", "--format", "json"], 3600)
    if not prefetched_quote:
        specs["quote"] = (["quote", symbol, "--format", "json"], 45)

    try:
        results, errors = fetch_longbridge_modules(specs, timeout=DEFAULT_TIMEOUT)
    except AppError as exc:
        is_busy = exc.status == 429 or "429" in exc.message or "频控" in exc.message or "超时" in exc.message
        return {
            "symbol": symbol,
            "name": zh_name or symbol,
            "last": (prefetched_quote or {}).get("last"),
            "turnover": (prefetched_quote or {}).get("turnover"),
            "volume": (prefetched_quote or {}).get("volume"),
            "fetch_failed": True,
            "status": "BUSY" if is_busy else "ERROR",
            "fail_reason": "接口繁忙 (触发频控)" if is_busy else exc.message,
            "score": None,
            "verdict": "接口繁忙" if is_busy else "取数失败",
            "tags": ["接口繁忙"] if is_busy else ["取数失败"],
            "data_status": "BUSY",
        }
    except Exception as exc:
        return {
            "symbol": symbol,
            "name": zh_name or symbol,
            "last": (prefetched_quote or {}).get("last"),
            "turnover": (prefetched_quote or {}).get("turnover"),
            "volume": (prefetched_quote or {}).get("volume"),
            "fetch_failed": True,
            "status": "ERROR",
            "fail_reason": f"异常: {exc}",
            "score": None,
            "verdict": "取数异常",
            "tags": ["取数异常"],
            "data_status": "ERROR",
        }

    quote = prefetched_quote if prefetched_quote else (extract_quote(results["quote"], symbol) if results.get("quote") else None)
    kline_raw = prefetched_kline if prefetched_kline else results.get("kline")

    if not quote or not kline_raw:
        # Check if rate limited
        is_busy = any("429" in (e.get("message") or "") or "频控" in (e.get("message") or "") or "超时" in (e.get("message") or "") for e in errors)
        existing = latest_analysis_payload(symbol)
        if existing and not is_busy:
            q_exist = existing.get("quote", {})
            tech_exist = existing.get("technical", {})
            news_exist = existing.get("news", [])
            val_exist = existing.get("valuation", {})
            rat_exist = existing.get("rating", {})
            fin_exist = existing.get("financials", {})
            short_exist = existing.get("short_positions") or (existing.get("risk_radar") or {}).get("short_positions")
            risk_bundle = {"controversies": [], "short_positions": short_exist}
            factor_breakdown = build_factor_breakdown(
                q_exist, tech_exist, news_exist, val_exist, rat_exist, fin_exist, risk_bundle,
                regime_weights=dynamic_weights, risk_multiplier=risk_multiplier
            )
            final_score = _numeric_score(factor_breakdown.get("composite"))
            verdict = verdict_for_score(final_score)
            score_dict = {"score": final_score, "verdict": verdict, "factor_breakdown": factor_breakdown}
            tags = tags_for_candidate(tech_exist, score_dict, val_exist, rat_exist, news_exist)
            return {
                "symbol": symbol,
                "name": zh_name or q_exist.get("name") or symbol,
                "last": q_exist.get("last"),
                "change_pct": q_exist.get("change_pct"),
                "volume": q_exist.get("volume"),
                "turnover": q_exist.get("turnover"),
                "score": final_score,
                "verdict": verdict,
                "tags": tags,
                "technical": tech_exist,
                "valuation": val_exist,
                "rating": rat_exist,
                "news_count": len(news_exist),
                "factor_breakdown": factor_breakdown,
                "data_status": "SNAPSHOT",
                "fetch_failed": False,
            }

        return {
            "symbol": symbol,
            "name": zh_name or symbol,
            "last": (quote or {}).get("last"),
            "turnover": (quote or {}).get("turnover"),
            "volume": (quote or {}).get("volume"),
            "fetch_failed": True,
            "status": "BUSY" if is_busy else "ERROR",
            "fail_reason": "接口繁忙 (触发频控)" if is_busy else "基础K线/行情获取失败",
            "score": None,
            "verdict": "接口繁忙" if is_busy else "取数失败",
            "tags": ["接口繁忙"] if is_busy else ["取数失败"],
            "data_status": "BUSY",
        }

    if prefetched_technical:
        technical = prefetched_technical
    else:
        klines = extract_klines(kline_raw)
        technical = compute_technical_summary(klines)
    news = extract_news(results["news"]) if results.get("news") else []
    valuation = extract_valuation(results.get("valuation"))
    rating = extract_rating(results.get("rating"))
    financials = extract_financials(results.get("financials"))
    short_raw = results.get("short_positions")
    short_positions = extract_short_positions(short_raw) if short_raw else None
    risk_bundle = {"controversies": [], "short_positions": short_positions}

    factor_breakdown = build_factor_breakdown(
        quote, technical, news, valuation, rating, financials, risk_bundle,
        regime_weights=dynamic_weights, risk_multiplier=risk_multiplier
    )
    final_score = _numeric_score(factor_breakdown.get("composite"))
    verdict = verdict_for_score(final_score)

    score_dict = {
        "score": final_score,
        "verdict": verdict,
        "factor_breakdown": factor_breakdown,
    }
    tags = tags_for_candidate(technical, score_dict, valuation, rating, news)

    return {
        "symbol": symbol,
        "name": zh_name or quote.get("name") or symbol,
        "last": quote.get("last"),
        "change_pct": quote.get("change_pct"),
        "volume": quote.get("volume"),
        "turnover": quote.get("turnover"),
        "score": final_score,
        "verdict": verdict,
        "tags": tags,
        "technical": technical,
        "valuation": valuation,
        "rating": rating,
        "news_count": len(news),
        "factor_breakdown": factor_breakdown,
        "data_status": "LIVE",
        "fetch_failed": False,
        "liquidity_passed": True,
    }


def run_screener(
    symbols: List[str],
    limit: int = 10,
    dynamic_weights: Optional[Dict[str, int]] = None,
    risk_multiplier: float = 1.0,
    skip_trend_culled_deep_scan: bool = True,
) -> Dict[str, Any]:
    """
    Run phased multi-factor screening across symbols.
    Phase 1: Batch-query live quotes in a single Longbridge CLI call.
    Phase 2: Gate 1 Liquidity filter (turnover >= $300M or volume >= 800k).
             Symbols failing liquidity are culled directly, saving downstream calls.
    Phase 3: Gate 2 Trend filter (above MA20 or 20d return > 0).
             Fetches K-line data for liquidity survivors and computes technical indicators.
             If skip_trend_culled_deep_scan is True, symbols failing trend gate are preserved
             with their technical indicators and marked as trend-culled, bypassing deep factor calls.
    Phase 4: Serialized / paced fetching of remaining factors (valuation, rating, financials, news)
             only for trend survivors (or all survivors if skip_trend_culled_deep_scan is False).
    """
    candidates: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    global _SCREENER_PROGRESS
    _SCREENER_PROGRESS["running"] = True
    _SCREENER_PROGRESS["total"] = len(symbols)
    _SCREENER_PROGRESS["current"] = 0
    _SCREENER_PROGRESS["current_symbol"] = "正在拉取批量基础行情..."
    _SCREENER_PROGRESS["updated_at"] = time.time()

    # Phase 1: 批量拉取所有标的的实时行情 (单次 CLI 调用)
    batch_quotes, quote_errors = fetch_batch_quotes(symbols, timeout=20)

    symbols_to_deep_scan = []
    for s in symbols:
        norm_s = normalize_symbol(s)
        zh_name = COMPANY_NAMES_ZH.get(s) or COMPANY_NAMES_ZH.get(norm_s) or s
        if norm_s in quote_errors:
            err_msg = quote_errors[norm_s]
            is_busy = "429" in err_msg or "频控" in err_msg or "超时" in err_msg
            candidates.append({
                "symbol": norm_s,
                "name": zh_name,
                "last": None,
                "turnover": 0.0,
                "volume": 0,
                "fetch_failed": True,
                "status": "BUSY" if is_busy else "ERROR",
                "fail_reason": "接口繁忙 (触发频控)" if is_busy else err_msg,
                "score": None,
                "verdict": "接口繁忙" if is_busy else "行情失败",
                "tags": ["接口繁忙"] if is_busy else ["行情失败"],
                "data_status": "BUSY",
            })
            errors.append({"symbol": norm_s, "message": err_msg})
            continue

        q = batch_quotes.get(norm_s, {})
        turnover = q.get("turnover") or 0.0
        volume = q.get("volume") or 0

        # Phase 2: 流动性硬规则评估 (单日成交额 ≥ $300M 或成交量 ≥ 80万股)
        is_liquid = (turnover >= 300_000_000 or volume >= 800_000)
        if not is_liquid:
            # 真实因流动性不足淘汰的标的记录下结果，无需耗费 API 请求技术面与财务面
            candidates.append({
                "symbol": norm_s,
                "name": zh_name or q.get("name") or norm_s,
                "last": q.get("last"),
                "change_pct": q.get("change_pct"),
                "volume": volume,
                "turnover": turnover,
                "score": None,
                "verdict": "流动性不足初筛淘汰",
                "tags": ["流动性不足"],
                "technical": {},
                "valuation": None,
                "rating": None,
                "news_count": 0,
                "factor_breakdown": None,
                "data_status": "LIVE",
                "fetch_failed": False,
                "liquidity_passed": False,
                "trend_passed": False,
            })
        else:
            symbols_to_deep_scan.append((norm_s, q))

    # Phase 3: 对通过流动性闸门的标的，并发拉取日K并计算技术面与趋势指标 (线程池并发)
    def _fetch_kline_trend(item):
        norm_s, q = item
        zh_name = COMPANY_NAMES_ZH.get(norm_s) or q.get("name") or norm_s
        turnover = q.get("turnover") or 0.0
        volume = q.get("volume") or 0
        try:
            try:
                kline_res = run_longbridge(
                    ["kline", norm_s, "--period", "day", "--count", "260", "--format", "json"],
                    ttl_seconds=3600,
                )
                klines = extract_klines(kline_res)
            except Exception:
                from backend.services.market_data import fetch_yahoo_klines
                klines = fetch_yahoo_klines(norm_s, count=260)
                kline_res = {"source": "yahoo_finance", "data": klines}

            if not klines:
                raise AppError("无法获取日K线数据", 502)

            technical = compute_technical_summary(klines)
            above_ma20 = technical.get("above_ma20", False)
            ret20 = (technical.get("returns", {}) or {}).get("20d", 0.0)
            is_trend = bool(above_ma20 or ret20 > 0)

            if not is_trend and skip_trend_culled_deep_scan:
                return {
                    "survivor": None,
                    "candidate": {
                        "symbol": norm_s,
                        "name": zh_name,
                        "last": q.get("last"),
                        "change_pct": q.get("change_pct"),
                        "volume": volume,
                        "turnover": turnover,
                        "score": None,
                        "verdict": "跌破20日线初筛淘汰",
                        "tags": ["趋势破位"],
                        "technical": technical,
                        "valuation": None,
                        "rating": None,
                        "news_count": 0,
                        "factor_breakdown": None,
                        "data_status": "LIVE",
                        "fetch_failed": False,
                        "liquidity_passed": True,
                        "trend_passed": False,
                    }
                }
            else:
                return {
                    "survivor": (norm_s, q, kline_res, technical, is_trend),
                    "candidate": None
                }
        except AppError as exc:
            is_busy = exc.status == 429 or "429" in exc.message or "频控" in exc.message or "超时" in exc.message
            return {
                "survivor": None,
                "candidate": {
                    "symbol": norm_s,
                    "name": zh_name,
                    "last": q.get("last"),
                    "turnover": turnover,
                    "volume": volume,
                    "fetch_failed": True,
                    "status": "BUSY" if is_busy else "ERROR",
                    "fail_reason": "接口繁忙 (触发频控)" if is_busy else exc.message,
                    "score": None,
                    "verdict": "接口繁忙" if is_busy else "K线失败",
                    "tags": ["接口繁忙"] if is_busy else ["K线失败"],
                    "data_status": "BUSY",
                },
                "error": {"symbol": norm_s, "message": exc.message}
            }
        except Exception as exc:
            return {
                "survivor": None,
                "candidate": {
                    "symbol": norm_s,
                    "name": zh_name,
                    "last": q.get("last"),
                    "turnover": turnover,
                    "volume": volume,
                    "fetch_failed": True,
                    "status": "ERROR",
                    "fail_reason": f"K线异常: {exc}",
                    "score": None,
                    "verdict": "K线异常",
                    "tags": ["异常"],
                    "data_status": "ERROR",
                },
                "error": {"symbol": norm_s, "message": f"K线获取异常：{exc}"}
            }

    trend_survivors = []
    if symbols_to_deep_scan:
        k_workers = max(1, min(6, len(symbols_to_deep_scan)))
        with ThreadPoolExecutor(max_workers=k_workers) as executor:
            for outcome in executor.map(_fetch_kline_trend, symbols_to_deep_scan):
                if outcome.get("survivor"):
                    trend_survivors.append(outcome["survivor"])
                if outcome.get("candidate"):
                    candidates.append(outcome["candidate"])
                if outcome.get("error"):
                    errors.append(outcome["error"])

    # Phase 4: 对通过趋势闸门的标的，执行多因子（估值、评级、财报、新闻）并发扫描
    worker_count = max(1, min(4, len(trend_survivors)))
    if trend_survivors:
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            trend_map = {sym: is_tr for sym, q, k_res, tech, is_tr in trend_survivors}
            futures = {
                executor.submit(fetch_screener_candidate, sym, dynamic_weights, risk_multiplier, q, k_res, tech): sym
                for sym, q, k_res, tech, is_tr in trend_survivors
            }
            for future in as_completed(futures):
                sym = futures[future]
                is_tr = trend_map.get(sym, True)
                _SCREENER_PROGRESS["current"] = min(_SCREENER_PROGRESS["total"], _SCREENER_PROGRESS["current"] + 1)
                _SCREENER_PROGRESS["current_symbol"] = sym
                _SCREENER_PROGRESS["updated_at"] = time.time()
                try:
                    c = future.result()
                    c["trend_passed"] = is_tr
                    c["liquidity_passed"] = True
                    if not is_tr:
                        sc_val = _numeric_score(c.get("score"))
                        c["verdict"] = "趋势破位 (未评分)" if sc_val is None else f"趋势破位 ({sc_val:.1f}分)"
                        c_tags = c.get("tags") or []
                        if "趋势破位" not in c_tags:
                            c_tags.insert(0, "趋势破位")
                        c["tags"] = c_tags
                    candidates.append(c)
                    if c.get("fetch_failed"):
                        errors.append({"symbol": sym, "message": c.get("fail_reason", "取数失败")})
                except Exception as exc:
                    candidates.append({
                        "symbol": sym,
                        "name": COMPANY_NAMES_ZH.get(sym, sym),
                        "fetch_failed": True,
                        "status": "ERROR",
                        "fail_reason": f"扫描异常: {exc}",
                        "score": None,
                        "verdict": "扫描异常",
                        "tags": ["异常"],
                        "data_status": "ERROR",
                    })
                    errors.append({"symbol": sym, "message": f"筛选异常：{exc}"})

    _SCREENER_PROGRESS["running"] = False
    _SCREENER_PROGRESS["current"] = _SCREENER_PROGRESS["total"]
    _SCREENER_PROGRESS["current_symbol"] = "已完成"
    _SCREENER_PROGRESS["updated_at"] = time.time()

    ranked = sorted(
        candidates,
        key=lambda item: (
            not item.get("fetch_failed", False),
            item.get("liquidity_passed", True),
            item.get("trend_passed", False),
            _numeric_score(item.get("score")) if _numeric_score(item.get("score")) is not None else -1,
            item.get("turnover") or 0,
            item.get("news_count") or 0,
        ),
        reverse=True,
    )
    for index, item in enumerate(ranked, 1):
        item["rank"] = index

    return {
        "ok": True,
        "generated_at": utc_now_iso(),
        "universe": symbols,
        "count": len(ranked),
        "top": ranked[:limit],
        "all": ranked,
        "errors": errors,
    }


def run_compare(symbols: List[str]) -> Dict[str, Any]:
    """Compare multiple stock metrics side-by-side using active synchronized macro weights."""
    symbols = symbols[:5]
    if len(symbols) < 2:
        raise AppError("多股对比至少需要 2 只股票。")

    # 同步读取宏观矩阵参数，与每日推荐和单股 360 严格保持同一套权重与风险系数
    active_weights, risk_multiplier = get_active_factor_config()

    result = run_screener(
        symbols,
        limit=len(symbols),
        dynamic_weights=active_weights,
        risk_multiplier=risk_multiplier,
        skip_trend_culled_deep_scan=False,  # 多股对比获取所有标的完整指标
    )
    rows = result.get("all", [])
    leaders: Dict[str, Any] = {}
    if rows:
        metric_rules = {
            "综合评分": ("score", True),
            "20日涨跌": ("technical.returns.20d", True),
            "60日涨跌": ("technical.returns.60d", True),
            "成交额": ("turnover", True),
            "新闻热度": ("news_count", True),
        }

        def nested_value(item: Dict[str, Any], path: str) -> Optional[float]:
            current: Any = item
            for part in path.split("."):
                if not isinstance(current, dict):
                    return None
                current = current.get(part)
            return number_from(current)

        for label, (path, higher_better) in metric_rules.items():
            if label == "综合评分":
                # 仅限通过趋势闸门的标的参选综合评分领跑者，防止破位淘汰标的误导买方
                candidates = [(row, nested_value(row, path)) for row in rows if row.get("trend_passed", True)]
            else:
                candidates = [(row, nested_value(row, path)) for row in rows]
            candidates = [(row, value) for row, value in candidates if value is not None]
            if not candidates:
                continue
            best_row, best_value = sorted(candidates, key=lambda pair: pair[1], reverse=higher_better)[0]
            leaders[label] = {
                "symbol": best_row.get("symbol"),
                "value": best_value,
                "higher_better": higher_better,
            }

        # 估值维度智能领跑者：优先 PE，若无 PE 则智能取 PS/PB 进行合理性比较
        val_candidates = []
        for row in rows:
            val = row.get("valuation") or {}
            pe_val = number_from(val.get("pe") or val.get("pe_raw"))
            ps_val = number_from(val.get("ps") or val.get("ps_raw"))
            if pe_val is not None and pe_val > 0:
                val_candidates.append((row, pe_val, f"PE {pe_val:.1f}x"))
            elif ps_val is not None and ps_val > 0:
                val_candidates.append((row, ps_val * 4.0, f"PS {ps_val:.1f}x"))
        if val_candidates:
            best_row, best_score, best_label = sorted(val_candidates, key=lambda x: x[1])[0]
            leaders["估值PE"] = {
                "symbol": best_row.get("symbol"),
                "value": best_label,
                "higher_better": False,
            }

    return {
        "ok": True,
        "generated_at": utc_now_iso(),
        "symbols": symbols,
        "rows": rows,
        "leaders": leaders,
    }


from backend.services.portfolio_allocator import calculate_portfolio_allocation, STOCK_SECTOR_MAP


def get_daily_screener_recommendations(force: bool = False) -> Dict[str, Any]:
    """
    Run genuine multi-factor quantitative screening across the core US liquid universe.
    Governed by the Active Macro Regime State Machine (weights and risk multiplier).
    No hardcoded stocks, prices, fake option strikes, or synthetic funnel ratios.
    """
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    # 1. 组合核心股票池 (系统22只核心流动性标的 ∪ 服务端自选)
    core_symbols = list(DEFAULT_SCREENER_SYMBOLS)
    try:
        watchlist_symbols = [item["symbol"] for item in list_watchlist() if item.get("symbol")]
    except Exception:
        watchlist_symbols = []
    universe = list(dict.fromkeys(core_symbols + watchlist_symbols))
    wl_key = ",".join(sorted(watchlist_symbols))
    cache_key = f"daily:screener:top:{today_str}:{wl_key}"
    if not force:
        cached = get_cache(cache_key)
        if cached is not None and "picks" in cached:
            return cached

    # 2. 从宏观天气状态机提取完全一致的实时权重矩阵与风险惩罚系数
    active_weights, risk_multiplier = get_active_factor_config()
    macro_climate = get_macro_climate()
    regime = macro_climate.get("regime", {})

    # 提取宏观建议仓位中值 (例如 "75% - 90%" -> 82.5%，在停止做多期严格约束为 0.0%)
    suggested_exposure_str = regime.get("suggested_exposure", "75% - 90%")
    regime_code = str(regime.get("code") or "").upper()
    action_advice = str(regime.get("action_advice") or "")
    is_stop_buying = "EXTREME" in regime_code or "BEAR" in regime_code or "停止做多" in action_advice or "0% - 20%" in suggested_exposure_str
    macro_target_exposure = 0.0 if is_stop_buying else 80.0
    try:
        if not is_stop_buying:
            parts = suggested_exposure_str.replace("%", "").split("-")
            if len(parts) >= 2:
                # 严肃取区间中值，杜绝盲目取最高上沿
                macro_target_exposure = round((float(parts[0].strip()) + float(parts[1].strip())) / 2.0, 1)
            elif len(parts) == 1:
                macro_target_exposure = float(parts[0].strip())
    except Exception:
        macro_target_exposure = 0.0 if is_stop_buying else 75.0

    # 3. 真实并发执行多因子筛选与评分
    screen_result = run_screener(universe, limit=len(universe), dynamic_weights=active_weights, risk_multiplier=risk_multiplier)
    all_candidates = screen_result.get("all", [])

    total_scanned = len(universe)

    # 准确拆分状态：区分接口繁忙/频控、异常、有效标的
    busy_candidates = [c for c in all_candidates if c.get("fetch_failed") and c.get("status") == "BUSY"]
    failed_candidates = [c for c in all_candidates if c.get("fetch_failed") and c.get("status") != "BUSY"]
    valid_candidates = [c for c in all_candidates if not c.get("fetch_failed")]

    # 真实漏斗过滤 (规矩13：这22只大票均过得了流动性，第一级直接展示候选池只数，拿掉多余的流动性通过22/22，保留趋势闸门与评分截断)
    passed_liquidity = [
        c for c in valid_candidates
        if c.get("liquidity_passed", True) and ((c.get("turnover") or 0) >= 300_000_000 or (c.get("volume") or 0) >= 800_000)
    ]
    liquidity_culled = [
        c for c in valid_candidates
        if c not in passed_liquidity
    ]

    # Gate 1: 趋势硬规则 (站上20日均线 或 20日收益为正)
    passed_trend = [
        c for c in passed_liquidity
        if c.get("technical", {}).get("above_ma20") or (c.get("technical", {}).get("returns", {}).get("20d") or 0) > 0
    ]
    trend_culled = [c for c in passed_liquidity if c not in passed_trend]

    # Gate 2: 综合评分排序与截断。不足 65 分不进 Top 6，也不降到 55 分补位。
    top_candidates = [c for c in passed_trend if (_numeric_score(c.get("score")) or -1) >= 65][:6]

    funnel_pipeline = {
        "raw_universe": {
            "name": "候选股票池",
            "count": total_scanned,
            "valid_count": len(valid_candidates),
            "busy_count": len(busy_candidates) + len(failed_candidates),
            "definition": f"核心高流动性池 ∪ 自选关注池 (共 {total_scanned} 只候选)"
        },
        "layer_trend": {
            "name": "Gate 1: 趋势硬规则闸门",
            "passed_count": len(passed_trend),
            "culled_count": len(trend_culled),
            "condition": "站上 20 日均线 或 20 日动量为正 (淘汰破位下跌标的)"
        },
        "layer_score": {
            "name": "Gate 2: 规则综合评分截断",
            "passed_count": len(top_candidates),
            "culled_count": len(passed_trend) - len(top_candidates),
            "condition": "多因子综合评分规则阈值 ≥ 65 分 (规则阈值，未做 T+5/T+20 验证，截断 Top 6)"
        }
    }

    # 4. 规范化推荐标的数据结构
    top_picks = []
    top_symbols_set = set()
    for idx, c in enumerate(top_candidates, 1):
        px = c.get("last")
        if not px or px <= 0:
            continue
        tech = c.get("technical", {})
        atr_stop = tech.get("trailing_stop_2atr")
        if atr_stop:
            sl = atr_stop
            defense_text = f"第一止损防线 ${sl:.2f} (基于 2xATR 动态跟踪止损)"
        else:
            sl = round(px * 0.93, 2)
            defense_text = f"常规防线 ${sl:.2f} (固定 -7% 跟踪，ATR 数据不足)"

        sym = c.get("symbol", "")
        sym_clean = sym.split(".")[0]
        top_symbols_set.add(sym)
        sector_entry = STOCK_SECTOR_MAP.get(sym, STOCK_SECTOR_MAP.get(sym_clean, "核心科技与成长"))
        sector = sector_entry.get("sector", "核心科技与成长") if isinstance(sector_entry, dict) else str(sector_entry)
        zh_name = COMPANY_NAMES_ZH.get(sym) or COMPANY_NAMES_ZH.get(sym_clean) or c.get("name") or sym
        turnover_val = c.get("turnover") or 0.0
        raw_target = (c.get("rating") or {}).get("target")
        target_val = round(float(raw_target), 2) if (raw_target and float(raw_target) > 0) else None

        top_picks.append({
            "rank": idx,
            "symbol": sym,
            "name": zh_name,
            "last": px,
            "change_pct": c.get("change_pct"),
            "score": _numeric_score(c.get("score")),
            "verdict": c.get("verdict") or verdict_for_score(_numeric_score(c.get("score"))),
            "sector": sector,
            "technical": tech,  # 注入完整技术指标对象，供前端精准呈现 20D 动量与均线形态
            "volume_ratio": tech.get("volume_ratio_20d"),  # 严禁写死 1.0x，无数据返回 None
            "tags": c.get("tags") or [],
            "core_rationale": f"规则分 {_numeric_score(c.get('score'))}（阈值 65，未经 T+5/T+20 验证）。动量形态【{tech.get('trend_label', '未标注')}】，20日收益 {tech.get('returns', {}).get('20d', 0):.1f}%。",
            "primary_defense": defense_text,
            "stop_loss": sl,
            "target_price": target_val,
            "turnover": turnover_val,
            "atr14": tech.get("atr14"),
            "factor_breakdown": c.get("factor_breakdown"),
            "data_status": c.get("data_status", "LIVE"),
            "data_source_badge": "🟢 实时量化" if c.get("data_status") == "LIVE" else "🔵 历史快照",
            "threshold_disclaimer": "规则阈值 (≥65分)，未做 T+5/T+20 验证",
        })

    # 5. 建立全量透明的接近入选与淘汰明细 (涵盖评分临界、趋势破位淘汰、流动性淘汰、接口繁忙)
    near_misses = []

    # 5.1 评分临界：通过趋势闸门但未进入 Top 6。没有综合分的不记成 0 分。
    def _trend_score(row: Dict[str, Any]) -> Optional[float]:
        return _numeric_score(row.get("score"))

    score_near = [
        c for c in passed_trend
        if c.get("symbol") not in top_symbols_set and (_trend_score(c) or -1) >= 55.0
    ]
    score_near.sort(key=lambda x: _trend_score(x) or -1, reverse=True)
    reserve_rank = 1
    for c in score_near:
        sc = _trend_score(c)
        if sc is None:
            continue
        fb = c.get("factor_breakdown") or {}
        weakest_text = _weakest_factor_text(fb)

        sym = c.get("symbol", "")
        sym_clean = sym.split(".")[0]
        zh_name = COMPANY_NAMES_ZH.get(sym) or COMPANY_NAMES_ZH.get(sym_clean) or c.get("name") or sym
        ret20 = ((c.get("technical") or {}).get("returns") or {}).get("20d", 0.0)

        if sc >= 65.0:
            gap = 0.0
            category = "RESERVE_BENCH"
            category_label = f"储备池第 {reserve_rank} 顺位 (评分达标)"
            reason = f"综合评分 {sc:.1f} 分已达规则门槛 (≥65分)，因单日入选名额上限 (Top 6) 暂列储备池第 {reserve_rank} 顺位。"
            reserve_rank += 1
        else:
            gap = round(65.0 - sc, 1)
            category = "NEAR_SCORE"
            category_label = f"评分临界 (距门槛差 {gap} 分)"
            reason = f"综合评分 {sc:.1f} 分，距离 65.0 分规则门槛差 {gap} 分。主要瓶颈：{weakest_text}。"

        near_misses.append({
            "symbol": sym,
            "name": zh_name,
            "last": c.get("last"),
            "score": sc,
            "gap": gap,
            "ret20": ret20,
            "verdict": c.get("verdict", "可加入观察"),
            "category": category,
            "category_label": category_label,
            "reason": reason,
            "cull_reason": reason,
            "factor_breakdown": fb
        })

    # 5.2 趋势合格但评分偏低（< 55 分）。综合分为空的单独列出，不写成 0 分。
    score_lag = [
        c for c in passed_trend
        if c.get("symbol") not in top_symbols_set and _trend_score(c) is not None and _trend_score(c) < 55.0
    ]
    for c in score_lag:
        sc = _trend_score(c) or 0.0
        gap = round(65.0 - sc, 1)
        fb = c.get("factor_breakdown") or {}
        weakest_text = _weakest_factor_text(fb)

        sym = c.get("symbol", "")
        sym_clean = sym.split(".")[0]
        zh_name = COMPANY_NAMES_ZH.get(sym) or COMPANY_NAMES_ZH.get(sym_clean) or c.get("name") or sym
        near_misses.append({
            "symbol": sym,
            "name": zh_name,
            "last": c.get("last"),
            "score": sc,
            "gap": gap,
            "ret20": ((c.get("technical") or {}).get("returns") or {}).get("20d"),
            "verdict": c.get("verdict") or "中性观察",
            "category": "SCORE_LAG",
            "category_label": "趋势合格但评分偏低",
            "reason": f"通过趋势硬规则，但规则分仅 {sc:.1f} 分（未达 65 分）。瓶颈：{weakest_text}。",
            "factor_breakdown": fb
        })

    unscored = [c for c in passed_trend if c.get("symbol") not in top_symbols_set and _trend_score(c) is None]
    for c in unscored:
        sym = c.get("symbol", "")
        sym_clean = sym.split(".")[0]
        zh_name = COMPANY_NAMES_ZH.get(sym) or COMPANY_NAMES_ZH.get(sym_clean) or c.get("name") or sym
        reason = "通过趋势硬规则，但财务与估值不足以计算综合分，不记为 0 分，也不进入 Top 6。"
        near_misses.append({
            "symbol": sym,
            "name": zh_name,
            "last": c.get("last"),
            "score": None,
            "gap": None,
            "ret20": ((c.get("technical") or {}).get("returns") or {}).get("20d"),
            "verdict": "数据不足，不能评级",
            "category": "UNSCORED",
            "category_label": "数据不足",
            "reason": reason,
            "cull_reason": reason,
            "factor_breakdown": c.get("factor_breakdown"),
        })

    # 5.3 趋势硬规则淘汰（成交活跃但跌破20日均线且动量为负）
    for c in trend_culled:
        tech = c.get("technical", {})
        ret20 = tech.get("returns", {}).get("20d", 0.0)
        sym = c.get("symbol", "")
        sym_clean = sym.split(".")[0]
        zh_name = COMPANY_NAMES_ZH.get(sym) or COMPANY_NAMES_ZH.get(sym_clean) or c.get("name") or sym
        near_misses.append({
            "symbol": sym,
            "name": zh_name,
            "last": c.get("last"),
            "score": None,  # 趋势淘汰未参与下游多因子打分，留空展示，杜绝假 0.0 与 -65 距门槛
            "gap": None,
            "ret20": ret20,
            "verdict": "趋势过滤",
            "category": "TREND_CULLED",
            "category_label": "趋势破位淘汰",
            "reason": f"未通过趋势硬规则闸门：20日涨跌幅 {ret20:+.1f}% 且跌破20日均线，处于防守承压期，触发防套硬规则汰除。",
            "factor_breakdown": None,
        })

    # 5.4 真实流动性不足淘汰（成交额 < $300M 且成交量 < 80万股）
    for c in liquidity_culled:
        sym = c.get("symbol", "")
        sym_clean = sym.split(".")[0]
        zh_name = COMPANY_NAMES_ZH.get(sym) or COMPANY_NAMES_ZH.get(sym_clean) or c.get("name") or sym
        turnover_m = (c.get("turnover") or 0.0) / 1_000_000
        vol_k = (c.get("volume") or 0) / 1_000
        near_misses.append({
            "symbol": sym,
            "name": zh_name,
            "last": c.get("last"),
            "score": None,  # 未参与多因子打分，留空展示
            "gap": None,
            "verdict": "流动性不足淘汰",
            "category": "LIQUIDITY_CULLED",
            "category_label": "流动性淘汰",
            "reason": f"单日成交额 ${turnover_m:.1f}M (< $300M) 且成交量 {vol_k:.0f}k (< 800k)，不满足高流动性防滑点闸门，依规剔除后续深度请求。",
            "factor_breakdown": None,
        })

    # 5.5 接口繁忙 / 频控未取得标的（单独列出，绝不算进流动性淘汰）
    for c in busy_candidates:
        sym = c.get("symbol", "")
        sym_clean = sym.split(".")[0]
        zh_name = COMPANY_NAMES_ZH.get(sym) or COMPANY_NAMES_ZH.get(sym_clean) or c.get("name") or sym
        near_misses.append({
            "symbol": sym,
            "name": zh_name,
            "last": c.get("last"),
            "score": None,  # 未打分，留空展示
            "gap": None,
            "verdict": "接口繁忙",
            "category": "API_BUSY",
            "category_label": "接口繁忙 (待重试)",
            "reason": f"长桥行情接口繁忙（{c.get('fail_reason', '触发频控')}），未能在限时内取得完整行情，未计入流动性汰除，请稍后刷新重试。",
            "factor_breakdown": None,
        })

    near_misses.sort(key=lambda x: (x.get("category") != "API_BUSY", x.get("score") if x.get("score") is not None else -1), reverse=True)

    # 6. 计算机构风险平价仓位 (保留核心模型能力，当单笔因现金限制为 0 股时注明原因)
    portfolio_plan = None
    if top_picks:
        try:
            portfolio_plan = calculate_portfolio_allocation(
                candidates=top_picks,
                total_capital=100000.0,
                risk_per_trade_pct=1.5,
                max_sector_exposure_pct=30.0,
                max_single_stock_pct=25.0,
                macro_exposure_limit_pct=macro_target_exposure
            )
        except Exception:
            portfolio_plan = None

    result = {
        "ok": bool(top_picks),
        "generated_at": utc_now_iso(),
        "universe_definition": f"核心高流动性股票池 (共 {total_scanned} 只候选，已剔除指数ETF)",
        "universe_size": total_scanned,
        "count": len(top_picks),
        "funnel_pipeline": funnel_pipeline,
        "pipeline": {
            "total_screened": total_scanned,
            "liquidity_passed": len(passed_liquidity),
            "trend_passed": len(passed_trend),
            "top_picks": len(top_picks),
        },
        "picks": top_picks,
        "near_misses": near_misses,
        "culled_details": near_misses,  # 双向对齐前端字段
        "active_weights": active_weights,
        "risk_multiplier": risk_multiplier,
        "macro_target_exposure": macro_target_exposure,
        "portfolio_plan": portfolio_plan,
        "errors": screen_result.get("errors", []),
        "rate_limited_symbols": [c.get("symbol") for c in busy_candidates if c.get("symbol")],
        "exceptions": [
            {"symbol": c.get("symbol"), "message": c.get("fail_reason") or "取数失败"}
            for c in failed_candidates
        ],
    }

    # 有失败、触发频控，或入选全是历史快照时，不写入当天缓存。
    has_busy = len(busy_candidates) > 0
    has_failed = len(failed_candidates) > 0
    all_snapshots = bool(top_picks) and all(p.get("data_status") == "SNAPSHOT" for p in top_picks)
    if not has_busy and not has_failed and not all_snapshots:
        set_cache(cache_key, result, 86400)

    return result


