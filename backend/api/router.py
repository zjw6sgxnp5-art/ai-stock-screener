"""
HTTP Request Dispatcher and REST API Router.
Built with Python standard library ThreadingHTTPServer for zero-dependency high concurrency.
"""
import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from backend.config import AppError, STATIC_DIR
from backend.core.utils import number_from, parse_symbol_list, utc_now_iso
from backend.db import (
    add_watchlist_symbol,
    archive_recommendation_snapshot,
    delete_dossier,
    get_review_snapshots,
    list_dossier_history,
    list_watchlist,
    recent_analysis_runs,
    remove_watchlist_symbol,
)
from backend.services.ai_engine import check_ai_models_status, run_cli_analysis_for_symbol
from backend.services.dossier_service import (
    get_or_create_dossier,
    hot_sync_price_and_technicals,
    refresh_dossier_module,
)
from backend.services.auto_evolution import get_autonomous_status, run_full_autonomous_cycle
from backend.services.backtester import run_quantitative_backtest, run_sensitivity_analysis
from backend.services.macro_service import get_macro_climate
from backend.services.market_data import (
    export_markdown_report,
    fetch_stock_bundle,
    longbridge_status,
)
from backend.services.portfolio_allocator import calculate_portfolio_allocation, inspect_existing_holdings
from backend.services.screener import (
    get_daily_screener_recommendations,
    get_screener_progress,
    run_compare,
    run_screener,
)
from backend.services.tech_radar import get_tech_catalysts


def json_response(handler: BaseHTTPRequestHandler, payload: Any, status: int = 200) -> None:
    """Send JSON response with UTF-8 encoding."""
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


def text_response(handler: BaseHTTPRequestHandler, body: bytes, content_type: str, status: int = 200) -> None:
    """Send raw text/binary response."""
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


def content_type_for(path: Path) -> str:
    """Determine MIME content type by file extension."""
    suffix = path.suffix.lower()
    if suffix == ".html":
        return "text/html; charset=utf-8"
    if suffix == ".css":
        return "text/css; charset=utf-8"
    if suffix == ".js":
        return "application/javascript; charset=utf-8"
    if suffix == ".svg":
        return "image/svg+xml"
    if suffix in (".png", ".jpg", ".jpeg"):
        return f"image/{suffix.lstrip('.')}"
    return "application/octet-stream"


class RequestHandler(BaseHTTPRequestHandler):
    """Institutional-grade HTTP Request Handler."""
    server_version = "AIStockTerminal/2.0"

    def do_OPTIONS(self) -> None:
        """Handle CORS pre-flight requests."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        """Handle GET requests."""
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/health":
                json_response(
                    self,
                    {
                        "ok": True,
                        "app": "AI 选股 · 机构级智能投研工作台",
                        "time": utc_now_iso(),
                        "status": "ready"
                    },
                )
                return
            if parsed.path == "/api/datasources/longbridge/status":
                json_response(self, longbridge_status())
                return
            if parsed.path in ("/api/macro", "/api/macro/climate"):
                json_response(self, {"ok": True, "macro": get_macro_climate()})
                return
            if parsed.path == "/api/universe/stocks":
                from backend.core.stock_registry import get_all_registered_stocks
                json_response(self, {"ok": True, "stocks": get_all_registered_stocks()})
                return
            if parsed.path == "/api/research/list":
                from backend.services.research_kb import query_research_list
                params = parse_qs(parsed.query)
                source = params.get("source", ["benchmark"])[0]
                query = params.get("query", [""])[0]
                sector = params.get("sector", [""])[0]
                rating = params.get("rating", [""])[0]
                sort_by = params.get("sort_by", [""])[0]
                order = params.get("order", ["desc"])[0]
                
                # Support both limit/offset and page/page_size pagination
                page = int(params.get("page", ["1"])[0] or 1)
                page_size = int(params.get("page_size", ["0"])[0] or 0)
                if page_size > 0:
                    limit = max(1, min(page_size, 600))
                    offset = max(0, (page - 1) * limit)
                else:
                    limit = int(params.get("limit", ["50"])[0] or 50)
                    offset = int(params.get("offset", ["0"])[0] or 0)

                json_response(self, query_research_list(
                    source=source,
                    query=query,
                    sector=sector,
                    rating=rating,
                    sort_by=sort_by,
                    order=order,
                    limit=max(1, min(limit, 600)),
                    offset=max(0, offset),
                ))
                return
            if parsed.path == "/api/research/detail":
                from backend.services.research_kb import get_stock_research_detail
                params = parse_qs(parsed.query)
                symbol = params.get("symbol", ["AAPL"])[0]
                json_response(self, get_stock_research_detail(symbol))
                return
            if parsed.path == "/api/research/report":
                from backend.services.research_kb import get_stock_markdown_report
                params = parse_qs(parsed.query)
                symbol = params.get("symbol", ["AAPL"])[0]
                json_response(self, get_stock_markdown_report(symbol))
                return
            if parsed.path == "/api/tech/catalysts":
                json_response(self, {
                    "ok": True,
                    "status": "disabled",
                    "note": "催化雷达按设计停用（无合规数据源接入，拒绝提供虚假事件）",
                    "tech": []
                })
                return
            if parsed.path == "/api/screener/progress":
                json_response(self, {"ok": True, "progress": get_screener_progress()})
                return
            if parsed.path == "/api/screener/daily":
                params = parse_qs(parsed.query)
                force = params.get("force", ["0"])[0] in ("1", "true", "yes")
                json_response(self, {"ok": True, "screener": get_daily_screener_recommendations(force=force)})
                return
            if parsed.path == "/api/ai/models":
                json_response(self, {"ok": True, "models": check_ai_models_status()})
                return
            if parsed.path == "/api/records/review":
                json_response(self, {"ok": True, "records": get_review_snapshots()})
                return
            if parsed.path == "/api/watchlist":
                json_response(self, {"ok": True, "watchlist": list_watchlist()})
                return
            if parsed.path == "/api/history":
                params = parse_qs(parsed.query)
                limit = int(params.get("limit", ["12"])[0] or 12)
                json_response(self, {"ok": True, "runs": recent_analysis_runs(limit)})
                return
            if parsed.path == "/api/dossier":
                params = parse_qs(parsed.query)
                symbol = params.get("symbol", ["NVDA.US"])[0]
                force = params.get("force", ["0"])[0] in ("1", "true", "yes")
                json_response(self, {"ok": True, "dossier": get_or_create_dossier(symbol, force_refresh=force)})
                return
            if parsed.path == "/api/dossiers/history":
                json_response(self, {"ok": True, "history": list_dossier_history()})
                return
            if parsed.path == "/api/analyze":
                params = parse_qs(parsed.query)
                symbol = params.get("symbol", ["NVDA.US"])[0]
                include_extra = params.get("extra", ["1"])[0] not in ("0", "false", "no")
                json_response(self, fetch_stock_bundle(symbol, include_ai=False, include_extra=include_extra))
                return
            if parsed.path == "/api/screener/run":
                params = parse_qs(parsed.query)
                universe = params.get("universe", ["custom"])[0]
                default_symbols = [item["symbol"] for item in list_watchlist()] if universe == "watchlist" else None
                symbols = parse_symbol_list(params.get("symbols", [""])[0], default=default_symbols)
                limit = int(params.get("limit", ["10"])[0] or 10)
                res = run_screener(symbols, limit=max(1, min(limit, 30)))
                if isinstance(res, dict) and "ok" not in res:
                    res["ok"] = True
                json_response(self, res)
                return
            if parsed.path == "/api/compare":
                params = parse_qs(parsed.query)
                symbols = parse_symbol_list(params.get("symbols", [""])[0], max_count=5)
                res = run_compare(symbols)
                if isinstance(res, dict) and "ok" not in res:
                    res["ok"] = True
                json_response(self, res)
                return
            if parsed.path == "/api/report/export":
                params = parse_qs(parsed.query)
                symbol = params.get("symbol", [""])[0]
                json_response(self, export_markdown_report(symbol))
                return
            if parsed.path == "/api/backtest/run":
                params = parse_qs(parsed.query)
                range_str = params.get("range", ["2y"])[0]
                rebal_freq = int(params.get("rebalance_freq", ["15"])[0] or 15)
                top_n = int(params.get("top_n", ["3"])[0] or 3)
                atr_mult = float(params.get("atr_mult", ["2.5"])[0] or 2.5)
                force = params.get("force", ["0"])[0] in ("1", "true", "yes")
                json_response(self, run_quantitative_backtest(
                    range_str=range_str,
                    rebalance_freq=rebal_freq,
                    top_n=top_n,
                    atr_mult=atr_mult,
                    force_refresh=force
                ))
                return
            if parsed.path == "/api/backtest/sensitivity":
                params = parse_qs(parsed.query)
                range_str = params.get("range", ["2y"])[0]
                top_n = int(params.get("top_n", ["2"])[0] or 2)
                force = params.get("force", ["0"])[0] in ("1", "true", "yes")
                json_response(self, run_sensitivity_analysis(
                    range_str=range_str,
                    top_n=top_n,
                    force_refresh=force
                ))
                return
            if parsed.path == "/api/evolution/status":
                json_response(self, get_autonomous_status())
                return

            self.serve_static(parsed.path)
        except AppError as exc:
            json_response(self, {"ok": False, "error": exc.message, "details": exc.details}, exc.status)
        except Exception as exc:
            json_response(self, {"ok": False, "error": f"服务器异常：{exc}"}, 500)

    def do_POST(self) -> None:
        """Handle POST requests."""
        parsed = urlparse(self.path)
        try:
            length = int(self.headers.get("Content-Length", "0") or 0)
            raw = self.rfile.read(length).decode("utf-8") if length else "{}"
            try:
                body = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                raise AppError("请求体 JSON 格式异常。", 400)

            if parsed.path == "/api/dossier/refresh-module":
                symbol = body.get("symbol", "NVDA.US")
                module_name = body.get("module", "core_products")
                json_response(self, refresh_dossier_module(symbol, module_name))
                return
            if parsed.path == "/api/dossier/sync-price":
                symbol = body.get("symbol", "NVDA.US")
                json_response(self, hot_sync_price_and_technicals(symbol))
                return
            if parsed.path == "/api/dossiers/delete":
                symbol = body.get("symbol", "")
                json_response(self, {"ok": True, "deleted": delete_dossier(symbol)})
                return
            if parsed.path == "/api/analyze/cli":
                symbol = body.get("symbol", "NVDA.US")
                model = body.get("model", "gemini")
                json_response(self, run_cli_analysis_for_symbol(symbol, model_name=model))
                return
            if parsed.path == "/api/evolution/run_cycle":
                json_response(self, run_full_autonomous_cycle())
                return
            if parsed.path == "/api/portfolio/calculate":
                candidates = body.get("candidates")
                if not candidates:
                    daily = get_daily_screener_recommendations()
                    candidates = daily.get("picks", [])
                total_capital = number_from(body.get("total_capital")) or 100000.0
                risk_pct = number_from(body.get("risk_per_trade_pct")) or 1.5
                sector_cap = number_from(body.get("max_sector_exposure_pct")) or 30.0
                single_stock_cap = number_from(body.get("max_single_stock_pct")) or 25.0
                macro_limit = number_from(body.get("macro_exposure_limit_pct")) or 85.0
                plan = calculate_portfolio_allocation(
                    candidates=candidates,
                    total_capital=total_capital,
                    risk_per_trade_pct=risk_pct,
                    max_sector_exposure_pct=sector_cap,
                    max_single_stock_pct=single_stock_cap,
                    macro_exposure_limit_pct=macro_limit
                )
                json_response(self, {"ok": True, "portfolio": plan})
                return
            if parsed.path == "/api/portfolio/inspect":
                holdings = body.get("holdings", [])
                max_sector = number_from(body.get("max_sector_exposure_pct")) or 30.0
                json_response(self, inspect_existing_holdings(holdings, max_sector_exposure_pct=max_sector))
                return
            if parsed.path == "/api/records/archive":
                snapshot = archive_recommendation_snapshot(
                    symbol=body.get("symbol", ""),
                    source_type=body.get("source_type", "manual"),
                    price=number_from(body.get("price")),
                    spy_price=number_from(body.get("spy_price")),
                    vix_value=number_from(body.get("vix_value")),
                    score=number_from(body.get("score")),
                    verdict=body.get("verdict", ""),
                    tags=body.get("tags", []),
                    short_term_thesis=body.get("short_term_thesis", ""),
                    mid_term_thesis=body.get("mid_term_thesis", ""),
                    long_term_thesis=body.get("long_term_thesis", ""),
                    stop_loss_price=number_from(body.get("stop_loss_price")),
                    target_price=number_from(body.get("target_price")),
                    ai_model=body.get("ai_model", "CLI"),
                    evidence_json=json.dumps(body.get("evidence", {}), ensure_ascii=False)
                )
                json_response(self, snapshot)
                return
            if parsed.path == "/api/watchlist/add":
                json_response(
                    self,
                    add_watchlist_symbol(
                        body.get("symbol", ""),
                        group_name=body.get("group", "默认"),
                        note=body.get("note", ""),
                    ),
                )
                return
            if parsed.path == "/api/watchlist/remove":
                json_response(self, remove_watchlist_symbol(body.get("symbol", "")))
                return

            raise AppError("未知接口路径。", 404)
        except AppError as exc:
            json_response(self, {"ok": False, "error": exc.message, "details": exc.details}, exc.status)
        except Exception as exc:
            json_response(self, {"ok": False, "error": f"服务器异常：{exc}"}, 500)

    def serve_static(self, request_path: str) -> None:
        """Serve static assets from web/ directory."""
        if request_path.startswith("/api/"):
            raise AppError("未知接口路径。", 404)
        if request_path == "/":
            request_path = "/index.html"
        safe_parts = [part for part in request_path.split("/") if part and part not in (".", "..")]
        path = STATIC_DIR.joinpath(*safe_parts)
        if not path.exists() or not path.is_file():
            path = STATIC_DIR / "index.html"
        text_response(self, path.read_bytes(), content_type_for(path))

    def log_message(self, fmt: str, *args: Any) -> None:
        """Format server access log messages."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {self.address_string()} {fmt % args}")
