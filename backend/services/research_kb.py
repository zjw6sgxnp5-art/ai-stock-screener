"""
Research Knowledge Base Service:
Imports and indexes:
1. Benchmark Database (美股研究_数据库最新版):
   - 00_最新评级总表.xlsx (518 stocks: S&P 500 503 + Nasdaq 100 non-SP 15)
   - 518 Markdown in-depth stock research reports in 个股报告/
2. User SP500 Research (标普500研究):
   - 标普500全量成分股结构化数据_506只标的.json (506 entries / 473 unique tickers)
Provides unified query APIs, tab data switching, and Markdown report rendering.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3
import threading
from typing import Any, Dict, List, Optional, Tuple

from backend.config import BASE_DIR, DB_PATH
from backend.core.utils import normalize_symbol

_SECTOR_CN_MAP = {
    "Communication Services": "通信服务",
    "Consumer Cyclical": "可选消费",
    "Consumer Defensive": "必需消费",
    "Healthcare": "医疗保健",
    "Industrials": "工业",
    "Technology": "信息技术",
}

REF_DIR = BASE_DIR / "【1】参考资料"
V4_EXCEL = REF_DIR / "美股研究_数据库最新版" / "00_最新评级总表.xlsx"
V4_REPORTS_DIR = REF_DIR / "美股研究_数据库最新版" / "个股报告"
USER_JSON = REF_DIR / "标普500研究" / "标普500全量成分股结构化数据_506只标的.json"

_KB_LOCK = threading.RLock()


@contextmanager
def get_kb_db():
    """Context manager to ensure SQLite connection is closed cleanly."""
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def clean_ticker(symbol_or_ticker: str) -> str:
    """Normalize input into an uppercase clean ticker like 'AAPL'."""
    s = (symbol_or_ticker or "").strip().upper()
    if s.endswith(".US") or s.endswith(".HK") or s.endswith(".SH") or s.endswith(".SZ"):
        s = s.split(".")[0]
    return s


def normalize_sector(sector: Optional[str]) -> str:
    """Normalize sector string into standard Chinese classification."""
    if not sector:
        return "综合行业"
    sec = sector.strip()
    return _SECTOR_CN_MAP.get(sec, sec)


def ensure_research_tables() -> None:
    """
    Ensure SQLite tables exist and automatically populate from Excel/JSON if missing or outdated.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _KB_LOCK:
        with get_kb_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS research_benchmark (
                    symbol TEXT PRIMARY KEY,
                    ticker TEXT NOT NULL,
                    name_cn TEXT,
                    name_en TEXT,
                    sector TEXT,
                    sub_industry TEXT,
                    index_code TEXT,
                    price REAL,
                    target_price REAL,
                    target_upside REAL,
                    rating TEXT,
                    analyst_rating TEXT,
                    total_score REAL,
                    score_moat REAL,
                    score_growth REAL,
                    score_financial REAL,
                    score_return REAL,
                    score_valuation REAL,
                    score_catalyst REAL,
                    ttm_pe REAL,
                    fwd_pe REAL,
                    fcf_yield REAL,
                    rev_growth REAL,
                    eps_growth REAL,
                    market_cap_b REAL,
                    conclusion TEXT,
                    action_plan TEXT,
                    last_earnings TEXT,
                    next_earnings TEXT,
                    as_of_date TEXT,
                    analyzed_at TEXT,
                    trigger_type TEXT,
                    has_report INTEGER DEFAULT 0
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bench_ticker ON research_benchmark(ticker)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bench_sector ON research_benchmark(sector)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bench_rating ON research_benchmark(rating)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bench_index ON research_benchmark(index_code)")

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS research_sp500_user (
                    id INTEGER PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    company_name TEXT,
                    sector TEXT,
                    round TEXT,
                    rating TEXT,
                    price REAL,
                    valuation_pe TEXT,
                    moat_and_momentum TEXT,
                    risks_and_mispricing TEXT,
                    action_plan TEXT,
                    invalidation_trigger TEXT,
                    updated_date TEXT
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_ticker ON research_sp500_user(ticker)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_symbol ON research_sp500_user(symbol)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_rating ON research_sp500_user(rating)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_sector ON research_sp500_user(sector)")

            # Check if populated
            bench_count = cursor.execute("SELECT COUNT(*) FROM research_benchmark").fetchone()[0]
            user_count = cursor.execute("SELECT COUNT(*) FROM research_sp500_user").fetchone()[0]

            need_import_bench = (bench_count < 518) and V4_EXCEL.exists()
            need_import_user = (user_count < 506) and USER_JSON.exists()

            if need_import_bench:
                _import_benchmark_excel(cursor)
                conn.commit()

            if need_import_user:
                _import_user_json(cursor)
                conn.commit()


def _import_benchmark_excel(cursor: sqlite3.Cursor) -> None:
    """Parse 00_最新评级总表.xlsx and load into research_benchmark."""
    try:
        import openpyxl
    except ImportError:
        print("[ResearchKB] openpyxl not installed, skipping Excel import.")
        return

    if not V4_EXCEL.exists():
        return

    print(f"[ResearchKB] Importing benchmark research from {V4_EXCEL}...")
    wb = openpyxl.load_workbook(V4_EXCEL, data_only=True)
    ws = wb.active
    headers = [cell.value for cell in ws[1]]
    h_map = {h: i for i, h in enumerate(headers)}

    report_files = set(f.stem.upper() for f in V4_REPORTS_DIR.glob("*.md")) if V4_REPORTS_DIR.exists() else set()

    rows = []
    for r in list(ws.iter_rows(values_only=True))[1:]:
        raw_ticker = r[h_map.get("symbol")]
        if not raw_ticker:
            continue
        ticker = str(raw_ticker).strip().upper()
        symbol = f"{ticker}.US"
        has_report = 1 if ticker in report_files else 0

        target_upside = r[h_map.get("target_upside")]
        if target_upside is not None:
            try:
                target_upside = round(float(target_upside), 4)
            except (ValueError, TypeError):
                target_upside = None

        total_score = r[h_map.get("total_score")]
        if total_score is not None:
            try:
                total_score = round(float(total_score), 1)
            except (ValueError, TypeError):
                total_score = None

        rows.append((
            symbol,
            ticker,
            r[h_map.get("name_cn")],
            r[h_map.get("name_en")],
            normalize_sector(r[h_map.get("sector")]),
            r[h_map.get("sub_industry")],
            r[h_map.get("index_code")],
            r[h_map.get("price")],
            r[h_map.get("target_price")],
            target_upside,
            r[h_map.get("rating")],
            r[h_map.get("analyst_rating")],
            total_score,
            r[h_map.get("score_moat")],
            r[h_map.get("score_growth")],
            r[h_map.get("score_financial")],
            r[h_map.get("score_return")],
            r[h_map.get("score_valuation")],
            r[h_map.get("score_catalyst")],
            r[h_map.get("ttm_pe")],
            r[h_map.get("fwd_pe")],
            r[h_map.get("fcf_yield")],
            r[h_map.get("rev_growth")],
            r[h_map.get("eps_growth")],
            r[h_map.get("market_cap_b")],
            r[h_map.get("conclusion")],
            r[h_map.get("action_plan")],
            str(r[h_map.get("last_earnings")]) if r[h_map.get("last_earnings")] else None,
            str(r[h_map.get("next_earnings")]) if r[h_map.get("next_earnings")] else None,
            str(r[h_map.get("as_of_date")]) if r[h_map.get("as_of_date")] else None,
            str(r[h_map.get("analyzed_at")]) if r[h_map.get("analyzed_at")] else None,
            r[h_map.get("trigger_type")],
            has_report,
        ))

    cursor.execute("DELETE FROM research_benchmark")
    cursor.executemany(
        """
        INSERT OR REPLACE INTO research_benchmark (
            symbol, ticker, name_cn, name_en, sector, sub_industry, index_code,
            price, target_price, target_upside, rating, analyst_rating, total_score,
            score_moat, score_growth, score_financial, score_return, score_valuation, score_catalyst,
            ttm_pe, fwd_pe, fcf_yield, rev_growth, eps_growth, market_cap_b,
            conclusion, action_plan, last_earnings, next_earnings, as_of_date, analyzed_at,
            trigger_type, has_report
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?
        )
        """,
        rows,
    )
    print(f"[ResearchKB] Successfully imported {len(rows)} benchmark records.")


def _import_user_json(cursor: sqlite3.Cursor) -> None:
    """Parse 标普500全量成分股结构化数据_506只标的.json and load into research_sp500_user."""
    if not USER_JSON.exists():
        return

    print(f"[ResearchKB] Importing user SP500 research from {USER_JSON}...")
    with open(USER_JSON, "r", encoding="utf-8") as f:
        items = json.load(f)

    rows = []
    for it in items:
        raw_ticker = it.get("ticker", "")
        if not raw_ticker:
            continue
        ticker = str(raw_ticker).strip().upper()
        symbol = f"{ticker}.US"
        price_val = None
        if it.get("price") is not None:
            try:
                price_val = round(float(it["price"]), 2)
            except (ValueError, TypeError):
                price_val = None

        rows.append((
            int(it.get("id")),
            symbol,
            ticker,
            it.get("company_name"),
            it.get("sector"),
            it.get("round"),
            it.get("rating"),
            price_val,
            it.get("valuation_pe"),
            it.get("moat_and_momentum"),
            it.get("risks_and_mispricing"),
            it.get("action_plan"),
            it.get("invalidation_trigger"),
            str(it.get("updated_date")),
        ))

    cursor.execute("DELETE FROM research_sp500_user")
    cursor.executemany(
        """
        INSERT OR REPLACE INTO research_sp500_user (
            id, symbol, ticker, company_name, sector, round, rating, price,
            valuation_pe, moat_and_momentum, risks_and_mispricing, action_plan,
            invalidation_trigger, updated_date
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?
        )
        """,
        rows,
    )
    print(f"[ResearchKB] Successfully imported {len(rows)} user SP500 records.")


def query_research_list(
    source: str = "benchmark",
    query: str = "",
    sector: str = "",
    rating: str = "",
    sort_by: str = "",
    order: str = "desc",
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    Unified query for Research tab views.
    source='benchmark': 518 stocks (S&P 500 + NDX 100)
    source='user': 506 S&P 500 user equity research entries
    """
    ensure_research_tables()
    is_user = (source == "user")
    table = "research_sp500_user" if is_user else "research_benchmark"

    conds: List[str] = []
    params: List[Any] = []

    if query:
        q = f"%{query.strip().upper()}%"
        q_raw = f"%{query.strip()}%"
        if is_user:
            conds.append("(ticker LIKE ? OR symbol LIKE ? OR company_name LIKE ? OR sector LIKE ?)")
            params.extend([q, q, q_raw, q_raw])
        else:
            conds.append("(ticker LIKE ? OR symbol LIKE ? OR name_cn LIKE ? OR name_en LIKE ? OR sector LIKE ?)")
            params.extend([q, q, q_raw, q_raw, q_raw])

    if sector and sector != "全部行业":
        conds.append("sector LIKE ?")
        params.append(f"%{sector.strip()}%")

    if rating and rating != "全部评级":
        conds.append("rating = ?")
        params.append(rating.strip())

    where_clause = f"WHERE {' AND '.join(conds)}" if conds else ""

    # Sort validation
    order_clause = "DESC" if str(order).lower() == "desc" else "ASC"
    if is_user:
        allowed_sorts = {
            "id": "id",
            "price": "price",
            "rating": "rating",
            "ticker": "ticker",
            "round": "id",
        }
        sort_col = allowed_sorts.get(sort_by, "id")
    else:
        allowed_sorts = {
            "total_score": "total_score",
            "target_upside": "target_upside",
            "price": "price",
            "target_price": "target_price",
            "market_cap_b": "market_cap_b",
            "fwd_pe": "fwd_pe",
            "ttm_pe": "ttm_pe",
            "rev_growth": "rev_growth",
            "ticker": "ticker",
        }
        sort_col = allowed_sorts.get(sort_by, "total_score")

    sql_list = f"""
        SELECT * FROM {table}
        {where_clause}
        ORDER BY {sort_col} {order_clause} NULLS LAST
        LIMIT ? OFFSET ?
    """
    sql_count = f"SELECT COUNT(*) FROM {table} {where_clause}"

    with _KB_LOCK:
        with get_kb_db() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            total_records = cursor.execute(sql_count, params).fetchone()[0]
            rows = cursor.execute(sql_list, params + [limit, offset]).fetchall()
            items = [dict(r) for r in rows]

            # Collect summary stats for header badges
            all_sectors = [
                r[0] for r in cursor.execute(f"SELECT DISTINCT sector FROM {table} WHERE sector IS NOT NULL AND sector != ''").fetchall()
            ]
            rating_counts = {}
            for r in cursor.execute(f"SELECT rating, COUNT(*) FROM {table} WHERE rating IS NOT NULL AND rating != '' GROUP BY rating").fetchall():
                rating_counts[r[0]] = r[1]
            all_ratings = list(rating_counts.keys())

    total_pages = max(1, (total_records + limit - 1) // limit) if limit > 0 else 1
    current_page = (offset // limit) + 1 if limit > 0 else 1

    return {
        "ok": True,
        "source": source,
        "total": total_records,
        "limit": limit,
        "offset": offset,
        "page": current_page,
        "page_size": limit,
        "total_pages": total_pages,
        "items": items,
        "sectors": sorted([s for s in all_sectors if s]),
        "available_sectors": sorted([s for s in all_sectors if s]),
        "ratings": sorted([r for r in all_ratings if r]),
        "available_ratings": sorted([r for r in all_ratings if r]),
        "rating_counts": rating_counts,
    }


def get_stock_research_detail(symbol_or_ticker: str) -> Dict[str, Any]:
    """
    Retrieve research profile from both datasets for Perspective A/B comparison.
    Handles the 15 NDX non-SP stocks gracefully by marking user research unavailable.
    """
    ensure_research_tables()
    ticker = clean_ticker(symbol_or_ticker)
    symbol = f"{ticker}.US"

    bench_item = None
    user_item = None

    with _KB_LOCK:
        with get_kb_db() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Benchmark row
            r_bench = cursor.execute(
                "SELECT * FROM research_benchmark WHERE ticker = ? OR symbol = ?",
                (ticker, symbol),
            ).fetchone()
            if r_bench:
                bench_item = dict(r_bench)

            # User row (latest review by id DESC)
            r_user = cursor.execute(
                "SELECT * FROM research_sp500_user WHERE ticker = ? OR symbol = ? ORDER BY id DESC LIMIT 1",
                (ticker, symbol),
            ).fetchone()
            if r_user:
                user_item = dict(r_user)

    has_bench = bench_item is not None
    has_user = user_item is not None

    user_unavailable_reason = None
    if not has_user:
        if bench_item and bench_item.get("index_code") == "NDX100_EX_SP":
            user_unavailable_reason = "该标的属于纳指100非标普成分股，本库仅收录标普500"
        else:
            user_unavailable_reason = "标普500避雷库暂未收录该标的"

    has_report = False
    if V4_REPORTS_DIR.exists():
        report_path = V4_REPORTS_DIR / f"{ticker}.md"
        has_report = report_path.exists()

    return {
        "ok": True,
        "ticker": ticker,
        "symbol": symbol,
        "has_benchmark": has_bench,
        "has_user": has_user,
        "benchmark": bench_item,
        "user": user_item,
        "user_unavailable_reason": user_unavailable_reason,
        "user_disabled_reason": user_unavailable_reason,
        "has_report": has_report,
    }


def get_stock_markdown_report(symbol_or_ticker: str) -> Dict[str, Any]:
    """Retrieve full text of 个股报告/{ticker}.md."""
    ticker = clean_ticker(symbol_or_ticker)
    symbol = f"{ticker}.US"

    if not V4_REPORTS_DIR.exists():
        return {
            "ok": False,
            "error": "报告文件夹未找到。",
            "symbol": symbol,
            "ticker": ticker,
        }

    report_path = V4_REPORTS_DIR / f"{ticker}.md"
    if not report_path.exists():
        return {
            "ok": False,
            "error": f"未找到标的【{ticker}】的对应个股分析报告。",
            "symbol": symbol,
            "ticker": ticker,
        }

    try:
        content = report_path.read_text(encoding="utf-8")
        bench_info = get_stock_research_detail(ticker).get("benchmark")
        return {
            "ok": True,
            "symbol": symbol,
            "ticker": ticker,
            "content": content,
            "report_content": content,
            "file_name": f"{ticker}.md",
            "benchmark": bench_info,
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": f"读取报告异常：{exc}",
            "symbol": symbol,
            "ticker": ticker,
        }


def get_all_benchmark_stocks() -> List[Dict[str, Any]]:
    """
    Retrieve all 518 benchmark universe stocks for universal top nav search and registry.
    """
    ensure_research_tables()
    with _KB_LOCK:
        with get_kb_db() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            rows = cursor.execute(
                """
                SELECT symbol, ticker, name_cn, name_en, sector, sub_industry,
                       index_code, rating, total_score, target_upside, price
                FROM research_benchmark
                ORDER BY total_score DESC, ticker ASC
                """
            ).fetchall()
            return [dict(r) for r in rows]
