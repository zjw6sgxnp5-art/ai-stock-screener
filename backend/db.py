"""
Database layer for SQLite storage, caching, watchlists, analysis history, and recommendation snapshots.
"""
import json
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional

from backend.config import DB_PATH
from backend.core.utils import number_from, utc_now_iso

DB_LOCK = threading.RLock()


def ensure_db() -> None:
    """Ensure database schema is created and upgraded with automated migrations."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DB_LOCK:
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


def get_cache(cache_key: str) -> Optional[Any]:
    """Retrieve unexpired payload from cache."""
    now = time.time()
    with DB_LOCK:
        with sqlite3.connect(DB_PATH) as conn:
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
        with sqlite3.connect(DB_PATH) as conn:
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


def add_watchlist_symbol(symbol: str, group_name: str = "默认", note: str = "") -> Dict[str, Any]:
    """Add or update symbol in watchlist."""
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
                (symbol, group_name, note, now, now),
            )
    return {"ok": True, "symbol": symbol, "group": group_name, "note": note}


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
    review_note: str = ""
) -> Dict[str, Any]:
    """Archive a daily pick or manual AI decision snapshot into the review table."""
    ensure_db()
    now = utc_now_iso()
    tags_str = ",".join(tags or [])
    with DB_LOCK:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
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
                       stop_loss_price, target_price, ai_model, t5_price, t20_price, alpha, review_note
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
                    "t5_price": row["t5_price"],
                    "t20_price": row["t20_price"],
                    "alpha": row["alpha"],
                    "review_note": row["review_note"]
                })
            return results
