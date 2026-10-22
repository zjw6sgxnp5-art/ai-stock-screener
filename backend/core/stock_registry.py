"""
Unified Stock Metadata & Registry Engine (Single Source of Truth).
Consolidates ticker aliases, Chinese names, industry sectors, default beta,
IV rank, and daily screening universe into a single authoritative registry.
Eliminates fragmented mappings across screener, portfolio, KB, and market_data.
"""
from typing import Any, Dict, List, Optional


# Authoritative definition for all institutional stock profiles
# Format: clean_symbol -> { name_zh, name_en, sector, beta, iv_rank, is_daily_core }
_REGISTRY_DATA: Dict[str, Dict[str, Any]] = {
    # 1. 半导体与前沿算力芯片 (Semiconductors & AI Accelerators)
    "NVDA": {"name_zh": "英伟达", "name_en": "NVIDIA", "sector": "半导体与芯片硬件", "beta": 1.75, "iv_rank": 65, "is_daily_core": True},
    "MU":   {"name_zh": "美光科技", "name_en": "Micron", "sector": "半导体与芯片硬件", "beta": 1.55, "iv_rank": 70, "is_daily_core": True},
    "AMD":  {"name_zh": "超微半导体", "name_en": "AMD", "sector": "半导体与芯片硬件", "beta": 1.70, "iv_rank": 68, "is_daily_core": True},
    "AVGO": {"name_zh": "博通", "name_en": "Broadcom", "sector": "半导体与芯片硬件", "beta": 1.40, "iv_rank": 52, "is_daily_core": True},
    "QCOM": {"name_zh": "高通", "name_en": "Qualcomm", "sector": "半导体与芯片硬件", "beta": 1.25, "iv_rank": 48, "is_daily_core": True},
    "ARM":  {"name_zh": "安谋", "name_en": "ARM Holdings", "sector": "半导体与芯片硬件", "beta": 1.85, "iv_rank": 72, "is_daily_core": True},
    "TSM":  {"name_zh": "台积电", "name_en": "TSMC", "sector": "半导体与芯片硬件", "beta": 1.30, "iv_rank": 45, "is_daily_core": False},
    "ASML": {"name_zh": "阿斯麦", "name_en": "ASML", "sector": "半导体与芯片硬件", "beta": 1.35, "iv_rank": 50, "is_daily_core": True},
    "INTC": {"name_zh": "英特尔", "name_en": "Intel", "sector": "半导体与芯片硬件", "beta": 1.45, "iv_rank": 62, "is_daily_core": True},
    "LRCX": {"name_zh": "拉姆研究", "name_en": "Lam Research", "sector": "半导体与芯片硬件", "beta": 1.45, "iv_rank": 55, "is_daily_core": False},
    "AMAT": {"name_zh": "应用材料", "name_en": "Applied Materials", "sector": "半导体与芯片硬件", "beta": 1.40, "iv_rank": 50, "is_daily_core": False},
    "KLAC": {"name_zh": "科磊", "name_en": "KLA Corp", "sector": "半导体与芯片硬件", "beta": 1.35, "iv_rank": 48, "is_daily_core": False},
    "TXN":  {"name_zh": "德州仪器", "name_en": "Texas Instruments", "sector": "半导体与芯片硬件", "beta": 1.05, "iv_rank": 35, "is_daily_core": False},
    "MRVL": {"name_zh": "迈威尔科技", "name_en": "Marvell", "sector": "半导体与芯片硬件", "beta": 1.60, "iv_rank": 60, "is_daily_core": False},

    # 2. 软件与云计算平台 (Software & Cloud Services)
    "MSFT": {"name_zh": "微软", "name_en": "Microsoft", "sector": "软件与云计算平台", "beta": 1.05, "iv_rank": 35, "is_daily_core": True},
    "PLTR": {"name_zh": "Palantir", "name_en": "Palantir", "sector": "软件与云计算平台", "beta": 1.65, "iv_rank": 66, "is_daily_core": True},
    "CRM":  {"name_zh": "赛富时", "name_en": "Salesforce", "sector": "软件与云计算平台", "beta": 1.15, "iv_rank": 38, "is_daily_core": True},
    "NOW":  {"name_zh": "ServiceNow", "name_en": "ServiceNow", "sector": "软件与云计算平台", "beta": 1.12, "iv_rank": 36, "is_daily_core": True},
    "PANW": {"name_zh": "派拓网络", "name_en": "Palo Alto Networks", "sector": "软件与云计算平台", "beta": 1.20, "iv_rank": 44, "is_daily_core": True},
    "ORCL": {"name_zh": "甲骨文", "name_en": "Oracle", "sector": "软件与云计算平台", "beta": 1.10, "iv_rank": 38, "is_daily_core": True},
    "ADBE": {"name_zh": "奥多比", "name_en": "Adobe", "sector": "软件与云计算平台", "beta": 1.25, "iv_rank": 42, "is_daily_core": False},
    "SNOW": {"name_zh": "Snowflake", "name_en": "Snowflake", "sector": "软件与云计算平台", "beta": 1.70, "iv_rank": 62, "is_daily_core": False},
    "CRWD": {"name_zh": "CrowdStrike", "name_en": "CrowdStrike", "sector": "软件与云计算平台", "beta": 1.40, "iv_rank": 52, "is_daily_core": False},

    # 3. 互动媒体与互联网平台 (Interactive Media & Internet)
    "META":  {"name_zh": "Meta", "name_en": "Meta", "sector": "互动媒体与互联网服务", "beta": 1.35, "iv_rank": 55, "is_daily_core": True},
    "GOOGL": {"name_zh": "谷歌A", "name_en": "Alphabet A", "sector": "互动媒体与互联网服务", "beta": 1.10, "iv_rank": 40, "is_daily_core": True},
    "GOOG":  {"name_zh": "谷歌C", "name_en": "Alphabet C", "sector": "互动媒体与互联网服务", "beta": 1.10, "iv_rank": 40, "is_daily_core": False},
    "NFLX":  {"name_zh": "奈飞", "name_en": "Netflix", "sector": "互动媒体与互联网服务", "beta": 1.25, "iv_rank": 46, "is_daily_core": True},
    "UBER":  {"name_zh": "优步", "name_en": "Uber", "sector": "互动媒体与互联网服务", "beta": 1.30, "iv_rank": 52, "is_daily_core": False},
    "BABA":  {"name_zh": "阿里巴巴", "name_en": "Alibaba", "sector": "电商与互联网服务", "beta": 1.35, "iv_rank": 55, "is_daily_core": False},
    "PDD":   {"name_zh": "拼多多", "name_en": "PDD Holdings", "sector": "电商与互联网服务", "beta": 1.45, "iv_rank": 60, "is_daily_core": False},

    # 4. 消费电子与移动硬件 (Consumer Hardware)
    "AAPL": {"name_zh": "苹果", "name_en": "Apple", "sector": "消费电子与移动硬件", "beta": 0.98, "iv_rank": 32, "is_daily_core": True},
    "DELL": {"name_zh": "戴尔科技", "name_en": "Dell", "sector": "IT硬件与算力服务器", "beta": 1.35, "iv_rank": 50, "is_daily_core": False},
    "SMCI": {"name_zh": "超微电脑", "name_en": "Super Micro Computer", "sector": "IT硬件与算力服务器", "beta": 2.20, "iv_rank": 85, "is_daily_core": False},

    # 5. 汽车与高端出行 (Automobiles & Mobility)
    "TSLA": {"name_zh": "特斯拉", "name_en": "Tesla", "sector": "汽车与高端制造", "beta": 2.10, "iv_rank": 78, "is_daily_core": True},
    "NIO":  {"name_zh": "蔚来", "name_en": "NIO", "sector": "汽车与高端制造", "beta": 1.90, "iv_rank": 75, "is_daily_core": False},
    "F":    {"name_zh": "福特汽车", "name_en": "Ford", "sector": "汽车与高端制造", "beta": 1.15, "iv_rank": 38, "is_daily_core": False},
    "GM":   {"name_zh": "通用汽车", "name_en": "General Motors", "sector": "汽车与高端制造", "beta": 1.20, "iv_rank": 40, "is_daily_core": False},

    # 6. 大众零售与连锁商业 (Retail & Consumer Services)
    "AMZN": {"name_zh": "亚马逊", "name_en": "Amazon", "sector": "电商与综合零售", "beta": 1.20, "iv_rank": 45, "is_daily_core": True},
    "COST": {"name_zh": "开市客", "name_en": "Costco", "sector": "大众零售与连锁商业", "beta": 0.78, "iv_rank": 26, "is_daily_core": True},
    "WMT":  {"name_zh": "沃尔玛", "name_en": "Walmart", "sector": "大众零售与连锁商业", "beta": 0.65, "iv_rank": 22, "is_daily_core": False},
    "TGT":  {"name_zh": "塔吉特", "name_en": "Target", "sector": "大众零售与连锁商业", "beta": 1.05, "iv_rank": 35, "is_daily_core": False},
    "HD":   {"name_zh": "家得宝", "name_en": "Home Depot", "sector": "大众零售与连锁商业", "beta": 0.92, "iv_rank": 28, "is_daily_core": False},
    "MCD":  {"name_zh": "麦当劳", "name_en": "McDonald's", "sector": "大众消费与餐饮连锁", "beta": 0.65, "iv_rank": 22, "is_daily_core": False},
    "SBUX": {"name_zh": "星巴克", "name_en": "Starbucks", "sector": "大众消费与餐饮连锁", "beta": 0.95, "iv_rank": 30, "is_daily_core": False},
    "KO":   {"name_zh": "可口可乐", "name_en": "Coca-Cola", "sector": "必需消费品与饮料", "beta": 0.58, "iv_rank": 18, "is_daily_core": True},
    "PEP":  {"name_zh": "百事可乐", "name_en": "PepsiCo", "sector": "必需消费品与饮料", "beta": 0.60, "iv_rank": 19, "is_daily_core": False},
    "PG":   {"name_zh": "宝洁", "name_en": "Procter & Gamble", "sector": "必需消费与日用家化", "beta": 0.55, "iv_rank": 18, "is_daily_core": False},
    "NKE":  {"name_zh": "耐克", "name_en": "Nike", "sector": "非必需消费与运动品牌", "beta": 1.05, "iv_rank": 36, "is_daily_core": False},

    # 7. 工业机械与高端制造 (Industrials & Aerospace)
    "CAT": {"name_zh": "卡特彼勒", "name_en": "Caterpillar", "sector": "工业机械与重型装备", "beta": 1.15, "iv_rank": 34, "is_daily_core": False},
    "DE":  {"name_zh": "迪尔", "name_en": "Deere & Co", "sector": "工业机械与重型装备", "beta": 1.05, "iv_rank": 32, "is_daily_core": False},
    "UNP": {"name_zh": "联合太平洋", "name_en": "Union Pacific", "sector": "铁路运输与大宗物流", "beta": 0.85, "iv_rank": 25, "is_daily_core": False},
    "BA":  {"name_zh": "波音", "name_en": "Boeing", "sector": "航空航天与国防军工", "beta": 1.45, "iv_rank": 52, "is_daily_core": False},
    "LMT": {"name_zh": "洛克希德马丁", "name_en": "Lockheed Martin", "sector": "航空航天与国防军工", "beta": 0.60, "iv_rank": 22, "is_daily_core": False},
    "GE":  {"name_zh": "通用电气航天", "name_en": "GE Aerospace", "sector": "多元工业与能源装备", "beta": 1.10, "iv_rank": 35, "is_daily_core": False},

    # 8. 医疗健康与生命科学 (Healthcare & Life Sciences)
    "LLY":  {"name_zh": "礼来", "name_en": "Eli Lilly", "sector": "医疗健康与创新药", "beta": 0.72, "iv_rank": 28, "is_daily_core": False},
    "NVO":  {"name_zh": "诺和诺德", "name_en": "Novo Nordisk", "sector": "医疗健康与创新药", "beta": 0.70, "iv_rank": 26, "is_daily_core": False},
    "JNJ":  {"name_zh": "强生", "name_en": "Johnson & Johnson", "sector": "医疗健康与多元医药", "beta": 0.58, "iv_rank": 18, "is_daily_core": False},
    "PFE":  {"name_zh": "辉瑞", "name_en": "Pfizer", "sector": "医疗健康与多元医药", "beta": 0.65, "iv_rank": 22, "is_daily_core": False},
    "MRK":  {"name_zh": "默沙东", "name_en": "Merck", "sector": "医疗健康与创新药", "beta": 0.62, "iv_rank": 20, "is_daily_core": False},
    "ABBV": {"name_zh": "艾伯维", "name_en": "AbbVie", "sector": "医疗健康与创新药", "beta": 0.68, "iv_rank": 24, "is_daily_core": False},
    "UNH":  {"name_zh": "联合健康", "name_en": "UnitedHealth", "sector": "医疗健康与综合健康险", "beta": 0.75, "iv_rank": 25, "is_daily_core": False},
    "ISRG": {"name_zh": "直觉外科", "name_en": "Intuitive Surgical", "sector": "医疗器械与手术科技", "beta": 1.10, "iv_rank": 35, "is_daily_core": False},

    # 9. 金融服务与支付结算 (Financial Services & Payments)
    "JPM": {"name_zh": "摩根大通", "name_en": "JPMorgan Chase", "sector": "商业银行与多元金融", "beta": 1.05, "iv_rank": 28, "is_daily_core": False},
    "BAC": {"name_zh": "美国银行", "name_en": "Bank of America", "sector": "商业银行与多元金融", "beta": 1.15, "iv_rank": 32, "is_daily_core": False},
    "V":   {"name_zh": "Visa", "name_en": "Visa", "sector": "金融科技与支付结算", "beta": 0.95, "iv_rank": 25, "is_daily_core": False},
    "MA":  {"name_zh": "万事达", "name_en": "Mastercard", "sector": "金融科技与支付结算", "beta": 1.00, "iv_rank": 26, "is_daily_core": False},
    "GS":  {"name_zh": "高盛", "name_en": "Goldman Sachs", "sector": "投资银行与资产管理", "beta": 1.25, "iv_rank": 36, "is_daily_core": False},
    "MS":  {"name_zh": "摩根士丹利", "name_en": "Morgan Stanley", "sector": "投资银行与财富管理", "beta": 1.20, "iv_rank": 34, "is_daily_core": False},

    # 10. 能源与基础材料 (Energy & Materials)
    "XOM": {"name_zh": "埃克森美孚", "name_en": "ExxonMobil", "sector": "能源与石油石化", "beta": 0.82, "iv_rank": 28, "is_daily_core": False},
    "CVX": {"name_zh": "雪佛龙", "name_en": "Chevron", "sector": "能源与石油石化", "beta": 0.85, "iv_rank": 29, "is_daily_core": False},
    "LIN": {"name_zh": "林德气体", "name_en": "Linde", "sector": "基础工业气体与化工", "beta": 0.88, "iv_rank": 26, "is_daily_core": False},
    "SHW": {"name_zh": "宣伟", "name_en": "Sherwin-Williams", "sector": "特种材料与涂料化工", "beta": 1.02, "iv_rank": 30, "is_daily_core": False},

    # 11. 公用与清洁环保 (Utilities & Environmental)
    "WM":  {"name_zh": "废物管理", "name_en": "Waste Management", "sector": "环保与固废综合治理", "beta": 0.68, "iv_rank": 20, "is_daily_core": False},
    "NEE": {"name_zh": "新纪元能源", "name_en": "NextEra Energy", "sector": "公用事业与清洁电力", "beta": 0.70, "iv_rank": 22, "is_daily_core": False},
}


def clean_symbol_key(symbol: str) -> str:
    """Normalize any symbol variant (e.g., 'NVDA.US', 'nvda', 'NVDA') to uppercase bare ticker."""
    if not symbol:
        return ""
    return symbol.strip().upper().split(".")[0]


def get_stock_profile(symbol: str) -> Optional[Dict[str, Any]]:
    """Retrieve full registered profile for a stock symbol."""
    key = clean_symbol_key(symbol)
    return _REGISTRY_DATA.get(key)


def get_company_zh_name(symbol: str, fallback: Optional[str] = None) -> str:
    """Retrieve Chinese name with fallback to ticker or passed string."""
    key = clean_symbol_key(symbol)
    prof = _REGISTRY_DATA.get(key)
    if prof and prof.get("name_zh"):
        return prof["name_zh"]
    return fallback or key


def get_stock_sector(symbol: str, default: str = "核心科技与成长") -> str:
    """Retrieve verified sector classification."""
    key = clean_symbol_key(symbol)
    prof = _REGISTRY_DATA.get(key)
    if prof and prof.get("sector"):
        return prof["sector"]
    return default


def get_stock_beta(symbol: str, default: float = 1.0) -> float:
    """Retrieve default baseline Beta."""
    key = clean_symbol_key(symbol)
    prof = _REGISTRY_DATA.get(key)
    if prof and prof.get("beta") is not None:
        return float(prof["beta"])
    return default


def get_stock_iv_rank(symbol: str, default: int = 40) -> int:
    """Retrieve baseline implied volatility rank."""
    key = clean_symbol_key(symbol)
    prof = _REGISTRY_DATA.get(key)
    if prof and prof.get("iv_rank") is not None:
        return int(prof["iv_rank"])
    return default


def get_daily_core_symbols() -> List[str]:
    """Retrieve authoritative list of daily screener symbols in .US format."""
    symbols = []
    for ticker, meta in _REGISTRY_DATA.items():
        if meta.get("is_daily_core"):
            symbols.append(f"{ticker}.US")
    return symbols


def get_all_registered_stocks() -> List[Dict[str, Any]]:
    """List all registered stocks for frontend autocomplete and pool discovery."""
    result = []
    for ticker, meta in sorted(_REGISTRY_DATA.items()):
        result.append({
            "ticker": ticker,
            "symbol": f"{ticker}.US",
            "name_zh": meta["name_zh"],
            "name_en": meta["name_en"],
            "sector": meta["sector"],
            "beta": meta["beta"],
            "is_daily_core": meta["is_daily_core"],
        })
    return result


# Compatibility Dictionaries (drop-in replacements for existing code)
COMPANY_NAMES_ZH: Dict[str, str] = {}
STOCK_SECTOR_MAP: Dict[str, Dict[str, Any]] = {}

for _ticker, _meta in _REGISTRY_DATA.items():
    _zh = _meta["name_zh"]
    COMPANY_NAMES_ZH[_ticker] = _zh
    COMPANY_NAMES_ZH[f"{_ticker}.US"] = _zh

    _sec_info = {
        "sector": _meta["sector"],
        "beta": _meta["beta"],
        "iv_rank": _meta["iv_rank"],
    }
    STOCK_SECTOR_MAP[_ticker] = _sec_info
    STOCK_SECTOR_MAP[f"{_ticker}.US"] = _sec_info
