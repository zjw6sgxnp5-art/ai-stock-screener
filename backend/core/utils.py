"""
Core utility functions for formatting, parsing, and normalization.
"""
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def utc_now_iso() -> str:
    """Return current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    """Clamp a floating point number to a given range."""
    return max(lower, min(upper, value))


_SYMBOL_PATTERN = re.compile(r"^[A-Z0-9.\-^]{1,20}$")


def is_valid_symbol(symbol: Any) -> bool:
    """Validate stock symbol format (letters, digits, dot, hyphen, caret)."""
    if not symbol or not isinstance(symbol, str):
        return False
    clean = symbol.strip().upper()
    return bool(_SYMBOL_PATTERN.match(clean))


def normalize_symbol(symbol: str) -> str:
    """Normalize stock symbol to UPPERCASE.US format after removing illegal characters."""
    sym = (symbol or "").strip().upper()
    if not sym:
        return ""
    # Strip any dangerous characters (e.g. paths, quotes, shell separators)
    sym = re.sub(r"[^A-Z0-9.\-^]", "", sym)
    if not sym:
        return ""
    if not (sym.endswith(".US") or sym.endswith(".HK") or sym.endswith(".SH") or sym.endswith(".SZ")):
        sym = f"{sym}.US"
    return sym


def parse_symbol_list(raw: str, default: Optional[List[str]] = None, max_count: int = 30) -> List[str]:
    """Parse comma/space/semicolon-separated symbols into a clean normalized list."""
    if not raw:
        return default or []
    tokens = re.split(r"[\s,;]+", raw.strip())
    results: List[str] = []
    for item in tokens:
        item = item.strip()
        if not item:
            continue
        cleaned = normalize_symbol(item)
        if cleaned and is_valid_symbol(cleaned) and cleaned not in results:
            results.append(cleaned)
        if len(results) >= max_count:
            break
    return results or (default or [])


def number_from(value: Any) -> Optional[float]:
    """Extract float from various data types safely, including multiples like '28.12x' and percentages."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace(",", "").replace("%", "").replace("$", "")
        if cleaned.lower().endswith("x"):
            cleaned = cleaned[:-1].strip()
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            m = re.search(r"[-+]?\d*\.?\d+", cleaned)
            if m:
                try:
                    return float(m.group(0))
                except ValueError:
                    return None
            return None
    return None


def pick_number(item: Dict[str, Any], keys: List[str]) -> Optional[float]:
    """Extract first non-null numerical value from a dictionary given candidate keys."""
    for key in keys:
        if key in item and item[key] is not None:
            num = number_from(item[key])
            if num is not None:
                return num
    return None


def first_value(item: Dict[str, Any], keys: List[str]) -> Any:
    """Extract first non-null non-empty value from candidate keys."""
    for key in keys:
        if key in item and item[key] not in (None, ""):
            return item[key]
    return None


def strip_html(value: Any) -> Optional[str]:
    """Remove HTML tags from text."""
    if not value or not isinstance(value, str):
        return None
    clean = re.sub(r"<[^>]+>", "", value)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean or None


def command_error_message(stderr: str, stdout: str = "") -> str:
    """Format readable command line error message."""
    text = (stderr or stdout or "未知错误").strip()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return "命令执行失败，但未输出具体错误信息。"
    if len(lines) == 1:
        return lines[0]
    return f"{lines[0]} (详情: {lines[-1]})"
