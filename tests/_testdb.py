"""Test bootstrap: point the app at an isolated temp SQLite DB and create tables.

Import this module BEFORE any `backend.*` import so DB_PATH picks up the env var.
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if "AI_STOCK_DB" not in os.environ:
    _tmpdir = tempfile.mkdtemp(prefix="ai_stock_test_")
    os.environ["AI_STOCK_DB"] = os.path.join(_tmpdir, "test.sqlite")

from backend.db import ensure_db  # noqa: E402

ensure_db()
