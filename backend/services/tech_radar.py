"""
Tech Radar Service:
Disabled as App Store / Google Play lacks public commercial API.
No synthetic or fabricated data is permitted in production research.
"""
from typing import Any, Dict
from backend.core.utils import utc_now_iso


def get_tech_catalysts() -> Dict[str, Any]:
    """
    Return status for tech alternative data.
    Explicitly indicates that App Store / Google Play API is unavailable.
    """
    return {
        "ok": True,
        "available": False,
        "app_store_available": False,
        "notice": "App Store / Google Play 移动榜单与旗舰产品路线图暂无官方免费数据接口，系统已完全停用该模块的合成假数据，不再参与任何量化漏斗或因子加分。",
        "timestamp": utc_now_iso(),
        "app_store_radar": [],
        "flagship_roadmaps": []
    }
