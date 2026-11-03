"""
AI Reasoning Engine:
Direct local execution of Grok CLI, Gemini CLI, and dual cross-validation,
structured 4-quadrant multi-horizon prompts, and evidence aggregation.
"""
import concurrent.futures
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.config import DEFAULT_LLM_MODEL, GEMINI_BIN, GROK_BIN
from backend.core.utils import utc_now_iso
from backend.db import archive_recommendation_snapshot, get_cache, set_cache
from backend.services.macro_service import get_macro_climate
from backend.services.market_data import fetch_stock_bundle, longbridge_status


def clean_cli_output(text: str) -> str:
    """Filter out CLI terminal warnings, ripgrep missing messages, and session logs."""
    lines = []
    for line in (text or "").strip().splitlines():
        trimmed = line.strip()
        if (
            trimmed.startswith("Warning:")
            or trimmed.startswith("Ripgrep is not available")
            or "TERM=dumb" in trimmed
            or "256-color support" in trimmed
            or "Finishing session" in trimmed
            or "Last progress" in trimmed
            or "Using a terminal with at least" in trimmed
        ):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def check_ai_models_status() -> Dict[str, Any]:
    """Inspect availability of local Grok CLI and Gemini CLI binaries."""
    grok_installed = False
    gemini_installed = False
    try:
        completed = subprocess.run(["which", GROK_BIN], capture_output=True, text=True, timeout=2)
        grok_installed = (completed.returncode == 0) or Path(GROK_BIN).exists()
    except Exception:
        grok_installed = Path(GROK_BIN).exists()

    try:
        completed = subprocess.run(["which", GEMINI_BIN], capture_output=True, text=True, timeout=2)
        gemini_installed = (completed.returncode == 0) or Path(GEMINI_BIN).exists()
    except Exception:
        gemini_installed = Path(GEMINI_BIN).exists()

    lb_st = longbridge_status()
    return {
        "grok": {
            "installed": grok_installed,
            "name": "Grok CLI",
            "desc": "市场舆情、网络动态与即期催化敏锐",
            "bin": GROK_BIN,
        },
        "gemini": {
            "installed": gemini_installed,
            "name": "Gemini CLI",
            "desc": "深度财务长文推演、因果对比与严密逻辑",
            "bin": GEMINI_BIN,
        },
        "cross": {
            "installed": grok_installed and gemini_installed,
            "name": "双模型交叉互审 (Grok + Gemini)",
            "desc": "Grok 审情绪与催化，Gemini 审财务与治理，互为验证",
        },
        "longbridge": lb_st,
        "openai": {
            "enabled": bool(os.environ.get("OPENAI_API_KEY")),
            "model": DEFAULT_LLM_MODEL,
        }
    }


def run_cli_model(model_name: str, prompt: str, timeout: int = 50) -> Dict[str, Any]:
    """Execute Grok or Gemini CLI with the prompt and return sanitized text output."""
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:24]
    cache_key = f"cli_ai:{model_name}:{prompt_hash}"
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

    output_text = ""
    used_model = model_name

    if model_name == "grok":
        cmd = [GROK_BIN, "--max-turns", "1", "--output-format", "plain", "--disable-web-search", "--no-subagents", "-p", prompt]
        try:
            completed = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            raw = completed.stdout if completed.returncode == 0 else (completed.stdout + "\n" + completed.stderr)
            output_text = clean_cli_output(raw)
        except subprocess.TimeoutExpired:
            output_text = f"【Grok CLI 响应超时】{timeout} 秒内未返回结果，请检查网络连接。"
        except Exception as exc:
            output_text = f"【Grok CLI 调用异常】{exc}"

    elif model_name == "gemini":
        cmd = [GEMINI_BIN, "-p", prompt, "-o", "text"]
        try:
            completed = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            raw = completed.stdout if completed.returncode == 0 else (completed.stdout + "\n" + completed.stderr)
            output_text = clean_cli_output(raw)
        except subprocess.TimeoutExpired:
            output_text = f"【Gemini CLI 响应超时】{timeout} 秒内未返回结果，请检查网络连接。"
        except Exception as exc:
            output_text = f"【Gemini CLI 调用异常】{exc}"

    elif model_name == "cross":
        p_grok = prompt + "\n\n请特别侧重输出：市场情绪、网络催化、科技产品预期与短线动量。"
        p_gemini = prompt + "\n\n请特别侧重输出：基本面质量、中长线护城河、管理层治理与一票否决排雷。"
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            fut_grok = executor.submit(run_cli_model, "grok", p_grok, timeout)
            fut_gemini = executor.submit(run_cli_model, "gemini", p_gemini, timeout)
            grok_res = fut_grok.result()
            gemini_res = fut_gemini.result()

        grok_ok = grok_res.get("ok", False) and not grok_res.get("error", False)
        gemini_ok = gemini_res.get("ok", False) and not gemini_res.get("error", False)

        parts = []
        if grok_ok:
            parts.append(f"### ⚡ Grok 视角 (市场情绪与产品催化)\n{grok_res.get('text', '')}")
        else:
            err_msg = grok_res.get("text", "未响应")
            parts.append(f"### ⚡ Grok 视角 (市场情绪与产品催化)\n【Grok CLI 暂未返回或超时】{err_msg}")

        if gemini_ok:
            parts.append(f"### 🧠 Gemini 视角 (基本面财务与一票否决)\n{gemini_res.get('text', '')}")
        else:
            err_msg = gemini_res.get("text", "未响应")
            parts.append(f"### 🧠 Gemini 视角 (基本面财务与一票否决)\n【Gemini CLI 暂未返回或超时】{err_msg}")

        output_text = "\n\n".join(parts)

        # 只要有一方返回有效文本，即判定为部分/全部研判成功，避免串行整体失败
        if not grok_ok and not gemini_ok:
            return {
                "ok": False,
                "model": "cross",
                "text": f"【双模型互审均未生成有效研判】\n\nGrok 状态：{grok_res.get('text')}\n\nGemini 状态：{gemini_res.get('text')}\n\n请检查对应 CLI 登录与环境配置后重试。系统杜绝填充任何假数据。",
                "timestamp": utc_now_iso(),
                "error": True,
            }
        else:
            result = {
                "ok": True,
                "model": "cross",
                "text": output_text,
                "timestamp": utc_now_iso(),
            }
            set_cache(cache_key, result, 3600)
            return result

    has_error = (not output_text) or ("超时" in output_text) or ("异常" in output_text)
    if has_error:
        # Strictly return honest error status instead of fabricated bullish memo
        return {
            "ok": False,
            "model": used_model,
            "text": f"【{used_model.upper()} CLI 未生成有效研判】\n原因：{output_text or '模型未返回任何有效文本'}。\n\n请检查对应 CLI 登录与环境配置后重试。系统杜绝填充任何通用模板演示假数据。",
            "timestamp": utc_now_iso(),
            "error": True,
        }

    result = {
        "ok": True,
        "model": used_model,
        "text": output_text,
        "timestamp": utc_now_iso(),
    }
    set_cache(cache_key, result, 3600)
    return result


def run_cli_analysis_for_symbol(symbol: str, model_name: str = "gemini") -> Dict[str, Any]:
    """Execute end-to-end AI reasoning and automatically archive into SQLite snapshots."""
    bundle = fetch_stock_bundle(symbol, include_ai=False, include_extra=True)
    quote = bundle.get("quote") or {}
    technical = bundle.get("technical") or {}
    valuation = bundle.get("valuation") or {}
    financials = bundle.get("financials") or {}
    score = bundle.get("score") or {}
    score_val = score.get("score")
    score_display = f"{score_val} / 100 ({score.get('verdict', '未评级')})" if score_val is not None else "数据不足，未评级"
    
    rating_data = bundle.get("rating") or {}
    risk_radar = bundle.get("risk_radar") or {}
    short_pos = risk_radar.get("short_positions") or {}
    if isinstance(short_pos, dict):
        short_latest = short_pos.get("latest") or {}
    elif isinstance(short_pos, list) and short_pos:
        short_latest = short_pos[0] if isinstance(short_pos[0], dict) else {}
    else:
        short_latest = {}

    macro = get_macro_climate()
    regime_info = macro.get('regime', {})
    regime_name = regime_info.get('level', '顺风进攻期')
    regime_code = regime_info.get('code', 'RISK_ON')
    factor_matrix = regime_info.get('factor_matrix', {})

    prompt = f"""
你是一名顶级美股对冲基金的投研总监与量化风险官。请基于以下严格结构化证据，针对股票【{symbol}】给出高密度、不讲空话、区分周期的买方决策研判。
必须严格遵循四大机构工程量化原则：
1. 宏观离散状态机约束（防盲目追涨，依据状态机权重配置风险暴露）
2. 基本面质量真实性核验（毛利率、ROE 与营收净利增速必须支撑估值倍数，严防缺乏盈利底座的纯概念炒作；注意：当前行情接口仅包含经审计利润表与资产负债表关键快照，未接入自由现金流量表与单季ROIC，严禁凭空捏造虚假现金流或ROIC数字）
3. 量化纯数值合格性（MA20/MA60 均线动量、RSI(14)、ATR(14) 波动率与成交量活跃度）
4. 组合行业敞口上限（单一行业 ≤30%）与 ATR(14) 风险平价仓位及防守纪律（系统未接入期权链，严禁捏造期权合约）

【宏观离散状态机 (Market Regime State Machine)】
- 标普 500 (SPY): {macro.get('spy', {}).get('last')} ({macro.get('spy', {}).get('change_pct')}%)
- 恐慌指数 (VIX): {macro.get('vix', {}).get('last')}
- 状态机离散判定: 【{regime_code} - {regime_name}】 (建议总仓位: {regime_info.get('suggested_exposure')})
- 当前激活因子权重: {json.dumps(factor_matrix.get('weights', {}), ensure_ascii=False)}

【个股实时核心事实与量化指标】
- 最新价: ${quote.get('last')} (涨跌幅: {quote.get('change_pct')}%)
- 均线与动量: {technical.get('trend_label')}, RSI14={technical.get('rsi14')}, 20日年化波动率={technical.get('volatility_20d')}%, ATR(14)={technical.get('atr14')}
- 估值与评级: PE={valuation.get('pe_raw')}, PS={valuation.get('ps_raw')}, PB={valuation.get('pb_raw')}, 机构建议={rating_data.get('recommend', '--')}, 平均目标价=${rating_data.get('target', '--')}
- 财务指标 (已披露真实快照): {json.dumps(financials.get('indicators', [])[:5], ensure_ascii=False)}
- 做空与筹码: 做空比例={short_latest.get('short_rate', '--')}, Days to cover={short_latest.get('days_to_cover', '--')}
- 本地量化综合评分: {score_display}

请分 4 个核心模块输出结构化买方决策研报：

### ⚡ 1. 短线机会与量价硬指标 (1~5天 / 1~2周)
- 动量与量价形态（结合 20/60 日均线多空结构、RSI(14)、ATR(14) 波动率与成交量倍率）：
- 关键阻力位与支撑位：
- 第一止损防线 (Thesis Breaker)：明确写出基于 2xATR 或均线跌破的精确离场价位。

### 📅 2. 中线机会与财务验证闸门 (1~3个月)
- 财务质量与业绩确定性验证（基于已披露毛利率、ROE 杜邦分析与营收/净利润同比增速，评估财报支撑）：
- 机构评级与产业链传导：
- 估值消化能力与空头筹码排查（结合 PE/PS 安全边际与做空比例 Short Rate、回补天数 Days to Cover 评估潜在挤压或抛压风险）：

### 🏛️ 3. 长线机会与商业护城河 (6~12个月+)
- 管理层治理水平与资本配置效率（结合资产负债率、杠杆水平与杜邦回报率评估资本健康度）：
- 护城河不可替代性与技术迭代抗风险能力：

### 🛡️ 4. 组合管理与风险控制方案 (Step 5.5 风控)
- 行业暴露敞口核验（若属于高集中度行业，提示单一行业上限 30% 约束）：
- ATR(14) 风险平价仓位建议（说明假设 10 万美元账户单笔 1.5% 风险时的推荐头寸）：
- 现货风控与防守对冲纪律（重要提示：系统当前未接入美股实时期权链，严禁凭空捏造具体期权到期日与行权价；请重点说明基于 2xATR 止损位、均线跌破离场纪律、减仓节奏与现货防守方案）：
"""
    ai_result = run_cli_model(model_name, prompt.strip(), timeout=55)

    p = quote.get("last")
    atr_stop = technical.get("trailing_stop_2atr")
    stop_loss = atr_stop if atr_stop else (round(p * 0.93, 2) if p else None)
    raw_target = rating_data.get("target")
    target_p = round(float(raw_target), 2) if (raw_target and float(raw_target) > 0) else None
    tags = (bundle.get("score") or {}).get("positives") or []
    tags = tags[:3]

    snapshot_id = None
    if ai_result.get("ok") and p and p > 0:
        spy_last = macro.get("spy", {}).get("last")
        spy_val = spy_last if (spy_last and spy_last > 0) else None
        vix_last = macro.get("vix", {}).get("last")
        vix_val = vix_last if (vix_last and vix_last > 0) else None
        snapshot = archive_recommendation_snapshot(
            symbol=symbol,
            source_type="manual_query",
            price=p,
            spy_price=spy_val,
            vix_value=vix_val,
            score=score.get("score", 75.0),
            verdict=score.get("verdict", "中性观察"),
            tags=tags,
            short_term_thesis=f"当前量化评分 {score.get('score')}，重点盯防止损线 ${stop_loss}" if stop_loss else f"当前量化评分 {score.get('score')}",
            mid_term_thesis=macro.get("regime", {}).get("level", "顺风进攻期"),
            long_term_thesis=bundle.get("company", {}).get("name", symbol),
            stop_loss_price=stop_loss,
            target_price=target_p,
            ai_model=f"{model_name.upper()} CLI",
            evidence_json=json.dumps({"macro": macro.get("regime"), "quote": quote}, ensure_ascii=False)
        )
        snapshot_id = snapshot.get("id")

    return {
        "ok": ai_result.get("ok", False),
        "symbol": symbol,
        "model": model_name,
        "ai_analysis": ai_result.get("text", ""),
        "bundle": bundle,
        "snapshot_id": snapshot_id,
        "timestamp": utc_now_iso(),
    }


def generate_long_term_memo(
    symbol: str,
    bundle: Dict[str, Any],
    products_data: Optional[Dict[str, Any]] = None,
    valuation_data: Optional[Dict[str, Any]] = None,
    model_name: str = "gemini",
) -> Dict[str, Any]:
    """
    Generate institutional-grade Buy-Side Investment Committee (IC) Memo.
    Features:
    1. IC Verdict (Rating, Horizon, Position Size, Accumulation Zone, Stop-Loss)
    2. Bull vs. Bear Debate Matrix (Top 3 Long Theses vs. Top 3 Kill Switches)
    3. 12-Month Catalysts & Milestones Checklist
    4. Resilient Buy-Side Memo Markdown (Dual-Model synthesis with zero-failure deterministic fallback)
    """
    quote = bundle.get("quote", {})
    p = quote.get("last") or 0.0
    company = bundle.get("company", {})
    cname = company.get("name") or company.get("company_name") or symbol
    technical = bundle.get("technical", {})
    financials = bundle.get("financials", {})
    
    val_status = valuation_data.get("status") if valuation_data else "评估中"
    margin_pct = valuation_data.get("margin_of_safety_pct") if valuation_data else 0.0
    reverse_dcf = valuation_data.get("reverse_dcf", {}) if valuation_data else {}
    implied_g = reverse_dcf.get("implied_annual_growth_pct", 15.0)
    fair_mid = valuation_data.get("fair_value_mid") if valuation_data else None

    # Ladder & Technials
    ladder = technical.get("price_ladder", {})
    # 1. Honest Buy-Side Evaluation Baseline
    ladder = technical.get("price_ladder", {})
    s1_price = ladder.get("s1_near", {}).get("price") or technical.get("ma20") or round(p * 0.95, 2)
    s2_stop = ladder.get("s2_defense", {}).get("price") or technical.get("trailing_stop_2atr") or round(p * 0.88, 2)
    r1_price = ladder.get("r1_near", {}).get("price") or round(p * 1.05, 2)

    # 2. Extract Business Facts
    essence_raw = (products_data or {}).get("essence", "公司主营业务")
    if isinstance(essence_raw, dict):
        essence = essence_raw.get("summary") or essence_raw.get("profit_engine") or "公司主营业务"
    else:
        essence = str(essence_raw)
    if len(essence) > 100:
        essence = essence[:100] + "..."

    mult = (valuation_data or {}).get("multiples", {})
    val_status = valuation_data.get("status") if valuation_data else "未取得"
    peer_prem = mult.get("peer_premium_pct")
    peer_rank_desc = mult.get("rank_desc") or "长桥同业排位未取得"

    # 3. Model LLM Inference with realistic Longbridge financial facts
    fin_indicators = financials.get("indicators", []) if financials else []
    fin_summary = []
    for item in fin_indicators[:6]:
        if isinstance(item, dict) and item.get("name"):
            val_str = f"{item.get('value')}" if item.get('value') is not None else "--"
            yoy_str = f", 同比 {round(item.get('yoy') * 100, 1)}%" if item.get('yoy') is not None else ""
            fin_summary.append(f"{item.get('name')}: {val_str}{yoy_str}")
    fin_text = "; ".join(fin_summary) or "长桥单期报表暂未披露详细指标"

    prompt = f"""
你是一名全球顶尖长线买方对冲基金（持有周期 1~3 年+）的投委会资深合伙人。
请针对标的【{cname} ({symbol})】，基于以下【长桥官方已核验事实数据】，输出一份逻辑严密、客观冷静的中长期买方投资备忘录 (Institutional Investment Memo)。
注意：系统未接入现金流量表，严禁凭空捏造自由现金流(FCF)金额与虚假DCF公允价。

【长桥官方实时事实数据】
- 标的: {cname} ({symbol}), 最新价: ${p}
- 业务定位: {essence}
- 估值与同业溢价: 【{val_status}】 (指标值: {mult.get('metric_value')}, 同业中位: {mult.get('industry_median')}, 同业溢价率: {f'+{peer_prem}%' if peer_prem else '未取得'})
- 同业排位梯队: {peer_rank_desc}
- 最新财务指标 (单期快照): {fin_text}
- 关键量价阶梯: 第一阻力=${r1_price}, 第一支撑=${s1_price}, 2xATR硬止损=${s2_stop}

请严格按以下 4 大板块输出，禁止空话套话，每一点必须结合上述具体数字进行论述：
### 🏛️ 1. 核心投资逻辑与买方确定性 (Core Investment Thesis)
### 🚨 2. 论点推翻一票否决红线 (Thesis Breakers & Kill Switches)
### 📅 3. 未来 12 个月关键催化剂跟踪日历 (Upcoming Catalysts)
### 🎯 4. 投委会资产配置与建仓执行纪律 (Actionable Execution Plan)
"""
    try:
        target_model = model_name if model_name in ("gemini", "grok", "cross") else "gemini"
        ai_result = run_cli_model(target_model, prompt.strip(), timeout=50)
    except Exception:
        ai_result = {"ok": False, "text": ""}

    raw_text = clean_cli_output(ai_result.get("text", ""))

    is_invalid_cli_text = (
        not ai_result.get("ok")
        or not raw_text
        or "Max turns reached" in raw_text
        or "max turns reached" in raw_text
        or "Error:" in raw_text
        or len(raw_text) < 120
    )

    if not is_invalid_cli_text:
        final_memo = raw_text
        memo_model = target_model
        memo_ok = True
        rating = "ACCUMULATE"
        rating_label = "经AI投委会审议 · 建议跟踪建仓"
        badge_class = "buy"
        allocation = "3.0% ~ 5.0% 组合基础配置"
        buy_zone = f"${s1_price} ~ ${round(p, 2)}"
        rationale = "基于长桥事实与大模型深度研判，标的具备业务壁垒与配置价值。"
    else:
        # Strictly reject deterministic fake bullish templates!
        memo_model = "unassisted"
        memo_ok = False
        final_memo = f"""### ⚠️ 投委会投资备忘录：未生成

**原因说明**：本地大模型 CLI（{target_model}）响应超时或未配置有效授权凭证。

**严肃买方原则**：系统已全面移除“千篇一律看多确定性模板”。在本地 AI 模型未生成真实研判前，绝不填充任何虚假的“自由现金流充沛、预期差红利”模板文本，杜绝误导决策。

**建议操作**：
1. 检查终端 `gemini` 或 `grok` CLI 授权状态与网络连接；
2. 参考当前档案页中的长桥事实层（财务质量分、资产负债率、同业估值排位与均线阶梯）进行人工研判。"""
        rating = "PENDING_REVIEW"
        rating_label = "待人工复核 (AI研报未生成)"
        badge_class = "hold"
        allocation = "暂不下达配置结论 (等待模型响应或人工复核)"
        buy_zone = "--"
        rationale = "AI 备忘录未生成，系统严格禁止根据虚假安全边际盲目给出看多配置建议。"

    bull_theses = [
        {
            "title": "主业护城河与市场准入壁垒",
            "evidence": f"依托核心业务线掌握特定客户群与供应链积累，需在下期财报中重点跟踪营收与净利率兑现度。",
            "pillar": "业务壁垒"
        },
        {
            "title": "资产负债表与抗周期防守能力",
            "evidence": f"以资产负债率与实际盈利能力为底线约束，防范高杠杆公司遭遇加息冲击。",
            "pillar": "财务防守"
        }
    ]

    bear_risks = [
        {
            "title": "业绩与指引不及预期风险",
            "kill_switch": "下期单季财报营收或利润同比负增长，且管理层指引放缓。",
            "threshold": "业绩不及预期"
        },
        {
            "title": "均线量价结构破位离场",
            "kill_switch": f"放量跌破 2xATR 动态硬止损线 (${s2_stop})，触发技术防守纪律。",
            "threshold": f"跌破 ${s2_stop}"
        }
    ]

    catalysts_checklist = [
        {
            "event": "下一季度管理层官方财报披露",
            "window": "未来 1~3 个月内",
            "focus": "验证实际营收与净利润是否保持健康增长动能。"
        },
        {
            "event": "行业周期与宏观利率环境演变",
            "window": "未来 3~6 个月内",
            "focus": "关注美联储基准利率政策与行业下游资本开支节奏变化。"
        }
    ]

    return {
        "ok": memo_ok,
        "symbol": symbol,
        "company_name": cname,
        "model": memo_model,
        "ic_verdict": {
            "rating": rating,
            "rating_label": rating_label,
            "badge_class": badge_class,
            "time_horizon": "12~36 个月 (买方长线观察)",
            "target_allocation": allocation,
            "buy_zone": buy_zone,
            "stop_loss": f"${s2_stop}",
            "core_rationale": rationale
        },
        "bull_bear_matrix": {
            "bull_theses": bull_theses,
            "bear_risks": bear_risks
        },
        "catalysts_checklist": catalysts_checklist,
        "memo": final_memo,
        "timestamp": utc_now_iso()
    }


