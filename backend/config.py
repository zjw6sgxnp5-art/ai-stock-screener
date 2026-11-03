"""
Configuration and constants for AI Stock Research Workbench.
"""
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "web"
DB_PATH = Path(os.environ.get("AI_STOCK_DB", str(BASE_DIR / "data" / "app.sqlite")))
REPORTS_DIR = BASE_DIR / "reports"

# Server configuration
APP_HOST = os.environ.get("AI_STOCK_HOST", "127.0.0.1")
APP_PORT = int(os.environ.get("AI_STOCK_PORT", "8765"))
MAX_WORKERS = int(os.environ.get("AI_STOCK_WORKERS", "6"))


def _resolve_cli_bin(env_name: str, cmd_name: str, fallback_path: str) -> str:
    """Resolve CLI binary dynamically from env, system PATH, user home, or fallback."""
    from_env = os.environ.get(env_name)
    if from_env:
        return from_env
    found = shutil.which(cmd_name)
    if found:
        return found
    home = Path.home()
    if cmd_name == "grok":
        candidate = home / ".grok" / "bin" / "grok"
        if candidate.exists():
            return str(candidate)
    elif cmd_name == "gemini":
        candidate = home / ".local" / "bin" / "gemini"
        if candidate.exists():
            return str(candidate)
    return fallback_path


# External CLI Binaries
LONG_BRIDGE_BIN = os.environ.get("LONG_BRIDGE_BIN", shutil.which("longbridge") or "longbridge")
GROK_BIN = _resolve_cli_bin("GROK_BIN", "grok", str(Path.home() / ".grok" / "bin" / "grok"))
GEMINI_BIN = _resolve_cli_bin("GEMINI_BIN", "gemini", str(Path.home() / ".local" / "bin" / "gemini"))
DEFAULT_TIMEOUT = int(os.environ.get("LONG_BRIDGE_TIMEOUT", "25"))
DEFAULT_LLM_MODEL = os.environ.get("AI_STOCK_LLM_MODEL", "gemini-1.5-pro")

# Universe & Screening Symbols (22 US Liquid Leaders - Excludes Broad ETFs)
DEFAULT_SCREENER_SYMBOLS = [
    "NVDA.US",
    "MSFT.US",
    "AAPL.US",
    "AMZN.US",
    "GOOGL.US",
    "META.US",
    "AVGO.US",
    "AMD.US",
    "TSLA.US",
    "NFLX.US",
    "COST.US",
    "PLTR.US",
    "QCOM.US",
    "INTC.US",
    "MU.US",
    "ARM.US",
    "CRM.US",
    "ORCL.US",
    "PANW.US",
    "NOW.US",
    "KO.US",
    "ASML.US",
]

DEFAULT_UNIVERSE = list(DEFAULT_SCREENER_SYMBOLS)


class AppError(Exception):
    """Custom Application Error for structured API responses."""
    def __init__(self, message: str, status: int = 400, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.details = details or {}


# ---- Strategy / backtest shared constants (single source of truth for live + backtest + README) ----
ATR_PERIOD = 14
ATR_STOP_MULTIPLIER = float(os.environ.get("AI_STOCK_ATR_MULT", "2.0"))
# One-way trading cost (commission + fees) and slippage, in basis points. Default total ~5bp per side.
BACKTEST_COST_BPS = float(os.environ.get("AI_STOCK_BT_COST_BPS", "3.0"))
BACKTEST_SLIPPAGE_BPS = float(os.environ.get("AI_STOCK_BT_SLIPPAGE_BPS", "2.0"))
DEFAULT_BACKTEST_UNIVERSE = [
    s.strip().upper()
    for s in os.environ.get(
        "AI_STOCK_BT_UNIVERSE",
        "AAPL,MSFT,NVDA,AMZN,GOOGL,JNJ,JPM,XOM,PG,CAT,AMD,TSLA",
    ).split(",")
    if s.strip()
]
# Fraction of the simulation window used as in-sample for sensitivity analysis (rest = out-of-sample).
SENSITIVITY_IS_FRACTION = float(os.environ.get("AI_STOCK_BT_IS_FRACTION", "0.6"))
