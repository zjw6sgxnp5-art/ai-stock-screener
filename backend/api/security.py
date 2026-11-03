"""HTTP security helpers complementing router.py's CORS/CSRF checks.

- Host header allowlist (DNS rebinding defense) for every request.
- Strict Origin check: same-origin (Origin netloc == Host) or explicit allowlist.
- Optional API token for non-browser write clients.

Environment variables:
  AI_STOCK_ALLOWED_ORIGINS  comma-separated extra origins, e.g. "http://192.168.1.5:8765"
  AI_STOCK_ALLOWED_HOSTS    comma-separated extra Host names (no port), e.g. "mybox.local"
  AI_STOCK_API_TOKEN        optional; if set, write requests without Origin/Referer must send
                            "X-API-Token: <token>" or "Authorization: Bearer <token>".
"""
import hmac
import os
import re
from typing import Optional
from urllib.parse import urlparse

from backend.config import AppError

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "[::1]"}


def _env_set(name: str) -> set:
    return {x.strip().rstrip("/").lower() for x in os.environ.get(name, "").split(",") if x.strip()}


def _host_name(host_header: str) -> str:
    h = (host_header or "").strip().lower()
    if h.startswith("["):
        return h.split("]")[0] + "]"
    return h.rsplit(":", 1)[0] if h.count(":") == 1 else h


def host_ok(host_header: Optional[str]) -> bool:
    if not host_header:
        return False
    return _host_name(host_header) in (_LOCAL_HOSTS | _env_set("AI_STOCK_ALLOWED_HOSTS"))


def origin_matches(origin_or_url: str, host_header: Optional[str]) -> bool:
    """True if Origin/Referer is same-origin with Host or in AI_STOCK_ALLOWED_ORIGINS."""
    p = urlparse((origin_or_url or "").strip())
    if p.scheme not in ("http", "https") or not p.netloc:
        return False  # rejects "null", file://, garbage
    origin = f"{p.scheme}://{p.netloc}".lower()
    if origin in _env_set("AI_STOCK_ALLOWED_ORIGINS"):
        return True
    return p.netloc.lower() == (host_header or "").strip().lower()


def token_ok(headers) -> bool:
    token = os.environ.get("AI_STOCK_API_TOKEN", "")
    if not token:
        return True
    given = headers.get("X-API-Token", "") or ""
    auth = headers.get("Authorization", "") or ""
    if not given and auth.lower().startswith("bearer "):
        given = auth[7:].strip()
    return bool(given) and hmac.compare_digest(given.encode(), token.encode())


def enforce_host_and_token(method: str, headers) -> None:
    """Raise AppError for forged Host (403) or missing token on non-browser writes (401)."""
    if not host_ok(headers.get("Host")):
        raise AppError("Host 不被允许（防 DNS rebinding），可用 AI_STOCK_ALLOWED_HOSTS 配置。", 403)
    if method.upper() in ("POST", "PUT", "PATCH", "DELETE"):
        if not headers.get("Origin") and not headers.get("Referer") and not token_ok(headers):
            raise AppError("缺少或错误的 API token（X-API-Token）。", 401)


def validate_symbol_list(raw: Optional[str], is_valid) -> Optional[str]:
    """Reject (400) a batch symbols param containing any invalid token."""
    if raw:
        for tok in re.split(r"[\s,;]+", raw.strip()):
            if tok and not is_valid(tok):
                raise AppError("股票代码格式非法。", 400, {"symbol": tok[:40]})
    return raw
