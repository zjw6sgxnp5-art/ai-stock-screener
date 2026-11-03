"""
Database layer for SQLite storage, caching, watchlists, analysis history, and recommendation snapshots.
"""
from contextlib import contextmanager
import json
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional

from backend.config import DB_PATH, AppError
from backend.core.utils import number_from, utc_now_iso

DB_LOCK = threading.RLock()
_INITIALIZED_DBS = set()


@contextmanager
def get_db():
    """Ensure SQLite database connections are cleanly closed upon context exit."""
    db_key = str(DB_PATH)
    if db_key not in _INITIALIZED_DBS:
        ensure_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def ensure_db() -> None:
    """Ensure database schema is created and upgraded with automated migrations."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DB_LOCK:
        _INITIALIZED_DBS.add(str(DB_PATH))
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                create table if not exists cache (
                    cache_key text primary key,
                    payload text not null,
                    fetched_at real not null,
                    ttl_seconds integer not null
                )
                """
            )
            conn.execute(
                """
                create table if not exists analysis_runs (
                    id integer primary key autoincrement,
                    symbol text not null,
                    created_at text not null,
                    payload text not null
                )
                """
            )
            conn.execute(
                """
                create table if not exists watchlist (
                    symbol text primary key,
                    group_name text not null default '默认',
                    note text not null default '',
                    created_at text not null,
                    updated_at text not null
                )
                """
            )
            conn.execute(
                """
                create table if not exists recommendation_snapshots (
                    id integer primary key autoincrement,
                    symbol text not null,
                    source_type text not null,
                    created_at text not null,
                    price real,
                    spy_price real,
                    vix_value real,
                    macro_regime text,
                    score real,
                    verdict text,
                    tags text,
                    short_term_thesis text,
                    mid_term_thesis text,
                    long_term_thesis text,
                    stop_loss_price real,
                    target_price real,
                    ai_model text,
                    evidence_json text,
                    status text default 'ACTIVE',
                    t5_price real,
                    t20_price real,
                    alpha real,
                    review_note text
                )
                """
            )
            # Automatic schema migration
            cursor = conn.cursor()
            existing_cols = [c[1] for c in cursor.execute("PRAGMA table_info(recommendation_snapshots)").fetchall()]
            new_columns = [
                ("macro_regime", "TEXT"),
                ("status", "TEXT DEFAULT 'ACTIVE'"),
                ("t5_price", "REAL"),
                ("t20_price", "REAL"),
                ("alpha", "REAL"),
                ("review_note", "TEXT"),
            ]
            for col_name, col_def in new_columns:
                if col_name not in existing_cols:
                    try:
                        cursor.execute(f"ALTER TABLE recommendation_snapshots ADD COLUMN {col_name} {col_def}")
                    except Exception:
                        pass

            conn.execute(
                """
                create table if not exists stock_dossiers (
                    symbol text primary key,
                    name text,
                    price real,
                    change_pct real,
                    valuation_status text,
                    margin_of_safety_pct real,
                    modules_json text not null,
                    created_at text not null,
                    updated_at text not null
                )
                """
            )
            conn.execute(
                """
                create table if not exists model_evolution_log (
                    id integer primary key autoincrement,
                    created_at text not null,
                    generation integer not null,
                    macro_regime text not null,
                    previous_weights text not null,
                    new_weights text not null,
                    evaluated_picks_count integer not null,
                    avg_alpha real,
                    hit_rate real,
                    tuning_rationale text not null
                )
                """
            )
            conn.execute(
                """
                create table if not exists active_model_state (
                    key text primary key,
                    value text not null,
                    updated_at text not null
                )
                """
            )

    try:
        from backend.services.research_kb import ensure_research_tables
        ensure_research_tables()
    except Exception as exc:
        print(f"[DB] ensure_research_tables skipped or failed: {exc}")


def get_cache(cache_key: str) -> Optional[Any]:
    """Retrieve unexpired payload from cache."""
    now = time.time()
    with DB_LOCK:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "select payload, fetched_at, ttl_seconds from cache where cache_key = ?",
                (cache_key,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            payload_str, fetched_at, ttl_seconds = row
            if (now - fetched_at) > ttl_seconds:
                return None
            try:
                return json.loads(payload_str)
            except json.JSONDecodeError:
                return None


def set_cache(cache_key: str, payload: Any, ttl_seconds: int) -> None:
    """Store payload in cache with TTL."""
    now = time.time()
    raw = json.dumps(payload, ensure_ascii=False)
    with DB_LOCK:
        with get_db() as conn:
            with conn:
                conn.execute(
                    """
                    insert into cache (cache_key, payload, fetched_at, ttl_seconds)
                    values (?, ?, ?, ?)
                    on conflict(cache_key) do update set
                        payload = excluded.payload,
                        fetched_at = excluded.fetched_at,
                        ttl_seconds = excluded.ttl_seconds
                    """,
                    (cache_key, raw, now, ttl_seconds),
                )


def save_analysis(symbol: str, payload: Dict[str, Any]) -> None:
    """Record an analysis run."""
    with DB_LOCK:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "insert into analysis_runs (symbol, created_at, payload) values (?, ?, ?)",
                (symbol, utc_now_iso(), json.dumps(payload, ensure_ascii=False)),
            )


def list_watchlist() -> List[Dict[str, Any]]:
    """List all symbols in watchlist."""
    with DB_LOCK:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            rows = cursor.execute(
                "select symbol, group_name, note, created_at, updated_at from watchlist order by updated_at desc"
            ).fetchall()
            return [
                {
                    "symbol": row["symbol"],
                    "group": row["group_name"],
                    "note": row["note"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
                for row in rows
            ]


def verify_symbol_exists(symbol: str) -> str:
    """Verify that a US stock symbol exists and has genuine market data."""
    clean_sym = symbol.strip().upper()
    if not clean_sym:
        raise AppError("请输入有效的股票代码。", 400)
    if not clean_sym.endswith(".US") and "." not in clean_sym and not clean_sym.startswith("^"):
        clean_sym = f"{clean_sym}.US"

    import re
    if not re.match(r"^[A-Z0-9\.\^]{1,15}$", clean_sym):
        raise AppError(f"标的代码格式不合法：【{clean_sym}】", 400)

    try:
        from backend.services.market_data import run_longbridge, unwrap_items
        res = run_longbridge(["quote", clean_sym, "--format", "json"], ttl_seconds=300, timeout=5)
        items = unwrap_items(res.get("data"))
        if items:
            for it in items:
                it_sym = str(it.get("symbol") or "").upper()
                if it_sym == clean_sym or it_sym == clean_sym.replace(".US", ""):
                    last = it.get("last_done") or it.get("last") or it.get("prev_close")
                    if last is not None and float(last) > 0:
                        return clean_sym
    except Exception:
        pass

    try:
        from backend.services.backtester import fetch_yahoo_history
        pure_sym = clean_sym.replace(".US", "").replace(".", "-")
        hist = fetch_yahoo_history(pure_sym, "5d")
        if hist and len(hist) > 0:
            return clean_sym
    except Exception:
        pass

    raise AppError(f"标的代码【{clean_sym}】在市场中不存在或未能取得有效行情，无法加入自选池。", 400)


def add_watchlist_symbol(symbol: str, group_name: str = "默认", note: str = "") -> Dict[str, Any]:
    """Add or update verified symbol in watchlist."""
    valid_symbol = verify_symbol_exists(symbol)
    now = utc_now_iso()
    with DB_LOCK:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                insert into watchlist (symbol, group_name, note, created_at, updated_at)
                values (?, ?, ?, ?, ?)
                on conflict(symbol) do update set
                    group_name = excluded.group_name,
                    note = excluded.note,
                    updated_at = excluded.updated_at
                """,
                (valid_symbol, group_name, note, now, now),
            )
    return {"ok": True, "symbol": valid_symbol, "group": group_name, "note": note}


def remove_watchlist_symbol(symbol: str) -> Dict[str, Any]:
    """Delete symbol from watchlist."""
    with DB_LOCK:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("delete from watchlist where symbol = ?", (symbol,))
    return {"ok": True, "symbol": symbol}


def recent_analysis_runs(limit: int = 12) -> List[Dict[str, Any]]:
    """List recent analysis summaries."""
    with DB_LOCK:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            rows = cursor.execute(
                "select id, symbol, created_at, payload from analysis_runs order by id desc limit ?",
                (limit,),
            ).fetchall()
            summaries: List[Dict[str, Any]] = []
            for row in rows:
                try:
                    payload = json.loads(row["payload"])
                except Exception:
                    payload = {}
                quote = payload.get("quote", {})
                score = payload.get("score", {})
                summaries.append(
                    {
                        "id": row["id"],
                        "symbol": row["symbol"],
                        "created_at": row["created_at"],
                        "price": quote.get("price"),
                        "pct_chg": quote.get("pct_chg"),
                        "score": score.get("score"),
                        "verdict": score.get("verdict"),
                        "ai_enabled": payload.get("ai_analysis", {}).get("enabled", False),
                    }
                )
            return summaries


def latest_analysis_payload(symbol: str) -> Optional[Dict[str, Any]]:
    """Get the latest analysis full payload for a symbol."""
    with DB_LOCK:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            row = cursor.execute(
                "select payload from analysis_runs where symbol = ? order by id desc limit 1",
                (symbol,),
            ).fetchone()
            if not row:
                return None
            try:
                return json.loads(row[0])
            except Exception:
                return None


def archive_recommendation_snapshot(
    symbol: str,
    source_type: str,
    price: Optional[float] = None,
    spy_price: Optional[float] = None,
    vix_value: Optional[float] = None,
    score: Optional[float] = None,
    verdict: str = "",
    tags: Optional[List[str]] = None,
    short_term_thesis: str = "",
    mid_term_thesis: str = "",
    long_term_thesis: str = "",
    stop_loss_price: Optional[float] = None,
    target_price: Optional[float] = None,
    ai_model: str = "CLI",
    evidence_json: str = "{}",
    review_note: str = "",
    created_at: Optional[str] = None
) -> Dict[str, Any]:
    """Archive a daily pick or manual AI decision snapshot into the review table."""
    ensure_db()
    now = created_at or utc_now_iso()
    tags_str = ",".join(tags or [])
    with DB_LOCK:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            date_prefix = now[:10]  # YYYY-MM-DD
            cursor.execute(
                """
                select id from recommendation_snapshots
                where symbol = ? and source_type = ? and substr(created_at, 1, 10) = ?
                order by id desc limit 1
                """,
                (symbol, source_type, date_prefix)
            )
            existing = cursor.fetchone()
            if existing:
                snap_id = existing[0]
                cursor.execute(
                    """
                    update recommendation_snapshots set
                        created_at = ?, price = ?, spy_price = ?, vix_value = ?, score = ?, verdict = ?,
                        tags = ?, short_term_thesis = ?, mid_term_thesis = ?, long_term_thesis = ?,
                        stop_loss_price = ?, target_price = ?, ai_model = ?, evidence_json = ?, review_note = ?
                    where id = ?
                    """,
                    (
                        now, price, spy_price, vix_value, score, verdict,
                        tags_str, short_term_thesis, mid_term_thesis, long_term_thesis,
                        stop_loss_price, target_price, ai_model, evidence_json, review_note,
                        snap_id
                    )
                )
                return {
                    "ok": True,
                    "id": snap_id,
                    "symbol": symbol,
                    "source_type": source_type,
                    "created_at": now,
                    "updated": True
                }
            cursor.execute(
                """
                insert into recommendation_snapshots (
                    symbol, source_type, created_at, price, spy_price, vix_value, score, verdict,
                    tags, short_term_thesis, mid_term_thesis, long_term_thesis,
                    stop_loss_price, target_price, ai_model, evidence_json, review_note
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    symbol, source_type, now, price, spy_price, vix_value, score, verdict,
                    tags_str, short_term_thesis, mid_term_thesis, long_term_thesis,
                    stop_loss_price, target_price, ai_model, evidence_json, review_note
                )
            )
            snapshot_id = cursor.lastrowid
            return {
                "ok": True,
                "id": snapshot_id,
                "symbol": symbol,
                "source_type": source_type,
                "created_at": now
            }


def get_review_snapshots(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve decision review and performance backtest snapshots."""
    with DB_LOCK:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            rows = cursor.execute(
                """
                select id, symbol, source_type, created_at, price, spy_price, vix_value, score, verdict,
                       tags, short_term_thesis, mid_term_thesis, long_term_thesis,
                       stop_loss_price, target_price, ai_model, status, t5_price, t20_price, alpha, review_note
                from recommendation_snapshots
                order by id desc limit ?
                """,
                (limit,)
            ).fetchall()
            results = []
            for row in rows:
                tags = [t.strip() for t in (row["tags"] or "").split(",") if t.strip()]
                results.append({
                    "id": row["id"],
                    "symbol": row["symbol"],
                    "source_type": row["source_type"],
                    "created_at": row["created_at"],
                    "price": row["price"],
                    "spy_price": row["spy_price"],
                    "vix_value": row["vix_value"],
                    "score": row["score"],
                    "verdict": row["verdict"],
                    "tags": tags,
                    "short_term_thesis": row["short_term_thesis"],
                    "mid_term_thesis": row["mid_term_thesis"],
                    "long_term_thesis": row["long_term_thesis"],
                    "stop_loss_price": row["stop_loss_price"],
                    "target_price": row["target_price"],
                    "ai_model": row["ai_model"],
                    "status": row["status"],
                    "t5_price": row["t5_price"],
                    "t20_price": row["t20_price"],
                    "alpha": row["alpha"],
                    "review_note": row["review_note"]
                })
            return results


def get_active_model_state() -> Dict[str, Any]:
    """Retrieve current dynamic model generation and factor weights."""
    ensure_db()
    with DB_LOCK:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            rows = cursor.execute("select key, value from active_model_state").fetchall()
            state = {r[0]: r[1] for r in rows}
            
            gen = int(state.get("generation", 1))
            weights_raw = state.get("weights")
            if weights_raw:
                try:
                    weights = json.loads(weights_raw)
                except Exception:
                    weights = {"momentum": 35, "catalyst": 25, "quality": 20, "valuation": 10, "liquidity": 10}
            else:
                weights = {"momentum": 35, "catalyst": 25, "quality": 20, "valuation": 10, "liquidity": 10}
                
            return {
                "generation": gen,
                "weights": weights,
                "updated_at": state.get("updated_at", utc_now_iso()),
                "total_cycles": int(state.get("total_cycles", 0)),
            }


def update_active_model_state(generation: int, weights: Dict[str, int], total_cycles: int = 1) -> None:
    """Save updated evolved model generation and weights."""
    ensure_db()
    now = utc_now_iso()
    with DB_LOCK:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "insert or replace into active_model_state (key, value, updated_at) values (?, ?, ?)",
                ("generation", str(generation), now)
            )
            cursor.execute(
                "insert or replace into active_model_state (key, value, updated_at) values (?, ?, ?)",
                ("weights", json.dumps(weights), now)
            )
            cursor.execute(
                "insert or replace into active_model_state (key, value, updated_at) values (?, ?, ?)",
                ("total_cycles", str(total_cycles), now)
            )


def record_model_evolution(
    generation: int,
    macro_regime: str,
    previous_weights: Dict[str, int],
    new_weights: Dict[str, int],
    evaluated_picks_count: int,
    avg_alpha: float,
    hit_rate: float,
    tuning_rationale: str,
) -> int:
    """Record an audit entry into the model evolution history log."""
    ensure_db()
    now = utc_now_iso()
    with DB_LOCK:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                insert into model_evolution_log (
                    created_at, generation, macro_regime, previous_weights, new_weights,
                    evaluated_picks_count, avg_alpha, hit_rate, tuning_rationale
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now, generation, macro_regime, json.dumps(previous_weights), json.dumps(new_weights),
                    evaluated_picks_count, avg_alpha, hit_rate, tuning_rationale
                )
            )
            return cursor.lastrowid or 0


def get_model_evolution_logs(limit: int = 15) -> List[Dict[str, Any]]:
    """Retrieve historical model self-evolution logs."""
    ensure_db()
    with DB_LOCK:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            rows = cursor.execute(
                """
                select id, created_at, generation, macro_regime, previous_weights, new_weights,
                       evaluated_picks_count, avg_alpha, hit_rate, tuning_rationale
                from model_evolution_log
                order by id desc limit ?
                """,
                (limit,)
            ).fetchall()
            logs = []
            for r in rows:
                try:
                    prev_w = json.loads(r["previous_weights"])
                except Exception:
                    prev_w = {}
                try:
                    new_w = json.loads(r["new_weights"])
                except Exception:
                    new_w = {}
                logs.append({
                    "id": r["id"],
                    "created_at": r["created_at"],
                    "generation": r["generation"],
                    "macro_regime": r["macro_regime"],
                    "previous_weights": prev_w,
                    "new_weights": new_w,
                    "evaluated_picks_count": r["evaluated_picks_count"],
                    "avg_alpha": r["avg_alpha"],
                    "hit_rate": r["hit_rate"],
                    "tuning_rationale": r["tuning_rationale"],
                })
            return logs


def update_snapshot_evaluation(
    snapshot_id: int,
    t5_price: Optional[float] = None,
    t20_price: Optional[float] = None,
    alpha: Optional[float] = None,
    status: str = "ACTIVE",
    review_note: str = "",
) -> None:
    """Update evaluation metrics for a historical recommendation snapshot."""
    with DB_LOCK:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                update recommendation_snapshots
                set t5_price = coalesce(?, t5_price),
                    t20_price = coalesce(?, t20_price),
                    alpha = coalesce(?, alpha),
                    status = ?,
                    review_note = ?
                where id = ?
                """,
                (t5_price, t20_price, alpha, status, review_note, snapshot_id)
            )


# ==============================================================================
# Stock Dossier (Modular Long-Term Research Persistence)
# ==============================================================================

def save_or_update_dossier(
    symbol: str,
    name: str,
    price: Optional[float],
    change_pct: Optional[float],
    valuation_status: str,
    margin_of_safety_pct: Optional[float],
    modules_dict: Dict[str, Any],
) -> Dict[str, Any]:
    """Persist or update an entire structured dossier for a symbol."""
    ensure_db()
    now = utc_now_iso()
    with DB_LOCK:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            existing = cursor.execute("SELECT created_at FROM stock_dossiers WHERE symbol = ?", (symbol,)).fetchone()
            created_at = existing[0] if existing else now
            cursor.execute(
                """
                INSERT INTO stock_dossiers (
                    symbol, name, price, change_pct, valuation_status,
                    margin_of_safety_pct, modules_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    name = excluded.name,
                    price = excluded.price,
                    change_pct = excluded.change_pct,
                    valuation_status = excluded.valuation_status,
                    margin_of_safety_pct = excluded.margin_of_safety_pct,
                    modules_json = excluded.modules_json,
                    updated_at = excluded.updated_at
                """,
                (
                    symbol, name, price, change_pct, valuation_status,
                    margin_of_safety_pct, json.dumps(modules_dict, ensure_ascii=False),
                    created_at, now
                )
            )
            return {
                "symbol": symbol,
                "name": name,
                "price": price,
                "change_pct": change_pct,
                "valuation_status": valuation_status,
                "margin_of_safety_pct": margin_of_safety_pct,
                "modules": modules_dict,
                "created_at": created_at,
                "updated_at": now
            }


def get_dossier(symbol: str) -> Optional[Dict[str, Any]]:
    """Retrieve full cached dossier for a symbol."""
    ensure_db()
    with DB_LOCK:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.cursor().execute(
                """
                SELECT symbol, name, price, change_pct, valuation_status,
                       margin_of_safety_pct, modules_json, created_at, updated_at
                FROM stock_dossiers WHERE symbol = ?
                """,
                (symbol,)
            ).fetchone()
            if not row:
                return None
            try:
                mods = json.loads(row["modules_json"])
            except Exception:
                mods = {}
            return {
                "symbol": row["symbol"],
                "name": row["name"],
                "price": row["price"],
                "change_pct": row["change_pct"],
                "valuation_status": row["valuation_status"],
                "margin_of_safety_pct": row["margin_of_safety_pct"],
                "modules": mods,
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }


def update_dossier_module(symbol: str, module_name: str, module_payload: Any) -> Optional[Dict[str, Any]]:
    """Granularly update a single module inside an existing dossier without touching others."""
    ensure_db()
    now = utc_now_iso()
    with DB_LOCK:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            row = cursor.execute(
                "SELECT modules_json, name, price, change_pct, valuation_status, margin_of_safety_pct, created_at FROM stock_dossiers WHERE symbol = ?",
                (symbol,)
            ).fetchone()
            if not row:
                return None
            try:
                mods = json.loads(row["modules_json"])
            except Exception:
                mods = {}

            mods[module_name] = {
                "updated_at": now,
                "data": module_payload
            }

            cursor.execute(
                "UPDATE stock_dossiers SET modules_json = ?, updated_at = ? WHERE symbol = ?",
                (json.dumps(mods, ensure_ascii=False), now, symbol)
            )
            return {
                "symbol": symbol,
                "module": module_name,
                "updated_at": now,
                "data": module_payload,
                "modules": mods
            }


def update_dossier_price(
    symbol: str,
    price: float,
    change_pct: float,
    technical_data: Optional[Dict[str, Any]] = None,
    valuation_data: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Hot sync current market price and technical indicators without touching deep research modules."""
    ensure_db()
    now = utc_now_iso()
    with DB_LOCK:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            row = cursor.execute("SELECT modules_json FROM stock_dossiers WHERE symbol = ?", (symbol,)).fetchone()
            if not row:
                return None
            try:
                mods = json.loads(row["modules_json"])
            except Exception:
                mods = {}

            if technical_data is not None:
                mods["technical_compass"] = {
                    "updated_at": now,
                    "data": technical_data
                }
            if valuation_data is not None:
                mods["valuation_matrix"] = {
                    "updated_at": now,
                    "data": valuation_data
                }

            val_status = valuation_data.get("status") if valuation_data else None
            margin_pct = valuation_data.get("margin_of_safety_pct") if valuation_data else None

            cursor.execute(
                """
                UPDATE stock_dossiers
                SET price = ?,
                    change_pct = ?,
                    valuation_status = COALESCE(?, valuation_status),
                    margin_of_safety_pct = COALESCE(?, margin_of_safety_pct),
                    modules_json = ?,
                    updated_at = ?
                WHERE symbol = ?
                """,
                (price, change_pct, val_status, margin_pct, json.dumps(mods, ensure_ascii=False), now, symbol)
            )
            return get_dossier(symbol)


def list_dossier_history() -> List[Dict[str, Any]]:
    """List all archived dossiers for the history panel."""
    ensure_db()
    with DB_LOCK:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.cursor().execute(
                """
                SELECT symbol, name, price, change_pct, valuation_status,
                       margin_of_safety_pct, created_at, updated_at
                FROM stock_dossiers
                ORDER BY updated_at DESC
                """
            ).fetchall()
            return [
                {
                    "symbol": r["symbol"],
                    "name": r["name"] or r["symbol"],
                    "price": r["price"],
                    "change_pct": r["change_pct"],
                    "valuation_status": r["valuation_status"] or "分析中",
                    "margin_of_safety_pct": r["margin_of_safety_pct"],
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"]
                }
                for r in rows
            ]


def delete_dossier(symbol: str) -> bool:
    """Remove a dossier entry from history."""
    ensure_db()
    with DB_LOCK:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM stock_dossiers WHERE symbol = ?", (symbol,))
            return cursor.rowcount > 0

