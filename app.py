#!/usr/bin/env python3
"""
AI 选股 · 机构级智能投研工作台 (AI Stock Workbench 2.0)
Entry point script.
"""
import sys
from http.server import ThreadingHTTPServer

from backend.api.router import RequestHandler
from backend.config import APP_HOST, APP_PORT, GEMINI_BIN, GROK_BIN, LONG_BRIDGE_BIN
from backend.db import ensure_db
from backend.services.ai_engine import check_ai_models_status
from backend.services.auto_evolution import start_autonomous_daemon


def main() -> None:
    """Initialize SQLite database and launch institutional HTTP service."""
    ensure_db()
    
    # Launch autonomous self-evolving engine in background
    start_autonomous_daemon()
    
    # Check AI models & Longbridge status on startup
    status = check_ai_models_status()
    grok_ok = status.get("grok", {}).get("installed", False)
    gemini_ok = status.get("gemini", {}).get("installed", False)
    lb_ok = status.get("longbridge", {}).get("ok", False)

    server = ThreadingHTTPServer((APP_HOST, APP_PORT), RequestHandler)
    print("=" * 65)
    print("  🚀 AI 选股 · 机构级智能投研工作台 (Workbench 2.0)")
    print(f"  🌐 服务地址: http://{APP_HOST}:{APP_PORT}")
    print("-" * 65)
    print(f"  [AI 引擎] Grok CLI:   {'✅ 可用 (' + GROK_BIN + ')' if grok_ok else '❌ 未就绪'}")
    print(f"  [AI 引擎] Gemini CLI: {'✅ 可用 (' + GEMINI_BIN + ')' if gemini_ok else '❌ 未就绪'}")
    print(f"  [数据引擎] Longbridge:{'✅ 实时数据已就绪' if lb_ok else '⚠️ 离线模式 (已启用高保真投研基准快照，绝不白屏)'}")
    print("=" * 65)
    print("提示: 在终端输入 'longbridge auth login' 可随时切换毫秒级实时流。")
    print("按 Ctrl+C 可停止服务...\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n正在安全关闭服务...")
    finally:
        server.server_close()
        print("服务已停止。")


if __name__ == "__main__":
    main()
