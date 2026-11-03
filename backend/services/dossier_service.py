"""
Dossier Service: Modular long-term research aggregation, zero-latency caching,
component-level hot refresh, and lightweight price sync.
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from backend.core.financial import analyze_capital_allocation_and_shareholder_yield
from backend.core.indicators import compute_technical_summary
from backend.core.utils import normalize_symbol, utc_now_iso
from backend.core.valuation import build_valuation_matrix
from backend.db import (
    delete_dossier,
    get_dossier,
    list_dossier_history,
    save_or_update_dossier,
    update_dossier_module,
    update_dossier_price,
)
from backend.services.ai_engine import generate_long_term_memo
from backend.services.company_kb import build_company_and_product_dossier
from backend.services.market_data import fetch_batch_quotes, fetch_stock_bundle


def get_or_create_dossier(symbol: str, force_refresh: bool = False) -> Dict[str, Any]:
    """
    Retrieve archived dossier with zero latency.
    If not cached or force_refresh is requested, build full multi-module dossier and persist.
    """
    sym = normalize_symbol(symbol)
    existing = get_dossier(sym)
    if not force_refresh:
        if existing and existing.get("modules"):
            mods = existing.get("modules", {})
            b_data = mods.get("business_and_industry", {}).get("data", {})
            p_data = mods.get("core_products", {}).get("data", {})
            m_memo = mods.get("ai_memo", {}).get("data", {})

            from backend.services.company_kb import PRESET_PRODUCT_KNOWLEDGE
            is_in_preset = sym in PRESET_PRODUCT_KNOWLEDGE
            is_old_essence = not isinstance(b_data.get("essence"), dict)
            is_old_preset = is_in_preset and not p_data.get("is_preset")
            is_missing_source_tag = not bool(b_data.get("source_tag") or b_data.get("essence", {}).get("source_tag"))

            v_data = mods.get("valuation_matrix", {}).get("data", {})
            has_stale_dcf = bool(v_data.get("dcf_fair_value") or v_data.get("intrinsic_value") or (v_data.get("margin_of_safety_pct") is not None))
            missing_new_val = not bool(v_data.get("multiples"))
            missing_financial_summary = not bool(v_data.get("financial_summary"))
            missing_klines = not bool(mods.get("technical_compass", {}).get("data", {}).get("klines"))

            c_data = mods.get("capital_allocation", {}).get("data", {})
            has_fake_coverage = c_data.get("balance_sheet_fortress", {}).get("interest_coverage_x") in (45.0, 16.5, 6.2)

            essence = b_data.get("essence") if isinstance(b_data.get("essence"), dict) else {}
            industry = b_data.get("industry") if isinstance(b_data.get("industry"), dict) else {}
            lifecycle = industry.get("lifecycle") if isinstance(industry.get("lifecycle"), dict) else {}
            characteristics = str(lifecycle.get("characteristics") or "")
            profit_engine = str(essence.get("profit_engine") or "")
            competitor_blob = " ".join(
                str(peer.get("name") or "")
                for peer in (industry.get("competitors") or [])
                if isinstance(peer, dict)
            )
            has_boilerplate = (
                "经营造血能力良好" in characteristics
                or "经营造血能力良好" in profit_engine
                or "主营产品销售与服务网络" in profit_engine
                or "标普500 核心同业集群" in competitor_blob
            )

            if not (is_old_essence or is_old_preset or is_missing_source_tag or has_stale_dcf or missing_new_val or missing_financial_summary or missing_klines or has_fake_coverage or has_boilerplate):
                try:
                    from backend.services.research_kb import get_stock_research_detail
                    existing["research_perspectives"] = get_stock_research_detail(sym)
                except Exception:
                    pass
                return existing

    # 1. Fetch live stock bundle from Longbridge CLI (minimal_extra enables sub-second fast loading)
    bundle = fetch_stock_bundle(sym, include_ai=False, include_extra=True, minimal_extra=True)
    quote = bundle.get("quote", {})
    price = quote.get("last")
    change_pct = quote.get("change_pct")
    company = bundle.get("company", {})
    name = company.get("name") or company.get("company_name") or sym
    financials = bundle.get("financials", {})
    valuation = bundle.get("valuation", {})
    technical = bundle.get("technical", {})
    rating = bundle.get("rating", {})
    klines = bundle.get("klines") or bundle.get("technical", {}).get("klines") or []
    if not klines:
        from backend.services.market_data import fetch_yahoo_klines
        klines = fetch_yahoo_klines(sym, count=260)

    now = utc_now_iso()

    # 2. Build Module 1 & 2: Business, Industry & Core Products Teardown
    prod_dossier = build_company_and_product_dossier(sym, company, financials, force_refresh=force_refresh)
    essence = prod_dossier.get("essence")
    if isinstance(essence, dict) and not essence.get("source_tag"):
        essence["source_tag"] = prod_dossier.get("source_tag")

    business_mod = {
        "updated_at": now,
        "data": {
            "symbol": sym,
            "company_name": name,
            "essence": essence,
            "industry": prod_dossier.get("industry"),
            "profile": company.get("profile"),
            "employees": company.get("employees"),
            "founded": company.get("founded"),
            "manager": company.get("manager"),
            "website": company.get("website"),
            "source_tag": prod_dossier.get("source_tag"),
            "is_preset": prod_dossier.get("is_preset", False)
        }
    }
    products_mod = {
        "updated_at": now,
        "data": {
            "symbol": sym,
            "company_name": name,
            "products": prod_dossier.get("products", []),
            "supply_chain": prod_dossier.get("supply_chain", {}),
            "is_preset": prod_dossier.get("is_preset", False)
        }
    }

    # 5. Build Module 5: Capital Allocation & Shareholder Yield (built before val_data enrichment)
    capital_data = analyze_capital_allocation_and_shareholder_yield(financials, valuation, quote)
    capital_mod = {
        "updated_at": now,
        "data": capital_data
    }

    # 3. Build Module 3: Valuation Matrix & Hard Financial Numbers
    val_data = build_valuation_matrix(sym, quote, valuation, financials)
    rating_dict = rating if isinstance(rating, dict) else {}
    fin_dict = financials if isinstance(financials, dict) else {}
    tech_dict = technical if isinstance(technical, dict) else {}
    
    val_data["price"] = price or quote.get("current_price") or quote.get("close") or (klines[-1]["close"] if klines else None)
    val_data["target_price"] = rating_dict.get("target_price")
    val_data["target_upside_pct"] = rating_dict.get("target_price_upside_pct")
    val_data["rating_label"] = rating_dict.get("consensus_rating_label")
    val_data["returns_20d"] = tech_dict.get("returns", {}).get("20d") if isinstance(tech_dict.get("returns"), dict) else None
    val_data["trailing_stop_2atr"] = tech_dict.get("trailing_stop_2atr")
    val_data["financials_summary"] = {
        "revenue": fin_dict.get("revenue"),
        "revenue_yoy": fin_dict.get("revenue_growth_yoy"),
        "net_income": fin_dict.get("net_income"),
        "net_income_yoy": fin_dict.get("net_income_growth_yoy"),
        "debt_to_assets": fin_dict.get("debt_to_assets") or (capital_data.get("balance_sheet", {}).get("debt_to_assets_pct") if capital_data else None),
    }
    val_data["financial_summary"] = val_data["financials_summary"]

    valuation_mod = {
        "updated_at": now,
        "data": val_data
    }

    # 4. Build Module 4: Technical Compass with Plain-Language Dictionary
    if klines and "klines" not in technical:
        technical["klines"] = klines
    technical_mod = {
        "updated_at": now,
        "data": technical
    }

    # 6. Build Module 6: Institutional Buy-Side Investment Memo
    # Decouple heavy LLM generation from initial dossier load:
    # If a completed memo already exists in DB, preserve it; otherwise return a pending state
    # so user gets full financial facts, valuation matrix, DuPont analysis, and capital allocation in < 1.5s.
    existing_memo = None
    if existing and existing.get("modules", {}).get("ai_memo", {}).get("data"):
        m = existing["modules"]["ai_memo"]["data"]
        if m.get("memo") and not m.get("pending") and m.get("ic_verdict"):
            existing_memo = m

    if existing_memo:
        ai_memo_mod = {
            "updated_at": existing.get("modules", {}).get("ai_memo", {}).get("updated_at", now),
            "data": existing_memo
        }
    else:
        ai_memo_mod = {
            "updated_at": now,
            "data": {
                "symbol": sym,
                "company_name": name,
                "model_used": "Gemini 2.5 Flash + Grok Dual-Audit",
                "pending": True,
                "status": "PENDING_REVIEW",
                "memo": "AI 投研备忘录待生成。长桥行情与多维财务基本盘已就绪，点击下方【⚡ 一键生成买方投资备忘录】即可启动大模型双轮深度审计。"
            }
        }

    modules = {
        "business_and_industry": business_mod,
        "core_products": products_mod,
        "valuation_matrix": valuation_mod,
        "technical_compass": technical_mod,
        "capital_allocation": capital_mod,
        "ai_memo": ai_memo_mod
    }

    val_status = val_data.get("status", "评估中")
    margin_pct = val_data.get("margin_of_safety_pct", 0.0)

    # Persist in SQLite
    res = save_or_update_dossier(
        symbol=sym,
        name=name,
        price=price,
        change_pct=change_pct,
        valuation_status=val_status,
        margin_of_safety_pct=margin_pct,
        modules_dict=modules
    )
    try:
        from backend.services.research_kb import get_stock_research_detail
        res["research_perspectives"] = get_stock_research_detail(sym)
    except Exception:
        pass
    return res


def refresh_dossier_module(symbol: str, module_name: str) -> Dict[str, Any]:
    """
    Granularly re-generate or re-fetch only the specified module without touching others.
    """
    sym = normalize_symbol(symbol)
    existing = get_dossier(sym)
    if not existing:
        return get_or_create_dossier(sym, force_refresh=True)

    bundle = fetch_stock_bundle(
        sym,
        include_ai=False,
        include_extra=(module_name in ("business_and_industry", "core_products", "valuation_matrix", "capital_allocation", "ai_memo")),
        minimal_extra=True
    )
    quote = bundle.get("quote", {})
    company = bundle.get("company", {})
    name = existing.get("name") or company.get("name") or sym
    financials = bundle.get("financials", {})
    valuation = bundle.get("valuation", {})
    technical = bundle.get("technical", {})

    if module_name == "business_and_industry":
        prod_dossier = build_company_and_product_dossier(sym, company, financials, force_refresh=True)
        payload = {
            "symbol": sym,
            "company_name": name,
            "essence": prod_dossier.get("essence"),
            "industry": prod_dossier.get("industry"),
            "profile": company.get("profile"),
            "employees": company.get("employees"),
            "founded": company.get("founded"),
            "manager": company.get("manager"),
            "website": company.get("website")
        }
    elif module_name == "core_products":
        prod_dossier = build_company_and_product_dossier(sym, company, financials, force_refresh=True)
        payload = {
            "symbol": sym,
            "company_name": name,
            "products": prod_dossier.get("products", []),
            "supply_chain": prod_dossier.get("supply_chain", {}),
            "is_preset": prod_dossier.get("is_preset", False)
        }
    elif module_name == "valuation_matrix":
        payload = build_valuation_matrix(sym, quote, valuation, financials)
    elif module_name == "technical_compass":
        payload = technical
    elif module_name == "capital_allocation":
        payload = analyze_capital_allocation_and_shareholder_yield(financials, valuation, quote)
    elif module_name == "ai_memo":
        prod_dossier = build_company_and_product_dossier(sym, company, financials)
        val_data = build_valuation_matrix(sym, quote, valuation, financials)
        payload = generate_long_term_memo(
            symbol=sym,
            bundle=bundle,
            products_data=prod_dossier,
            valuation_data=val_data,
            model_name="cross"
        )
    else:
        raise ValueError(f"Unknown module name: {module_name}")

    updated = update_dossier_module(sym, module_name, payload)
    return {
        "ok": True,
        "symbol": sym,
        "module": module_name,
        "module_entry": updated
    }


def hot_sync_price_and_technicals(symbol: str) -> Dict[str, Any]:
    """
    Sub-second sync of current market price and technical indicators without touching deep research cards.
    """
    sym = normalize_symbol(symbol)
    bundle = fetch_stock_bundle(sym, include_ai=False, include_extra=False)
    quote = bundle.get("quote", {})
    p = quote.get("last")
    chg = quote.get("change_pct")
    technical = bundle.get("technical", {})

    existing = get_dossier(sym)
    val_data = None
    if existing:
        old_val_data = existing.get("modules", {}).get("valuation_matrix", {}).get("data", {})
        if old_val_data and p:
            val_data = dict(old_val_data)
            val_data["current_price"] = p

    res = update_dossier_price(sym, price=p, change_pct=chg, technical_data=technical, valuation_data=val_data)
    return {
        "ok": True,
        "symbol": sym,
        "price": p,
        "change_pct": chg,
        "dossier": res or get_or_create_dossier(sym)
    }
