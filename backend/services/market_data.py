"""
Market data service: Longbridge CLI communication, data normalization,
network graph builder, timeline extraction, and fallback resilience.
"""
import json
import os
import re
import shutil
import ssl
import subprocess
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.config import (
    DEFAULT_TIMEOUT,
    LONG_BRIDGE_BIN,
    MAX_WORKERS,
    REPORTS_DIR,
    AppError,
)
from backend.core.financial import (
    analyze_financial_quality,
    analyze_management_governance,
    analyze_risk_radar,
    analyze_valuation_profile,
    build_factor_breakdown,
    summarize_insider_trades,
)
from backend.core.indicators import compute_technical_summary
from backend.core.utils import (
    clamp,
    command_error_message,
    first_value,
    normalize_symbol,
    number_from,
    pick_number,
    strip_html,
    utc_now_iso,
)
from backend.db import get_cache, latest_analysis_payload, save_analysis, set_cache

# Global serialized pacing lock for Longbridge CLI (250ms gap = 4 QPS, safe and fast)
_LB_CLI_LOCK = threading.Lock()
_LAST_LB_EXEC_TIME = 0.0
MIN_LB_INTERVAL = 0.25  # 250ms gap between calls to accelerate batch fetches while respecting rate limits


def longbridge_status() -> Dict[str, Any]:
    """Check whether Longbridge CLI is installed, responsive, and authenticated."""
    cached = get_cache("longbridge:auth:check")
    if cached is not None:
        return cached

    # 1. 优先极速检查本地 Token 凭证文件，避免耗时的网络往返阻塞
    tokens_dir = os.path.expanduser("~/.longbridge/openapi/tokens")
    if os.path.isdir(tokens_dir):
        now_ts = time.time()
        for fname in os.listdir(tokens_dir):
            t_path = os.path.join(tokens_dir, fname)
            if os.path.isfile(t_path):
                try:
                    with open(t_path, "r", encoding="utf-8") as f:
                        t_data = json.load(f)
                    expires_at = t_data.get("expires_at", 0)
                    if expires_at and expires_at > now_ts:
                        res = {
                            "ok": True,
                            "authenticated": True,
                            "binary": LONG_BRIDGE_BIN,
                            "message": "长桥 CLI 认证有效，实时行情流已连接",
                        }
                        set_cache("longbridge:auth:check", res, 60)
                        return res
                    elif expires_at and expires_at <= now_ts:
                        res = {
                            "ok": False,
                            "authenticated": False,
                            "binary": LONG_BRIDGE_BIN,
                            "message": "长桥 CLI Token 已过期，请在终端执行 'longbridge auth login' 重新登录",
                        }
                        set_cache("longbridge:auth:check", res, 15)
                        return res
                except Exception:
                    pass

    # 2. 本地检查未明确时，调用 CLI 命令核验
    try:
        completed = subprocess.run(
            [LONG_BRIDGE_BIN, "auth", "status", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        if completed.returncode == 0 and completed.stdout:
            try:
                data = json.loads(completed.stdout)
                token_status = data.get("token", {}).get("status")
                if token_status == "valid":
                    res = {
                        "ok": True,
                        "authenticated": True,
                        "binary": LONG_BRIDGE_BIN,
                        "member_id": data.get("account", {}).get("member_id"),
                        "message": "长桥 CLI 认证有效，实时行情流已连接",
                    }
                    set_cache("longbridge:auth:check", res, 60)
                    return res
            except Exception:
                pass

        stdout = (completed.stdout or "") + (completed.stderr or "")
        if "expired" in stdout.lower() or "invalid" in stdout.lower():
            res = {
                "ok": False,
                "authenticated": False,
                "binary": LONG_BRIDGE_BIN,
                "message": "长桥 CLI Refresh Token 已过期，请在终端执行 'longbridge auth login' 重新登录",
            }
        else:
            res = {
                "ok": False,
                "authenticated": False,
                "binary": LONG_BRIDGE_BIN,
                "message": "长桥 CLI 认证未就绪，请在终端执行 'longbridge auth login'",
            }
        set_cache("longbridge:auth:check", res, 15)
        return res
    except FileNotFoundError:
        return {
            "ok": False,
            "authenticated": False,
            "binary": LONG_BRIDGE_BIN,
            "message": "未找到 longbridge 命令行工具，请确保已安装并在 PATH 中。",
        }
    except Exception as exc:
        return {
            "ok": False,
            "authenticated": False,
            "binary": LONG_BRIDGE_BIN,
            "message": f"长桥状态检测异常：{exc}",
        }


_LB_BIN_CHECK: Dict[str, Any] = {"at": 0.0, "ok": None}
_LB_BIN_CHECK_TTL = 60.0


def longbridge_binary_available() -> bool:
    """Cheap, cached (60s) check whether the Longbridge CLI binary is on PATH.

    Lets callers fail fast in Yahoo-only mode instead of paying the 450ms
    serialized pacing sleep for every CLI call that is doomed to fail.
    """
    now = time.time()
    if _LB_BIN_CHECK["ok"] is None or now - _LB_BIN_CHECK["at"] > _LB_BIN_CHECK_TTL:
        _LB_BIN_CHECK["ok"] = bool(shutil.which(LONG_BRIDGE_BIN)) or os.path.isfile(LONG_BRIDGE_BIN)
        _LB_BIN_CHECK["at"] = now
    return bool(_LB_BIN_CHECK["ok"])


def run_longbridge(args: List[str], ttl_seconds: int, timeout: int = DEFAULT_TIMEOUT, max_retries: int = 1) -> Dict[str, Any]:
    """
    Run Longbridge CLI command with global lock, serialized 450ms pacing,
    controlled single retry on 429 without amplification, and cache result in SQLite.
    """
    cache_key = "longbridge:" + " ".join(args)
    cached = get_cache(cache_key)
    if cached is not None:
        cached["_cached"] = True
        return cached

    if not longbridge_binary_available():
        raise AppError("未检测到长桥 CLI，请先安装并配置 longbridge。", 503)

    command = [LONG_BRIDGE_BIN] + args
    last_completed = None
    global _LAST_LB_EXEC_TIME

    for attempt in range(max_retries + 1):
        try:
            with _LB_CLI_LOCK:
                now = time.time()
                elapsed = now - _LAST_LB_EXEC_TIME
                if elapsed < MIN_LB_INTERVAL:
                    time.sleep(MIN_LB_INTERVAL - elapsed)
                _LAST_LB_EXEC_TIME = time.time()

            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            last_completed = completed
        except FileNotFoundError as exc:
            raise AppError("未检测到长桥 CLI，请先安装并配置 longbridge。", 503) from exc
        except subprocess.TimeoutExpired as exc:
            if attempt < max_retries:
                time.sleep(1.0)
                continue
            raise AppError(f"请求超时：长桥服务未在 {timeout}s 内响应 (接口繁忙)", 504) from exc

        err_text = completed.stderr or ""
        # Detect Longbridge 429 rate limit (e.g. 429002 frequency limit) only in stderr or on non-zero exit
        is_429 = (
            "429002" in err_text
            or "frequency limit" in err_text.lower()
            or "too many requests" in err_text.lower()
            or (completed.returncode != 0 and "429" in err_text)
        )
        if is_429:
            if attempt < max_retries:
                # Sleep 1.2s to clear the 1-second rolling rate limit window
                time.sleep(1.2)
                continue
            raise AppError("触发频控 (长桥接口繁忙，已超频控上限 429002，请稍后刷新)", 429)

        if completed.returncode != 0:
            if attempt < max_retries and ("retry" in err_text.lower() or "timeout" in err_text.lower() or "reset" in err_text.lower()):
                time.sleep(1.0)
                continue
            raise AppError(
                command_error_message(completed.stderr, completed.stdout),
                502,
                {"command": command, "stderr": completed.stderr[-1000:]},
            )

        # Successful execution
        break

    stdout = (last_completed.stdout if last_completed else "").strip()
    try:
        payload = json.loads(stdout) if stdout else None
    except json.JSONDecodeError as exc:
        raise AppError(
            "长桥返回的 JSON 格式异常，系统无法解析。",
            502,
            {"command": command, "stdout": stdout[:2000], "stderr": (last_completed.stderr if last_completed else "")[-1000:]},
        ) from exc

    # In case CLI returns 0 but payload itself contains Longbridge API 429 error code
    if isinstance(payload, dict) and (
        payload.get("code") in (429, 429002)
        or "frequency limit" in str(payload.get("message", "")).lower()
    ):
        raise AppError("触发频控 (长桥接口繁忙，已超频控上限 429002，请稍后刷新)", 429)

    result = {
        "source": "longbridge_cli",
        "command": command,
        "fetched_at": utc_now_iso(),
        "data": payload,
        "_cached": False,
    }
    # Only cache if data is valid and ttl > 0
    if payload is not None and ttl_seconds > 0:
        set_cache(cache_key, result, ttl_seconds)
    return result


def fetch_yahoo_quotes_batch(symbols: List[str], timeout: int = 8) -> Dict[str, Dict[str, Any]]:
    """Fetch quotes concurrently from Yahoo Finance as a resilient fallback."""
    if not symbols:
        return {}
    ctx = ssl._create_unverified_context()
    results: Dict[str, Dict[str, Any]] = {}

    def _fetch_one(s: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        clean = s.replace(".US", "").upper().replace("^", "%5E")
        cache_key = f"yahoo_quote:{clean}"
        cached = get_cache(cache_key)
        if cached is not None and isinstance(cached, dict):
            return s, cached
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{clean}?interval=1d&range=5d"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            resp = urllib.request.urlopen(req, context=ctx, timeout=timeout)
            payload = json.loads(resp.read().decode("utf-8"))
            chart_res = payload.get("chart", {}).get("result", [])
            if not chart_res:
                return None
            data = chart_res[0]
            meta = data.get("meta", {})
            quote_data = data.get("indicators", {}).get("quote", [{}])[0]
            closes = [c for c in quote_data.get("close", []) if c is not None]
            last = meta.get("regularMarketPrice") or (closes[-1] if closes else None)
            if not last:
                return None
            prev_close = meta.get("chartPreviousClose") or (closes[-2] if len(closes) > 1 else last)
            chg_pct = round((last / prev_close - 1) * 100, 2) if prev_close else 0.0
            day_high = meta.get("regularMarketDayHigh") or (max(closes) if closes else last)
            day_low = meta.get("regularMarketDayLow") or (min(closes) if closes else last)
            volume = meta.get("regularMarketVolume") or (quote_data.get("volume", [0])[-1] if quote_data.get("volume") else 0)
            from backend.core.stock_registry import get_company_zh_name
            zh_name = get_company_zh_name(s, meta.get("shortName") or clean)
            q = {
                "symbol": s,
                "name": zh_name,
                "last": round(float(last), 2),
                "prev_close": round(float(prev_close), 2) if prev_close else None,
                "open": round(float(quote_data.get("open", [last])[-1]), 2) if quote_data.get("open") else None,
                "high": round(float(day_high), 2) if day_high else None,
                "low": round(float(day_low), 2) if day_low else None,
                "volume": volume,
                "turnover": round(float(last * (volume or 0)), 2),
                "trade_status": "Normal",
                "change_pct": chg_pct,
                "data_status": "YAHOO_FALLBACK",
                "source": "yahoo_finance",
                "fetched_at": utc_now_iso(),
            }
            set_cache(cache_key, q, 30)
            return s, q
        except Exception:
            return None

    worker_count = min(6, len(symbols))
    with ThreadPoolExecutor(max_workers=worker_count) as ex:
        futures = [ex.submit(_fetch_one, sym) for sym in symbols]
        for f in as_completed(futures):
            res = f.result()
            if res:
                results[res[0]] = res[1]
    return results


def fetch_yahoo_klines(symbol: str, count: int = 260) -> List[Dict[str, Any]]:
    """Fetch daily K-lines from Yahoo Finance formatted as standard klines list."""
    clean_sym = symbol.replace(".US", "").upper().replace("^", "%5E")
    cache_key = f"yahoo_klines:{clean_sym}:{count}"
    cached = get_cache(cache_key)
    if cached is not None and isinstance(cached, list) and len(cached) > 0:
        return cached

    ctx = ssl._create_unverified_context()
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{clean_sym}?interval=1d&range=1y"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=10)
        payload = json.loads(resp.read().decode("utf-8"))
        chart_res = payload.get("chart", {}).get("result", [])
        if not chart_res:
            return []
        data = chart_res[0]
        timestamps = data.get("timestamp", [])
        quote_indicators = data.get("indicators", {}).get("quote", [{}])[0]
        closes = quote_indicators.get("close", [])
        opens = quote_indicators.get("open", closes)
        highs = quote_indicators.get("high", closes)
        lows = quote_indicators.get("low", closes)
        volumes = quote_indicators.get("volume", [])

        klines = []
        for ts, o, h, l, c, v in zip(timestamps, opens, highs, lows, closes, volumes):
            if c is not None:
                klines.append({
                    "timestamp": ts,
                    "open": float(o if o is not None else c),
                    "high": float(h if h is not None else c),
                    "low": float(l if l is not None else c),
                    "close": float(c),
                    "volume": float(v if v is not None else 0),
                    "turnover": float(c * (v if v is not None else 0)),
                })
        if count and len(klines) > count:
            klines = klines[-count:]
        if klines:
            set_cache(cache_key, klines, 3600)
        return klines
    except Exception:
        return []


def fetch_batch_quotes(symbols: List[str], timeout: int = 15) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, str]]:
    """
    Fetch live quotes for multiple symbols with primary Longbridge CLI and automatic Yahoo Finance fallback.
    Returns (quotes_map, errors_map).
    """
    if not symbols:
        return {}, {}
    norm_symbols = [normalize_symbol(s) for s in symbols]
    cmd_args = ["quote"] + norm_symbols + ["--format", "json"]
    quotes_map: Dict[str, Dict[str, Any]] = {}
    errors_map: Dict[str, str] = {}
    try:
        # Cache for 20 seconds to avoid repeating batch within same screen/refresh cycle
        res = run_longbridge(cmd_args, ttl_seconds=20, timeout=timeout, max_retries=1)
        items = unwrap_items(res.get("data"))
        for item in items:
            sym = first_value(item, ["symbol"])
            if sym:
                quotes_map[sym] = extract_quote(item, sym)
        for s in norm_symbols:
            if s not in quotes_map:
                errors_map[s] = "行情接口未返回该标的数据"
    except AppError as exc:
        for s in norm_symbols:
            errors_map[s] = exc.message
    except Exception as exc:
        for s in norm_symbols:
            errors_map[s] = f"行情获取异常：{exc}"

    # 自动弹性降级：若长桥未能返回全部或部分标的，无缝调用 Yahoo Finance 补齐真实行情
    missing = [s for s in norm_symbols if s not in quotes_map]
    if missing:
        try:
            y_quotes = fetch_yahoo_quotes_batch(missing, timeout=8)
            for s, yq in y_quotes.items():
                quotes_map[s] = yq
                if s in errors_map:
                    del errors_map[s]
        except Exception:
            pass

    return quotes_map, errors_map



def fetch_longbridge_modules(
    specs: Dict[str, Any],
    timeout: int = 8,
) -> Tuple[Dict[str, Optional[Dict[str, Any]]], List[Dict[str, Any]]]:
    """Concurrently fetch multiple Longbridge endpoints with paced execution and individual timeout protection."""
    results: Dict[str, Optional[Dict[str, Any]]] = {name: None for name in specs}
    errors: List[Dict[str, Any]] = []
    if not specs:
        return results, errors

    # Paced worker pool (max 10) to execute Longbridge endpoints in parallel
    worker_count = max(1, min(10, len(specs)))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = {}
        for idx, (name, spec) in enumerate(specs.items()):
            args = spec[0]
            ttl = spec[1]
            mod_timeout = spec[2] if len(spec) > 2 else timeout
            # Stagger submissions slightly to prevent blasting at the exact same millisecond
            if idx > 0 and idx % 4 == 0:
                time.sleep(0.04)
            futures[executor.submit(run_longbridge, args, ttl, mod_timeout)] = (name, args)
        for future in as_completed(futures):
            name, args = futures[future]
            try:
                results[name] = future.result()
            except AppError as exc:
                errors.append({"module": name, "message": exc.message, "status": exc.status})
            except Exception as exc:
                errors.append({"module": name, "message": f"模块取数异常：{exc}", "command": args})
    return results, errors


def unwrap_items(payload: Any) -> List[Dict[str, Any]]:
    """Unwrap nested lists from Longbridge JSON data structures."""
    if payload is None:
        return []
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in ("data", "items", "list", "quotes", "candles", "news", "filings", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
        return [payload]
    return []


def extract_quote(raw: Dict[str, Any], symbol: str) -> Dict[str, Any]:
    """Parse real-time quote metrics from either raw response wrapper or single quote dict."""
    if not raw:
        return {"symbol": symbol, "last": None, "prev_close": None, "volume": None, "turnover": None, "change_pct": None}

    if "data" in raw:
        items = unwrap_items(raw.get("data"))
        quote = next((item for item in items if str(first_value(item, ["symbol", "ticker", "code"]) or "").upper() == symbol), None)
        if quote is None and items:
            quote = items[0]
        quote = quote or {}
    else:
        quote = raw

    last = pick_number(quote, ["last_done", "last", "price", "close"])
    prev_close = pick_number(quote, ["prev_close", "previous_close", "pre_close"])
    change_pct = None
    if last is not None and prev_close:
        change_pct = (last / prev_close - 1) * 100

    return {
        "symbol": symbol,
        "name": first_value(quote, ["name", "security_name", "display_name"]),
        "last": last,
        "prev_close": prev_close,
        "open": pick_number(quote, ["open"]),
        "high": pick_number(quote, ["high"]),
        "low": pick_number(quote, ["low"]),
        "volume": pick_number(quote, ["volume"]),
        "turnover": pick_number(quote, ["turnover"]),
        "trade_status": first_value(quote, ["trade_status", "status"]),
        "change_pct": change_pct,
        "raw": quote,
        "fetched_at": raw.get("fetched_at") if isinstance(raw, dict) else None,
        "cached": raw.get("_cached", False) if isinstance(raw, dict) else False,
    }


def extract_klines(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse candlestick bars."""
    items = unwrap_items(raw.get("data"))
    klines: List[Dict[str, Any]] = []
    for item in items:
        close = pick_number(item, ["close", "c"])
        if close is None:
            continue
        klines.append(
            {
                "timestamp": first_value(item, ["timestamp", "time", "date"]),
                "open": pick_number(item, ["open", "o"]),
                "high": pick_number(item, ["high", "h"]),
                "low": pick_number(item, ["low", "l"]),
                "close": close,
                "volume": pick_number(item, ["volume", "v"]),
                "turnover": pick_number(item, ["turnover"]),
                "raw": item,
            }
        )
    return klines


def extract_news(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse recent news headlines."""
    items = unwrap_items(raw.get("data"))
    normalized = []
    for item in items:
        title = first_value(item, ["title", "name", "headline"])
        if not title:
            continue
        normalized.append(
            {
                "id": first_value(item, ["id", "article_id", "news_id"]),
                "title": title,
                "published_at": first_value(item, ["published_at", "publish_time", "time", "date"]),
                "likes": pick_number(item, ["likes", "like_count", "likes_count"]),
                "comments": pick_number(item, ["comments", "comment_count", "comments_count"]),
                "raw": item,
            }
        )
    return normalized


def extract_company(raw: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Parse company profile."""
    if not raw:
        return None
    data = raw.get("data")
    if not isinstance(data, dict):
        return None
    return {
        "name": first_value(data, ["name", "company_name"]),
        "company_name": first_value(data, ["company_name", "name"]),
        "ticker": first_value(data, ["ticker"]),
        "market": first_value(data, ["market"]),
        "founded": first_value(data, ["founded"]),
        "employees": pick_number(data, ["employees"]),
        "manager": first_value(data, ["manager", "chairman"]),
        "website": first_value(data, ["website"]),
        "profile": first_value(data, ["profile"]),
        "address": first_value(data, ["address", "office_address"]),
    }


def extract_valuation(raw: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Parse PE, PS, PB, and industry peer valuation benchmarks."""
    if not raw:
        return None
    data = raw.get("data") if isinstance(raw.get("data"), dict) else raw
    if not isinstance(data, dict):
        return None
    overview = data.get("overview") if isinstance(data.get("overview"), dict) else {}
    indicator = (overview.get("indicator") or "pe").lower()
    metrics = overview.get("metrics") if isinstance(overview.get("metrics"), dict) else {}

    # Locate active metric: priority indicator, then pe, ps, pb
    active_metric = metrics.get(indicator)
    if not isinstance(active_metric, dict):
        for candidate_key in ("pe", "ps", "pb"):
            if isinstance(metrics.get(candidate_key), dict):
                active_metric = metrics.get(candidate_key)
                indicator = candidate_key
                break
    active_metric = active_metric if isinstance(active_metric, dict) else {}

    peers = data.get("peers") if isinstance(data.get("peers"), dict) else {}
    peer_metric = peers.get(indicator) if isinstance(peers.get(indicator), dict) else {}
    if not peer_metric:
        for candidate_key in ("pe", "ps", "pb"):
            if isinstance(peers.get(candidate_key), dict):
                peer_metric = peers.get(candidate_key)
                break
    peer_list = peer_metric.get("list") if isinstance(peer_metric.get("list"), list) else []

    metric_str = first_value(active_metric, ["metric", "value"])
    metric_val = number_from(metric_str) or pick_number(active_metric, ["circle", "part"])
    median_val = number_from(first_value(active_metric, ["industry_median"]) or peer_metric.get("industry_median"))

    desc_str = active_metric.get("desc") or overview.get("ai_summary") or ""
    rank_val = None
    total_peers = None
    if desc_str:
        # Regex search for rank: e.g. 行业排名 <strong>219/253</strong> or 行业排名 219/253
        m = re.search(r"行业排名\s*(?:<[^>]+>)*\s*(\d+)\s*/\s*(\d+)", desc_str)
        if m:
            try:
                rank_val = int(m.group(1))
                total_peers = int(m.group(2))
            except Exception:
                pass
    if not total_peers and peer_list:
        total_peers = len(peer_list)

    peer_premium = None
    if metric_val is not None and median_val and median_val > 0:
        peer_premium = round((metric_val / median_val - 1) * 100, 1)

    indicator_labels = {
        "pe": "P/E",
        "ps": "P/S",
        "pb": "P/B",
    }
    indicator_names = {
        "pe": "市盈率 (P/E)",
        "ps": "市销率 (P/S)",
        "pb": "市净率 (P/B)",
    }
    ind_label = indicator_labels.get(indicator, indicator.upper())
    ind_name = indicator_names.get(indicator, indicator.upper())

    return {
        "date": overview.get("date"),
        "indicator": indicator,
        "indicator_label": ind_label,
        "indicator_name": ind_name,
        "metric_value": metric_val,
        "metric_str": metric_str,
        "pe": metric_str if indicator == "pe" else None,
        "pe_raw": metric_val if indicator == "pe" else None,
        "ps": metric_str if indicator == "ps" else None,
        "ps_raw": metric_val if indicator == "ps" else None,
        "pb": metric_str if indicator == "pb" else None,
        "pb_raw": metric_val if indicator == "pb" else None,
        "industry_median": median_val,
        "peer_rank": rank_val,
        "peer_total": total_peers,
        "peer_premium_pct": peer_premium,
        "summary": strip_html(desc_str),
        "peers": [
            {
                "name": first_value(peer, ["name", "ticker", "counter_id"]),
                "value": pick_number(peer, ["value"]),
            }
            for peer in peer_list[:8]
            if isinstance(peer, dict)
        ],
    }


def extract_rating(raw: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Parse institutional consensus ratings and target prices."""
    if not raw:
        return None
    data = raw.get("data")
    if not isinstance(data, dict):
        return None
    instratings = data.get("instratings") if isinstance(data.get("instratings"), dict) else {}
    analyst = data.get("analyst") if isinstance(data.get("analyst"), dict) else {}
    evaluate = instratings.get("evaluate") if isinstance(instratings.get("evaluate"), dict) else {}
    target = analyst.get("target") if isinstance(analyst.get("target"), dict) else {}
    return {
        "recommend": instratings.get("recommend"),
        "target": pick_number(instratings, ["target"]),
        "target_change_pct": pick_number(instratings, ["change"]),
        "updated_at": instratings.get("updated_at"),
        "currency": instratings.get("ccy_symbol"),
        "strong_buy": pick_number(evaluate, ["strong_buy"]),
        "buy": pick_number(evaluate, ["buy"]),
        "hold": pick_number(evaluate, ["hold"]),
        "sell": pick_number(evaluate, ["sell"]),
        "highest_price": pick_number(target, ["highest_price"]),
        "lowest_price": pick_number(target, ["lowest_price"]),
        "industry_rank": pick_number(analyst, ["industry_rank"]),
        "industry_total": pick_number(analyst, ["industry_total"]),
        "industry_name": analyst.get("industry_name"),
    }


def extract_financials(raw: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Parse fundamental financial snapshot."""
    if not raw:
        return None
    data = raw.get("data") if isinstance(raw.get("data"), dict) else raw
    if not isinstance(data, dict):
        return None
    indicators = data.get("indicators") if isinstance(data.get("indicators"), list) else []
    normalized = []
    for item in indicators:
        if not isinstance(item, dict):
            continue
        field = first_value(item, ["field_name", "field", "indicator_field", "key"])
        if not field:
            continue
        normalized.append(
            {
                "field": field,
                "name": first_value(item, ["indicator_name", "name", "title"]) or field,
                "value": pick_number(item, ["indicator_value", "value", "val"]),
                "yoy": pick_number(item, ["yoy", "growth"]),
                "unit": first_value(item, ["unit"]),
                "raw": item,
            }
        )
    if not normalized and not data.get("report"):
        return None
    return {
        "currency": data.get("currency"),
        "report": data.get("report"),
        "report_txt": data.get("report_txt"),
        "indicators": normalized,
    }


def extract_filings(raw: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parse SEC regulatory filings."""
    if not raw:
        return []
    items = unwrap_items(raw.get("data"))
    return [
        {
            "id": first_value(item, ["id"]),
            "title": first_value(item, ["title", "file_name"]),
            "file_name": first_value(item, ["file_name"]),
            "publish_at": first_value(item, ["publish_at", "published_at", "time"]),
            "file_count": pick_number(item, ["file_count"]),
            "file_urls": item.get("file_urls") if isinstance(item.get("file_urls"), list) else [],
        }
        for item in items
        if first_value(item, ["title", "file_name"])
    ]


def extract_executives(raw: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parse executive team and board members from Longbridge CLI."""
    if not raw:
        return []
    data = raw.get("data") if isinstance(raw.get("data"), dict) else raw
    if not isinstance(data, dict):
        return []
    profiles = []
    professional_list = data.get("professional_list") or raw.get("professional_list")
    if isinstance(professional_list, list):
        for group in professional_list:
            if not isinstance(group, dict):
                continue
            exec_items = group.get("professionals") or group.get("list") or []
            for item in exec_items:
                if isinstance(item, dict):
                    name = first_value(item, ["name", "name_zhcn", "name_en"])
                    if name:
                        profiles.append(
                            {
                                "name": name,
                                "title": first_value(item, ["title", "duty"]),
                                "biography": strip_html(first_value(item, ["biography", "desc"])),
                            }
                        )
    return profiles[:15]


def extract_shareholders(raw: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parse institutional and principal shareholders."""
    if not raw:
        return []
    items = unwrap_items(raw.get("data"))
    return [
        {
            "name": first_value(item, ["name", "shareholder_name"]),
            "shares": pick_number(item, ["shares", "holding_shares"]),
            "percent": pick_number(item, ["percent", "holding_ratio", "ratio"]),
            "change": pick_number(item, ["change", "holding_change"]),
        }
        for item in items[:15]
        if first_value(item, ["name", "shareholder_name"])
    ]


def extract_insider_trades(raw: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parse insider transactions (Form 4)."""
    if not raw:
        return []
    items = unwrap_items(raw.get("data"))
    return [
        {
            "owner": first_value(item, ["owner", "name"]),
            "type": first_value(item, ["trade_type", "type"]),
            "trade_date": first_value(item, ["trade_date", "date"]),
            "price": pick_number(item, ["price"]),
            "shares": pick_number(item, ["shares"]),
            "value": pick_number(item, ["value"]),
            "shares_after": pick_number(item, ["shares_after"]),
        }
        for item in items[:60]
        if first_value(item, ["owner"])
    ]


def extract_industry_peers(raw: Optional[Dict[str, Any]], symbol: str) -> List[Dict[str, Any]]:
    """Parse sector peers and comparable valuations."""
    if not raw:
        return []
    data = raw.get("data")
    if not isinstance(data, dict):
        return []
    items = data.get("list") if isinstance(data.get("list"), list) else []
    peers = []
    for item in items[:30]:
        if not isinstance(item, dict):
            continue
        counter_id = first_value(item, ["counter_id"])
        peer_symbol = None
        if isinstance(counter_id, str) and counter_id.startswith("ST/"):
            parts = counter_id.split("/")
            if len(parts) == 3:
                peer_symbol = f"{parts[2]}.{parts[1]}"
        peers.append(
            {
                "symbol": peer_symbol or counter_id,
                "name": first_value(item, ["name"]),
                "market": first_value(item, ["market"]),
                "price_close": pick_number(item, ["price_close"]),
                "pe": pick_number(item, ["pe"]),
                "pb": pick_number(item, ["pb"]),
                "ps": pick_number(item, ["ps"]),
                "roe": pick_number(item, ["roe"]),
                "net_margin": pick_number(item, ["net_margin"]),
                "market_value": pick_number(item, ["market_value"]),
                "is_target": (peer_symbol or "").upper() == symbol.upper(),
            }
        )
    return peers


def extract_fund_holders(raw: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parse institutional ETF and fund holders."""
    if not raw:
        return []
    items = unwrap_items(raw.get("data"))
    return [
        {
            "name": first_value(item, ["fund_name", "name"]),
            "symbol": first_value(item, ["symbol", "ticker", "code"]),
            "weight": pick_number(item, ["weight", "position_ratio", "ratio"]),
            "report_date": first_value(item, ["report_date", "date"]),
        }
        for item in items[:20]
        if first_value(item, ["fund_name", "name", "symbol", "ticker"])
    ]


def extract_short_positions(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Parse short interest, settlement date, staleness, and days to cover."""
    if not raw:
        return {"latest": None, "history": []}
    data = raw.get("data")
    if isinstance(data, dict):
        items = data.get("data") if isinstance(data.get("data"), list) else []
    else:
        items = unwrap_items(data)

    now_ts = time.time()
    history = []
    for item in items:
        if not isinstance(item, dict):
            continue
        ts_val = first_value(item, ["timestamp"])
        dt_str = first_value(item, ["date", "settlement_date"])
        is_stale = False
        if ts_val:
            try:
                ts_int = int(ts_val)
                if not dt_str:
                    from datetime import datetime, timezone
                    dt_str = datetime.fromtimestamp(ts_int, tz=timezone.utc).strftime("%Y-%m-%d")
                if (now_ts - ts_int) > 90 * 86400:
                    is_stale = True
            except Exception:
                pass

        history.append(
            {
                "timestamp": ts_val,
                "date": dt_str or "未知",
                "is_stale": is_stale,
                "shares_short": pick_number(item, ["current_shares_short"]),
                "days_to_cover": pick_number(item, ["days_to_cover"]),
                "short_rate": pick_number(item, ["rate"]),
                "avg_daily_volume": pick_number(item, ["avg_daily_share_volume"]),
                "close": pick_number(item, ["close"]),
            }
        )
    latest = history[-1] if history else None
    return {"latest": latest, "history": history[-12:]}


def extract_invest_relations(raw: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parse supply-chain and corporate investment relations."""
    if not raw:
        return []
    data = raw.get("data")
    if not isinstance(data, dict):
        return []
    items = data.get("invest_securities") if isinstance(data.get("invest_securities"), list) else []
    return [
        {
            "name": first_value(item, ["name", "security_name"]),
            "symbol": first_value(item, ["symbol", "ticker", "code"]),
            "relation": first_value(item, ["relation", "type"]),
            "ratio": pick_number(item, ["ratio", "holding_ratio"]),
        }
        for item in items[:20]
    ]


def analyze_related_network(
    symbol: str,
    company: Optional[Dict[str, Any]],
    industry_peers: List[Dict[str, Any]],
    fund_holders: List[Dict[str, Any]],
    invest_relations: List[Dict[str, Any]],
    shareholders: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build peer, supply chain, and fund holder relationship graph."""
    nodes: List[Dict[str, Any]] = []
    watch_triggers: List[str] = []
    target_market = symbol.split(".")[-1]
    target_region = (company or {}).get("market") or target_market

    sorted_peers = sorted(
        [peer for peer in industry_peers if not peer.get("is_target")],
        key=lambda item: item.get("market_value") or 0,
        reverse=True,
    )
    for peer in sorted_peers[:8]:
        strength = 55
        if peer.get("market") == target_region:
            strength += 8
        if peer.get("market_value"):
            strength += 8
        if peer.get("pe") is not None:
            strength += 4
        nodes.append(
            {
                "symbol": peer.get("symbol"),
                "name": peer.get("name"),
                "type": "同行业",
                "region": peer.get("market") or target_region,
                "strength": int(clamp(strength, 0, 100)),
                "reason": "同属长桥行业估值列表，可用于比较估值、盈利能力和市场情绪。",
            }
        )

    for item in invest_relations[:8]:
        nodes.append(
            {
                "symbol": item.get("symbol"),
                "name": item.get("name"),
                "type": item.get("relation") or "投资/产业链",
                "region": target_region,
                "strength": int(clamp(62 + (item.get("ratio") or 0) * 25, 0, 100)),
                "reason": "长桥投资关系数据表明两者可能存在持股、业务或产业链关联。",
            }
        )

    for holder in fund_holders[:8]:
        weight = holder.get("weight") or 0
        nodes.append(
            {
                "symbol": holder.get("symbol"),
                "name": holder.get("name"),
                "type": "基金/ETF 持仓",
                "region": target_region,
                "strength": int(clamp(48 + weight * 4, 0, 100)),
                "reason": "该基金或 ETF 持有目标股票，资金流入流出可能形成联动。",
            }
        )

    if sorted_peers:
        watch_triggers.append("同行业龙头若出现评级或财报超预期变化，目标股估值锚可能同步变化。")
    if fund_holders:
        watch_triggers.append("若主要科技 ETF 出现持续净申赎，可能影响短期成交和资金面。")

    return {
        "industry_peers": industry_peers,
        "fund_holders": fund_holders,
        "invest_relations": invest_relations,
        "network": sorted(nodes, key=lambda item: item.get("strength") or 0, reverse=True)[:24],
        "summary": {
            "node_count": len(nodes),
            "region": target_region,
            "top_watch": watch_triggers[:4],
        },
    }


def build_event_timeline(
    news: List[Dict[str, Any]],
    filings: List[Dict[str, Any]],
    insider_trades: List[Dict[str, Any]],
    controversies: List[Dict[str, Any]],
    rating: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Merge filings, news, and insider events into chronological timeline."""
    events: List[Dict[str, Any]] = []

    for item in filings[:8]:
        title = item.get("title") or item.get("file_name")
        events.append(
            {
                "type": "SEC/公告",
                "time": item.get("publish_at"),
                "title": title,
                "impact": "medium" if title and any(term in title.upper() for term in ("8-K", "10-K", "10-Q")) else "low",
                "source": "SEC/Longbridge",
                "url": (item.get("file_urls") or [None])[0],
                "reason": "官方披露文件，包含治理、风险因素与关键财务数据。",
            }
        )

    for item in insider_trades[:8]:
        trade_type = str(item.get("type") or "交易").upper()
        shares = item.get("shares") or 0
        value = item.get("value")
        val_str = f"${value / 1_000_000:.1f}M" if value else f"{shares:,.0f} 股"
        events.append(
            {
                "type": "内部人交易",
                "time": item.get("trade_date"),
                "title": f"{item.get('owner', '内部人')} {trade_type} {val_str}",
                "impact": "medium" if value and value >= 2_000_000 else "low",
                "source": "Form 4",
                "url": None,
                "reason": "反映核心管理层对公司当前估值和未来预期的直接仓位行为。",
            }
        )

    for item in news[:10]:
        events.append(
            {
                "type": "新闻",
                "time": item.get("published_at"),
                "title": item.get("title"),
                "impact": "low",
                "source": "媒体聚合",
                "url": None,
                "reason": "市场主流媒体公开资讯与舆情动态。",
            }
        )

    return {
        "critical": events[:12],
        "all": events,
    }


def fetch_yahoo_stock_bundle(symbol: str) -> Dict[str, Any]:
    """
    Build complete stock analysis bundle entirely from Yahoo Finance real daily bars + local knowledge base.
    Provides bulletproof resilience when Longbridge broker CLI is unauthenticated or down.
    """
    symbol = normalize_symbol(symbol)
    clean_sym = symbol.replace(".US", "").upper()

    klines = fetch_yahoo_klines(symbol, count=260)
    if not klines:
        raise AppError(f"未能在 Yahoo Finance 查询到标的【{symbol}】行情数据 (Symbol not found)。", 404)

    technical = compute_technical_summary(klines)
    technical["klines"] = klines
    quotes_map = fetch_yahoo_quotes_batch([symbol])
    quote = quotes_map.get(symbol) or quotes_map.get(clean_sym)
    if not quote:
        last_close = klines[-1]["close"]
        prev_close = klines[-2]["close"] if len(klines) > 1 else last_close
        quote = {
            "symbol": symbol,
            "name": clean_sym,
            "last": round(float(last_close), 2),
            "prev_close": round(float(prev_close), 2),
            "open": round(float(klines[-1]["open"]), 2),
            "high": round(float(klines[-1]["high"]), 2),
            "low": round(float(klines[-1]["low"]), 2),
            "volume": klines[-1]["volume"],
            "turnover": round(float(last_close * klines[-1]["volume"]), 2),
            "trade_status": "Normal",
            "change_pct": round((last_close / prev_close - 1) * 100, 2) if prev_close else 0.0,
            "data_status": "YAHOO_FALLBACK",
            "source": "yahoo_finance",
            "fetched_at": utc_now_iso(),
        }

    from backend.services.company_kb import PRESET_PRODUCT_KNOWLEDGE
    from backend.core.stock_registry import get_company_zh_name
    preset = PRESET_PRODUCT_KNOWLEDGE.get(symbol) or PRESET_PRODUCT_KNOWLEDGE.get(clean_sym) or {}
    essence = preset.get("essence") or {}

    company_name = get_company_zh_name(symbol, quote.get("name") or clean_sym)
    company = {
        "name": company_name,
        "company_name": company_name,
        "ticker": clean_sym,
        "market": "US",
        "founded": preset.get("founded", "公开上市企业"),
        "employees": preset.get("employees", None),
        "manager": preset.get("manager") or essence.get("ceo") or "--",
        "website": preset.get("website", ""),
        "profile": preset.get("profile") or f"{clean_sym} 是美股主流核心资产标的，具备良好的二级市场交易流动性与基本面跟踪基础。",
        "address": preset.get("address", "--"),
    }

    # 严格严肃数据准则：长桥离线时，Yahoo 仅提供真实价格与日K，绝不编造虚假 PE/PB/PS、ROE 或目标价
    valuation = None
    rating = None
    financials = None
    financial_quality = {}
    valuation_profile = {}

    risk_analysis = analyze_risk_radar([], [], [], [])
    risk_bundle = {
        "controversies": [],
        "thesis_breakers": [],
        "short_positions": [],
    }

    # 规矩1：没有数就空着，空着的项不进综合分，也不出「值得重点研究」
    score = {
        "score": None,
        "verdict": "数据不足，不能评级",
        "factor_breakdown": None,
        "positives": [
            f"技术面: 20日涨幅 {technical['returns'].get('20d', 0):.1f}%，趋势 {technical.get('trend_label')}",
            f"波动率: ATR(14) ${technical.get('atr14', '--')}，2xATR 止损价 ${technical.get('trailing_stop_2atr', '--')}",
        ],
        "risks": ["长桥官方财务与估值离线，仅取得 Yahoo 价格与日K，未做综合评级"]
    }

    bundle = {
        "symbol": symbol,
        "generated_at": utc_now_iso(),
        "quote": quote,
        "technical": technical,
        "klines": klines,
        "news": [],
        "company": company,
        "valuation": valuation,
        "rating": rating,
        "financials": financials,
        "financial_quality": financial_quality,
        "valuation_profile": valuation_profile,
        "filings": [],
        "timeline": [],
        "related": [],
        "management": {
            "executives": [],
            "shareholders": [],
            "insider_trades": [],
            "insider_summary": {},
            "governance": {}
        },
        "risk_radar": {
            "short_positions": [],
            "controversies": [],
            "analysis": risk_analysis
        },
        "score": score,
        "data_status": "YAHOO_FALLBACK",
        "data_source_badge": "⚠️ 仅行情 (长桥离线)",
        "data_source_note": "注意：长桥 API 未连接或 Token 离线，当前仅取得 Yahoo 真实价格与日K技术指标，估值与财务数据留空，综合分不计算。在终端执行 'longbridge auth login' 后可恢复完整评级。",
        "extra_errors": [{"module": "data_mode", "message": "长桥行情未就绪，仅取得 Yahoo 真实日频行情，缺失官方财务与估值，未做综合评级"}],
        "missing_modules": ["valuation", "rating", "financials"]
    }
    save_analysis(symbol, bundle)
    return bundle


# Backwards compatibility alias
generate_fallback_stock_bundle = fetch_yahoo_stock_bundle


def fetch_stock_bundle(symbol: str, include_ai: bool = False, include_extra: bool = True, minimal_extra: bool = False) -> Dict[str, Any]:
    """Fetch complete stock profile bundle: quote, klines, news, financials, management, risk."""
    symbol = normalize_symbol(symbol)
    specs: Dict[str, Any] = {
        "quote": (["quote", symbol, "--format", "json"], 45, 6),
        "kline": (["kline", symbol, "--period", "day", "--count", "260", "--format", "json"], 3600, 6),
        "news": (["news", symbol, "--count", "20", "--format", "json"], 600, 5),
    }
    if include_extra:
        if minimal_extra:
            specs.update({
                "company": (["company", symbol, "--format", "json"], 86400, 6),
                "valuation": (["valuation", symbol, "--format", "json"], 21600, 6),
                "rating": (["institution-rating", symbol, "--format", "json"], 21600, 5),
                "financials": (["financial-report", symbol, "--latest", "--format", "json"], 86400, 6),
                "executives": (["executive", symbol, "--format", "json"], 86400, 5),
            })
        else:
            specs.update({
                "company": (["company", symbol, "--format", "json"], 86400, 8),
                "valuation": (["valuation", symbol, "--format", "json"], 21600, 8),
                "rating": (["institution-rating", symbol, "--format", "json"], 21600, 8),
                "financials": (["financial-report", symbol, "--latest", "--format", "json"], 86400, 8),
                "filings": (["filing", symbol, "--count", "8", "--format", "json"], 3600, 8),
                "executives": (["executive", symbol, "--format", "json"], 86400, 8),
                "shareholders": (["shareholder", symbol, "--format", "json"], 86400, 8),
                "insider_trades": (["insider-trades", symbol, "--format", "json"], 21600, 5),
                "industry_peers": (["industry-valuation", symbol, "--format", "json"], 21600, 8),
                "fund_holders": (["fund-holder", symbol, "--count", "20", "--format", "json"], 86400, 8),
                "invest_relations": (["invest-relation", symbol, "--format", "json"], 86400, 8),
                "short_positions": (["short-positions", symbol, "--format", "json"], 86400, 8),
            })

    results, all_errors = fetch_longbridge_modules(specs, timeout=8)
    quote_raw = results.get("quote")
    kline_raw = results.get("kline")

    quote_items = unwrap_items(quote_raw.get("data")) if quote_raw else []
    if quote_raw and not quote_items:
        raise AppError(f"标的代码【{symbol}】在美股市场中不存在或未能取得行情 (Symbol not found)。", 404)

    if not quote_raw or not kline_raw:
        existing = latest_analysis_payload(symbol)
        is_rate_limited = any(
            "429" in (e.get("message") or "") or "频控" in (e.get("message") or "")
            for e in all_errors
        )
        if existing:
            existing["data_status"] = "SNAPSHOT"
            if not existing.get("klines"):
                existing["klines"] = fetch_yahoo_klines(symbol, count=260)
            if "technical" in existing and isinstance(existing["technical"], dict) and not existing["technical"].get("klines"):
                existing["technical"]["klines"] = existing.get("klines") or []
            if is_rate_limited:
                existing["data_source_badge"] = "⚠️ 触发频控 (展示历史快照)"
                existing["data_source_note"] = "注意：长桥接口触发频控上限 (429002)，当前展示本地历史快照存档。请等待几秒后重新刷新。"
                existing["extra_errors"] = list(existing.get("extra_errors", [])) + [
                    {"module": "rate_limit", "message": "触发频控 (长桥接口繁忙，请稍后刷新)"}
                ]
            else:
                existing["data_source_badge"] = "🔵 本地历史快照 (长桥离线)"
                existing["data_source_note"] = "注意：长桥凭证离线，当前展示数据库历史快照存档。在终端运行 longbridge auth login 后将自动恢复实时流。"
                existing["extra_errors"] = list(existing.get("extra_errors", [])) + [
                    {"module": "data_mode", "message": "长桥凭证离线，当前展示数据库快照存档（终端运行 longbridge auth login 后将自动恢复实时流）"}
                ]
            return existing
        err_msg = all_errors[0].get("message") if all_errors else "请在终端执行 'longbridge auth login' 登录授权"
        if is_rate_limited:
            raise AppError("触发频控 (长桥接口繁忙，请稍后点击【⚡ 刷新实时行情与量化】重试)", 429)
        if "not found" in err_msg.lower() or "no data" in err_msg.lower():
            raise AppError(f"标的代码【{symbol}】在美股市场中不存在或未能取得行情 (Symbol not found)。", 404)

        # 弹性降级兜底：当长桥离线且本地无快照时，自动拉取真实 Yahoo Finance 历史日K与实时行情生成投研档案
        try:
            fallback_bundle = fetch_yahoo_stock_bundle(symbol)
            if fallback_bundle:
                return fallback_bundle
        except Exception:
            pass

        raise AppError(
            f"长桥行情接口未就绪或未授权（{err_msg}），且备用行情源未连通。请在终端执行 'longbridge auth login'。",
            503
        )

    news_raw = results.get("news")
    news = extract_news(news_raw) if news_raw else []
    quote = extract_quote(quote_raw, symbol)
    klines = extract_klines(kline_raw)
    technical = compute_technical_summary(klines)
    technical["klines"] = klines

    company_raw = results.get("company")
    valuation_raw = results.get("valuation")
    rating_raw = results.get("rating")
    financials_raw = results.get("financials")
    filings_raw = results.get("filings")
    executives_raw = results.get("executives")
    shareholders_raw = results.get("shareholders")
    insider_raw = results.get("insider_trades")
    industry_raw = results.get("industry_peers")
    fund_holders_raw = results.get("fund_holders")
    invest_relations_raw = results.get("invest_relations")
    short_raw = results.get("short_positions")
    extra_errors = list(all_errors)

    company = extract_company(company_raw)
    executives = extract_executives(executives_raw)
    if company and not company.get("manager"):
        for exe in executives:
            t = (exe.get("title") or "").lower()
            if "ceo" in t or "chief executive" in t or "president" in t or "founder" in t:
                company["manager"] = exe.get("name")
                break
        if not company.get("manager") and executives:
            company["manager"] = executives[0].get("name")
    valuation = extract_valuation(valuation_raw)
    rating = extract_rating(rating_raw)
    financials = extract_financials(financials_raw)
    financial_quality = analyze_financial_quality(financials)
    industry_peers = extract_industry_peers(industry_raw, symbol)
    valuation_profile = analyze_valuation_profile(quote, valuation, rating, industry_peers)
    filings = extract_filings(filings_raw)
    shareholders = extract_shareholders(shareholders_raw)
    insider_trades = extract_insider_trades(insider_raw)
    insider_summary = summarize_insider_trades(insider_trades)
    fund_holders = extract_fund_holders(fund_holders_raw)
    invest_relations = extract_invest_relations(invest_relations_raw)
    short_positions = extract_short_positions(short_raw)
    governance = analyze_management_governance(executives, shareholders, insider_trades, insider_summary)
    risk_analysis = analyze_risk_radar(short_positions, [], filings, news)
    related = analyze_related_network(symbol, company, industry_peers, fund_holders, invest_relations, shareholders)
    timeline = build_event_timeline(news, filings, insider_trades, [], rating)
    risk_bundle = {
        "controversies": [],
        "thesis_breakers": risk_analysis.get("thesis_breakers", []),
        "short_positions": short_positions,
    }

    # 读取当前活跃宏观动态因子权重与风险系数，确保单股 360、横向对比与选股漏斗计算基准完全一致
    from backend.services.macro_service import get_active_factor_config
    active_weights, risk_multiplier = get_active_factor_config()

    factor_breakdown = build_factor_breakdown(
        quote, technical, news, valuation, rating, financials, risk_bundle,
        regime_weights=active_weights,
        risk_multiplier=risk_multiplier
    )
    final_score = factor_breakdown.get("composite")
    if final_score is None:
        verdict = "数据不足，不能评级"
    else:
        verdict = "值得重点研究" if final_score >= 75 else ("可加入观察" if final_score >= 60 else "中性观察")

    score = {
        "score": final_score,
        "verdict": verdict,
        "factor_breakdown": factor_breakdown,
        "positives": [
            f"技术面: 20日涨幅 {technical['returns'].get('20d', 0):.1f}%，趋势 {technical.get('trend_label')}",
            f"估值: PE {valuation.get('pe', '-') if valuation else '-'}，行业中位 {valuation.get('industry_median', '-') if valuation else '-'}",
        ],
        "risks": risk_analysis["key_risks"]
    }

    result = {
        "symbol": symbol,
        "generated_at": utc_now_iso(),
        "quote": quote,
        "technical": technical,
        "klines": klines,
        "news": news,
        "company": company,
        "valuation": valuation,
        "rating": rating,
        "financials": financials,
        "financial_quality": financial_quality,
        "valuation_profile": valuation_profile,
        "filings": filings,
        "timeline": timeline,
        "related": related,
        "management": {
            "executives": executives,
            "shareholders": shareholders,
            "insider_trades": insider_trades,
            "insider_summary": insider_summary,
            "governance": governance
        },
        "risk_radar": {
            "short_positions": short_positions,
            "controversies": [],
            "analysis": risk_analysis
        },
        "score": score,
        "data_status": "LIVE",
        "data_source_badge": "🟢 长桥实时行情",
        "extra_errors": extra_errors,
        "missing_modules": [e.get("module") for e in extra_errors if e.get("module")]
    }
    # 评级、行情、K线任一失败，杜绝缓存残缺快照，保证下次请求发起真实重试
    has_critical_error = any(e.get("module") in ("rating", "quote", "financials", "kline") for e in extra_errors)
    if not has_critical_error:
        save_analysis(symbol, result)
    return result


def export_markdown_report(symbol: str) -> Dict[str, Any]:
    """Export research report to markdown file."""
    symbol = normalize_symbol(symbol)
    payload = latest_analysis_payload(symbol)
    if not payload:
        payload = fetch_stock_bundle(symbol, include_ai=False, include_extra=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = REPORTS_DIR / f"{symbol.replace('.', '-')}-{timestamp}.md"
    
    quote = payload.get("quote") or {}
    score = payload.get("score") or {}
    score_val = score.get("score")
    score_display = f"{score_val} / 100 ({score.get('verdict', '未评级')})" if score_val is not None else "数据不足，未评级"

    content = f"""# {symbol} 本地投研简报

- 生成时间: {payload.get('generated_at', utc_now_iso())}
- 最新价: {quote.get('last', '--')}
- 涨跌幅: {quote.get('change_pct', '--')}%
- 综合评分: {score_display}

## 因子归因
"""
    fb = score.get("factor_breakdown") or {}
    factors = fb.get("factors") or []
    if factors:
        for f in factors:
            evidence = f.get('evidence') or []
            ev_str = ' / '.join(str(e) for e in evidence) if evidence else "无额外佐证"
            content += f"- **{f.get('name', '因子')}** ({f.get('score', 0)}分): {ev_str}\n"
    else:
        content += "- *当前模式下无量化因子明细（长桥官方财务离线或数据不足，遵循不伪造数据原则未生成因子细项）*\n"
    
    path.write_text(content, encoding="utf-8")
    return {
        "ok": True,
        "symbol": symbol,
        "path": str(path),
        "filename": path.name,
        "content": content,
        "generated_at": utc_now_iso()
    }
