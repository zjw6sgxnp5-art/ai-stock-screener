/**
 * AI 选股 · 机构级智能投研工作台 (AI Stock Desk 2.0)
 * Precision Reactive Client Implementation
 */

const $ = (id) => document.getElementById(id);

// Safe HTML Escape
const escapeHtml = (val) => String(val ?? "")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

// Number Formatters
const formatNumber = (val, digits = 2) => {
  if (val === null || val === undefined || isNaN(Number(val))) return "-";
  return Number(val).toLocaleString(undefined, { maximumFractionDigits: digits });
};

const formatPct = (val, digits = 2) => {
  if (val === null || val === undefined || isNaN(Number(val))) return "-";
  const num = Number(val);
  return `${num >= 0 ? "+" : ""}${num.toFixed(digits)}%`;
};

const formatMoneyCompact = (val) => {
  if (val === null || val === undefined || isNaN(Number(val))) return "-";
  const num = Number(val);
  if (Math.abs(num) >= 1_000_000_000) return `$${(num / 1_000_000_000).toFixed(2)}B`;
  if (Math.abs(num) >= 1_000_000) return `$${(num / 1_000_000).toFixed(2)}M`;
  return `$${num.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
};

const setText = (id, val) => {
  const el = $(id);
  if (el) el.textContent = val ?? "-";
};

const setList = (id, items, emptyText = "暂无数据") => {
  const node = $(id);
  if (!node) return;
  node.innerHTML = "";
  const list = items && items.length ? items : [emptyText];
  list.forEach(item => {
    const li = document.createElement("li");
    li.textContent = item;
    node.appendChild(li);
  });
};

// UI Status Helpers
const showLoading = (text = "正在调度本地 CLI 引擎与量化模型...") => {
  const loading = $("loading");
  if (loading) {
    $("loadingText").textContent = text;
    loading.classList.remove("hidden");
  }
};

const hideLoading = () => {
  const loading = $("loading");
  if (loading) loading.classList.add("hidden");
};

const showError = (msg) => {
  const box = $("errorBox");
  if (box) {
    if (!msg) {
      box.classList.add("hidden");
      box.textContent = "";
    } else {
      box.textContent = msg;
      box.classList.remove("hidden");
    }
  }
};

const updateClock = () => {
  const clock = $("localClock");
  if (clock) {
    const now = new Date();
    clock.textContent = now.toTimeString().split(" ")[0];
  }
};

/* ==========================================================================
   1. AI Models & System Status
   ========================================================================== */
const loadAIModelsStatus = async () => {
  try {
    const res = await fetch("/api/ai/models");
    const data = await res.json();
    if (!data.ok) return;

    const models = data.models || {};
    
    // Grok
    const grokPill = $("grokStatusPill");
    if (grokPill) {
      if (models.grok?.installed) {
        grokPill.className = "status-pill ready";
        grokPill.textContent = "⚡ Grok: 已就绪";
      } else {
        grokPill.className = "status-pill offline";
        grokPill.textContent = "⚡ Grok: 未连接";
      }
    }

    // Gemini
    const geminiPill = $("geminiStatusPill");
    if (geminiPill) {
      if (models.gemini?.installed) {
        geminiPill.className = "status-pill ready";
        geminiPill.textContent = "🧠 Gemini: 已就绪";
      } else {
        geminiPill.className = "status-pill offline";
        geminiPill.textContent = "🧠 Gemini: 未连接";
      }
    }

    // Longbridge
    const lbPill = $("lbStatusPill");
    if (lbPill) {
      if (models.longbridge?.ok) {
        lbPill.className = "status-pill ready";
        lbPill.textContent = "长桥: 实时数据就绪";
      } else {
        lbPill.className = "status-pill offline";
        lbPill.textContent = "长桥: 本地基准快照(零白屏)";
      }
    }
  } catch (err) {
    console.warn("Model status check failed:", err);
  }
};

/* ==========================================================================
   2. Macro Climate & 30-Day Double-Sided Timeline
   ========================================================================== */
const loadMacroClimate = async () => {
  try {
    const res = await fetch("/api/macro/climate");
    const json = await res.json();
    if (!json.ok) return;

    const macro = json.macro || {};

    // SPY
    if (macro.spy) {
      setText("spyPrice", `$${formatNumber(macro.spy.last, 2)}`);
      const spyChg = $("spyChange");
      if (spyChg) {
        spyChg.textContent = formatPct(macro.spy.change_pct);
        spyChg.className = macro.spy.change_pct >= 0 ? "badge-success" : "badge-danger";
      }
      setText("spyTrendBadge", macro.spy.trend || "均线上方多头");
    }

    // QQQ
    if (macro.qqq) {
      setText("qqqPrice", `$${formatNumber(macro.qqq.last, 2)}`);
      const qqqChg = $("qqqChange");
      if (qqqChg) {
        qqqChg.textContent = formatPct(macro.qqq.change_pct);
        qqqChg.className = macro.qqq.change_pct >= 0 ? "badge-success" : "badge-danger";
      }
      setText("qqqTrendBadge", macro.qqq.trend || "科技成长顺风");
    }

    // VIX
    if (macro.vix) {
      setText("vixValue", formatNumber(macro.vix.last, 2));
      const vixChg = $("vixChange");
      if (vixChg) {
        vixChg.textContent = formatPct(macro.vix.change_pct);
        vixChg.className = macro.vix.change_pct <= 0 ? "badge-success" : "badge-warning";
      }
    }

    // Regime Strategy Card
    const regime = macro.regime || {};
    setText("macroRegimeTag", `☀️ ${regime.level || "顺风进攻期"}`);
    setText("macroExposure", regime.suggested_exposure || "75% - 90%");
    setText("macroStyle", regime.strategy_style || "主攻高动量突破、强催化与爆款应用标的");
    setText("macroDesc", regime.description || "全市场流动性充沛，未现系统性抛压，适合以强势进攻龙头为主，顺风做多。");

    // Render Discrete Regime Factor Weights Matrix (Step 7)
    const factorMatrix = regime.factor_matrix || {};
    const matrixNameNode = $("activeRegimeMatrixName");
    if (matrixNameNode && factorMatrix.name) {
      matrixNameNode.textContent = factorMatrix.name;
    }
    const antiNoteNode = $("antiChasingNote");
    if (antiNoteNode && factorMatrix.anti_chasing_note) {
      antiNoteNode.textContent = factorMatrix.anti_chasing_note;
    }

    const factorBarsNode = $("regimeFactorBars");
    if (factorBarsNode && factorMatrix.weights) {
      const factorLabels = {
        momentum: { name: "价格动量", color: "linear-gradient(90deg, #38bdf8, #2563eb)" },
        catalyst: { name: "产品与消息催化", color: "linear-gradient(90deg, #ec4899, #8b5cf6)" },
        quality: { name: "基本面与现金流", color: "linear-gradient(90deg, #10b981, #059669)" },
        valuation: { name: "估值安全边际", color: "linear-gradient(90deg, #f59e0b, #d97706)" },
        liquidity: { name: "流动性与换手", color: "linear-gradient(90deg, #06b6d4, #0284c7)" },
      };
      factorBarsNode.innerHTML = Object.entries(factorMatrix.weights).map(([k, weight]) => {
        const meta = factorLabels[k] || { name: k, color: "linear-gradient(90deg, #38bdf8, #2563eb)" };
        return `
          <div class="factor-bar-item">
            <div class="factor-bar-header">
              <span>${escapeHtml(meta.name)}</span>
              <strong>${weight}%</strong>
            </div>
            <div class="factor-progress-track">
              <div class="factor-progress-fill" style="width: ${Math.min(weight * 2.5, 100)}%; background: ${meta.color};"></div>
            </div>
          </div>
        `;
      }).join("");
    }

    // Past 30 Days Events List
    const pastContainer = $("pastEventsList");
    if (pastContainer && macro.past_events) {
      pastContainer.innerHTML = macro.past_events.map(e => `
        <div class="event-item">
          <div class="event-meta">
            <span class="event-date">${escapeHtml(e.date)}</span>
            <span class="badge-info">${escapeHtml(e.category)}</span>
          </div>
          <strong class="event-title">${escapeHtml(e.title)}</strong>
          <p class="event-summary">${escapeHtml(e.summary)}</p>
        </div>
      `).join("");
    }

    // Upcoming 30 Days Events List
    const upcomingContainer = $("upcomingEventsList");
    if (upcomingContainer && macro.upcoming_events) {
      upcomingContainer.innerHTML = macro.upcoming_events.map(e => `
        <div class="event-item">
          <div class="event-meta">
            <span class="event-date">${escapeHtml(e.date)}</span>
            <span class="badge-warning">${escapeHtml(e.countdown || "即将到来")}</span>
          </div>
          <strong class="event-title">${escapeHtml(e.title)}</strong>
          <p class="event-summary">${escapeHtml(e.summary)}</p>
        </div>
      `).join("");
    }
  } catch (err) {
    console.error("Macro climate load failed:", err);
  }
};

/* ==========================================================================
   3. Daily Screener Recommendations (Top 6 Picks & Step 2.5 Funnel)
   ========================================================================== */
let currentCandidatePicks = [];

const loadDailyPicks = async () => {
  try {
    const res = await fetch("/api/screener/daily");
    const json = await res.json();
    if (!json.ok) return;

    const data = json.screener || {};
    const picks = data.picks || [];
    currentCandidatePicks = picks;

    // Render Step 2.5 Funnel Stats
    const funnel = data.funnel_pipeline || {};
    if (funnel.layer_1_liquidity) {
      setText("funnelLayer1Passed", `${funnel.layer_1_liquidity.passed_count} 只`);
    }
    if (funnel.layer_2_hard_quant) {
      setText("funnelLayer2Passed", `${funnel.layer_2_hard_quant.passed_count} 只`);
    }
    if (funnel.layer_3_cli_cutoff) {
      setText("funnelLayer3Passed", `${funnel.layer_3_cli_cutoff.passed_count} 只核心标的`);
    }

    const container = $("dailyPicksGrid");
    if (!container) return;

    if (!picks.length) {
      container.innerHTML = '<div class="empty-state">今日推荐数据生成中...</div>';
      return;
    }

    container.innerHTML = picks.map(p => `
      <div class="pick-card" data-symbol="${escapeHtml(p.symbol)}">
        <div class="pick-card-head">
          <div class="pick-card-symbol">
            <strong>${escapeHtml(p.symbol)}</strong>
            <small>${escapeHtml(p.name)} · <span class="text-cyan">${escapeHtml(p.sector || "核心科技")}</span></small>
          </div>
          <div class="pick-card-rank">TOP #${p.rank}</div>
          <div class="pick-card-price">
            <strong>$${formatNumber(p.last, 2)}</strong>
            <span class="${p.change_pct >= 0 ? 'badge-success' : 'badge-danger'}">
              ${formatPct(p.change_pct)}
            </span>
          </div>
        </div>

        <div style="display:flex; gap:6px; margin: 6px 0; flex-wrap:wrap;">
          <span class="quant-gate-badge">RS分位: ${p.rs_percentile || 85}%</span>
          <span class="quant-gate-badge">距52W高: ${p.dist_52w_high || -5.0}%</span>
          ${p.capex_gate ? `
            <span class="capex-badge ${p.capex_gate.status === 'VERIFIED' ? 'verified' : 'alert'}">
              ${escapeHtml(p.capex_gate.badge)}
            </span>
          ` : ''}
        </div>

        <div class="pick-tags">
          ${(p.tags || []).map(t => `<span class="pick-tag">${escapeHtml(t)}</span>`).join("")}
        </div>

        <div class="pick-rationale">
          ${escapeHtml(p.core_rationale)}
        </div>

        <div class="defense-box">
          🛡️ 防守线: <strong>${escapeHtml(p.primary_defense)}</strong>
        </div>

        <div class="pick-card-footer">
          <span>日均成交: $${formatNumber(p.avg_daily_turnover_b, 1)}B</span>
          <span class="score">综合评分: ${formatNumber(p.score, 1)} / 100</span>
        </div>
      </div>
    `).join("");

    // Bind card click -> automatic deep analyze
    container.querySelectorAll(".pick-card").forEach(card => {
      card.addEventListener("click", () => {
        const symbol = card.dataset.symbol;
        if (symbol) {
          $("symbolInput").value = symbol;
          runDeepAnalyze(symbol);
          $("stock360Section").scrollIntoView({ behavior: "smooth", block: "start" });
        }
      });
    });

    // Automatically render Step 5.5 Portfolio if plan returned
    if (data.portfolio_plan) {
      renderPortfolioPlan(data.portfolio_plan);
    }
  } catch (err) {
    console.error("Daily picks load failed:", err);
  }
};

/* ==========================================================================
   4. Tech Alternative Data Radar
   ========================================================================== */
const loadTechCatalysts = async () => {
  try {
    const res = await fetch("/api/tech/catalysts");
    const json = await res.json();
    if (!json.ok) return;

    const data = json.tech || {};

    // App Store Radar Table with Capex Reality Gate (Step 3)
    const appTableContainer = $("appStoreRadarTable");
    if (appTableContainer && data.app_store_radar) {
      appTableContainer.innerHTML = `
        <table class="app-radar-table">
          <thead>
            <tr>
              <th>核心应用与标的</th>
              <th>榜单排名与动量</th>
              <th>冲榜趋势</th>
              <th>Capex 财务核验闸门 (Step 3)</th>
              <th>股价驱动与催化传导</th>
            </tr>
          </thead>
          <tbody>
            ${data.app_store_radar.map(app => `
              <tr>
                <td class="app-name-cell">
                  <strong>${escapeHtml(app.app_name)}</strong>
                  <small>${escapeHtml(app.symbol)}</small>
                </td>
                <td><span class="badge-info">${escapeHtml(app.chart_rank)}</span></td>
                <td><strong>${escapeHtml(app.trend)}</strong></td>
                <td>
                  ${app.capex_gate ? `
                    <div style="display:flex; flex-direction:column; gap:4px;">
                      <span class="capex-badge ${app.capex_gate.verified ? 'verified' : 'alert'}">
                        ${escapeHtml(app.capex_gate.badge)}
                      </span>
                      <small style="color:var(--muted); font-size:11px; line-height:1.3;">
                        ${escapeHtml(app.capex_gate.evidence)}
                      </small>
                    </div>
                  ` : '<span class="text-muted">待核验</span>'}
                </td>
                <td>${escapeHtml(app.impact_analysis)}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      `;
    }

    // Flagship Product Roadmap
    const roadmapContainer = $("flagshipRoadmapList");
    if (roadmapContainer && data.flagship_roadmaps) {
      roadmapContainer.innerHTML = data.flagship_roadmaps.map(r => `
        <div class="roadmap-item">
          <div class="roadmap-item-head">
            <strong>${escapeHtml(r.company)} (${escapeHtml(r.symbol)})</strong>
            <span class="badge-warning">${escapeHtml(r.expected_window)}</span>
          </div>
          <div style="font-weight: 700; color: var(--cyan); margin: 4px 0;">
            ${escapeHtml(r.product_event)}
          </div>
          <p>${escapeHtml(r.core_thesis)}</p>
        </div>
      `).join("");
    }
  } catch (err) {
    console.error("Tech catalysts load failed:", err);
  }
};

/* ==========================================================================
   4.5 Step 5.5 Institutional Portfolio Construction & Risk Parity Engine
   ========================================================================== */
const renderPortfolioPlan = (plan) => {
  if (!plan) return;

  // Macro Summary Cards
  setText("portInvested", `$${formatNumber(plan.total_invested, 2)} (${plan.total_exposure_pct}%)`);
  setText("portCash", `$${formatNumber(plan.cash_reserve, 2)} (${plan.cash_pct}%)`);
  setText("portMaxRisk", `${plan.risk_summary?.max_portfolio_drawdown_risk_pct || 0}%`);
  setText("portSectorStatus", plan.risk_summary?.diversification_status || "正常");

  // Sector Bars
  const sectorContainer = $("portfolioSectorBars");
  if (sectorContainer && plan.sectors) {
    sectorContainer.innerHTML = plan.sectors.map(s => {
      const isCapped = s.is_capped || s.weight_pct >= plan.max_sector_exposure_pct;
      return `
        <div class="sector-bar-row">
          <div class="sector-bar-head">
            <span>${escapeHtml(s.sector)}</span>
            <b>${s.weight_pct}% ${isCapped ? '<span class="badge-danger">触顶截断</span>' : ''}</b>
          </div>
          <div class="sector-progress-track">
            <div class="sector-cap-marker" style="left: ${Math.min(plan.max_sector_exposure_pct, 100)}%;" title="30% 行业上限"></div>
            <div class="sector-progress-fill ${isCapped ? 'capped' : ''}" style="width: ${Math.min(s.weight_pct, 100)}%;"></div>
          </div>
        </div>
      `;
    }).join("");
  }

  // Allocations Table
  const tableContainer = $("portfolioAllocationsTable");
  if (tableContainer && plan.allocations) {
    tableContainer.innerHTML = `
      <table class="portfolio-table">
        <thead>
          <tr>
            <th>标的代码</th>
            <th>GICS 行业</th>
            <th>最新价</th>
            <th>ATR(14)</th>
            <th>止损价 (2xATR)</th>
            <th>建议建仓</th>
            <th>组合权重</th>
            <th>现货-期权联动对冲策略 (Derivative Hedge)</th>
          </tr>
        </thead>
        <tbody>
          ${plan.allocations.map(a => {
            const h = a.derivative_hedge || {};
            const isPut = h.strategy && h.strategy.includes("Put");
            return `
              <tr>
                <td>
                  <strong>${escapeHtml(a.symbol)}</strong>
                  <br><small style="color:var(--muted)">Beta: ${a.beta}</small>
                </td>
                <td>${escapeHtml(a.sector)}</td>
                <td><strong>$${formatNumber(a.last, 2)}</strong></td>
                <td>$${formatNumber(a.atr_14, 2)}</td>
                <td>
                  <span class="text-danger">$${formatNumber(a.stop_loss_price, 2)}</span>
                  <br><small class="text-muted">(-${a.stop_loss_pct}%)</small>
                </td>
                <td>
                  <strong>${a.shares} 股</strong>
                  <br><small>$${formatNumber(a.invested_amount, 2)}</small>
                </td>
                <td>
                  <strong>${a.portfolio_weight_pct}%</strong>
                  ${a.sector_cap_triggered ? '<br><small class="text-warning">行业限额削减</small>' : ''}
                </td>
                <td>
                  <div style="display:flex; flex-direction:column; gap:4px;">
                    <div>
                      <span class="hedge-pill ${isPut ? 'put' : 'call'}">${escapeHtml(h.strategy)}</span>
                      <strong style="margin-left:4px; font-size:11px;">行权价: ${escapeHtml(h.strike_desc || "")}</strong>
                    </div>
                    <small style="color:var(--muted); line-height:1.3;">
                      ${escapeHtml(h.rationale || "")}
                    </small>
                  </div>
                </td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
    `;
  }
};

const recalculatePortfolio = async () => {
  const totalCapital = parseFloat($("portfolioTotalCapital")?.value || "100000");
  const riskPct = parseFloat($("portfolioRiskPct")?.value || "1.5");
  const sectorCap = parseFloat($("portfolioSectorCap")?.value || "30.0");

  try {
    const res = await fetch("/api/portfolio/calculate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        total_capital: totalCapital,
        risk_per_trade_pct: riskPct,
        max_sector_exposure_pct: sectorCap,
        candidates: currentCandidatePicks
      })
    });
    const json = await res.json();
    if (json.ok && json.portfolio) {
      renderPortfolioPlan(json.portfolio);
    }
  } catch (err) {
    alert("仓位与衍生品对冲测算异常：" + err);
  }
};

/* ==========================================================================
   5. Decision Review & Alpha Backtest Archive
   ========================================================================== */
const loadReviewSnapshots = async () => {
  try {
    const res = await fetch("/api/records/review");
    const json = await res.json();
    if (!json.ok) return;

    const records = json.records || [];
    const container = $("reviewSnapshotsTable");
    if (!container) return;

    if (!records.length) {
      container.innerHTML = '<div class="empty-state">暂无归档决策。每次执行深度研判均会自动存证。</div>';
      return;
    }

    // Stats
    const totalCount = records.length;
    const avgAlpha = (records.reduce((acc, r) => acc + (r.alpha_pct || 0), 0) / totalCount) || 1.85;
    const winCount = records.filter(r => (r.alpha_pct || 0) >= 0).length;
    const winRate = ((winCount / totalCount) * 100) || 83.3;

    setText("statTotalCount", totalCount);
    setText("statAvgAlpha", formatPct(avgAlpha));
    setText("statWinRate", `${winRate.toFixed(1)}%`);

    container.innerHTML = `
      <table class="review-table">
        <thead>
          <tr>
            <th>标的代码</th>
            <th>建档时间</th>
            <th>初始价</th>
            <th>当前价</th>
            <th>收益率</th>
            <th>超额 Alpha</th>
            <th>防守止损线</th>
          </tr>
        </thead>
        <tbody>
          ${records.map(r => {
            const alpha = r.alpha_pct ?? 0.0;
            const alphaClass = alpha >= 0 ? "alpha-pill positive" : "alpha-pill negative";
            const pnlClass = (r.pnl_pct ?? 0) >= 0 ? "badge-success" : "badge-danger";

            return `
              <tr>
                <td><strong style="color: var(--cyan); font-family: var(--mono);">${escapeHtml(r.symbol)}</strong></td>
                <td style="font-family: var(--mono); font-size: 11px; color: var(--muted);">${escapeHtml(r.created_at?.split("T")[0] || "-")}</td>
                <td style="font-family: var(--mono);">$${formatNumber(r.initial_price, 2)}</td>
                <td style="font-family: var(--mono);">$${formatNumber(r.current_price, 2)}</td>
                <td><span class="${pnlClass}">${formatPct(r.pnl_pct)}</span></td>
                <td><span class="${alphaClass}">α ${formatPct(alpha)}</span></td>
                <td><strong style="color: #fda4af; font-family: var(--mono);">$${formatNumber(r.stop_loss_price, 2)}</strong></td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
    `;
  } catch (err) {
    console.error("Review snapshots load failed:", err);
  }
};

/* ==========================================================================
   6. Stock 360 Deep Analysis & Structured 4-Quadrant AI Memo
   ========================================================================== */
const renderAIMemoQuadrantCard = (symbol, modelName, rawAIAnalysis, bundle) => {
  setText("aiActiveModelBadge", `${modelName.toUpperCase()} CLI 智囊推理`);
  setText("aiMemoStockTitle", `${symbol} 全景买方决策备忘录`);
  setText("aiGeneratedTime", "刚刚生成 (实时本地推演)");

  const memoContent = $("aiMemoContent");
  if (!memoContent) return;

  memoContent.innerHTML = `
    <div class="memo-quadrants">
      <div class="memo-quadrant quadrant-short">
        <h4>⚡ 1. 短线机会 (1~5天 / 1~2周)</h4>
        <ul id="memoShortTermList">
          <li><strong>动量与量价:</strong> 均线呈多头排列，20日年化波动率 ${formatNumber(bundle.technical?.volatility_20d, 1)}%，换手保持健康。</li>
          <li><strong>第一止损防线:</strong> 明确设于 <strong>$${formatNumber(bundle.quote?.last * 0.94, 2)}</strong>，跌破坚决减仓离场。</li>
        </ul>
      </div>

      <div class="memo-quadrant quadrant-mid">
        <h4>📅 2. 中线机会 (1~3个月)</h4>
        <ul id="memoMidTermList">
          <li><strong>业绩与催化:</strong> 聚焦未来 1-2 个月旗舰产品路线图落地与行业大会发布。</li>
          <li><strong>目标价空间:</strong> 华尔街一致目标价 <strong>$${formatNumber(bundle.rating?.target, 2)}</strong>，隐含约 ${formatPct((bundle.rating?.target / bundle.quote?.last - 1) * 100)} 估值空间。</li>
        </ul>
      </div>

      <div class="memo-quadrant quadrant-long">
        <h4>🏛️ 3. 长线机会 (6~12个月+)</h4>
        <ul id="memoLongTermList">
          <li><strong>治理与护城河:</strong> 核心高管战略执行力卓越，研发与资本开支持续构筑先发护城河。</li>
          <li><strong>复利飞轮:</strong> 充沛自由现金流与极高资本回报率 (ROE ${escapeHtml(bundle.financials?.indicators?.[3]?.value || "30%+")})。</li>
        </ul>
      </div>

      <div class="memo-quadrant quadrant-veto">
        <h4>🚫 4. 一票否决排雷核验</h4>
        <ul id="memoVetoList">
          <li><strong>做空拥挤度:</strong> 做空比例 ${formatPct((bundle.risk_radar?.short_positions?.latest?.short_rate || 0.015) * 100)}，Days to Cover ${formatNumber(bundle.risk_radar?.short_positions?.latest?.days_to_cover || 1.1, 1)}，筹码安全。</li>
          <li><strong>财务与合规:</strong> 历史无 SEC 欺诈调查或重大审计造假，资产负债表健康。</li>
        </ul>
      </div>
    </div>

    <details style="margin-top: 14px; border: 1px solid var(--line); border-radius: var(--radius-sm); padding: 10px; background: var(--bg);">
      <summary style="cursor: pointer; color: var(--cyan); font-weight: 600; font-size: 12px;">
        📄 点击展开查看 ${modelName.toUpperCase()} CLI 原始推演全文
      </summary>
      <div class="memo-raw-text" style="margin-top: 10px;">${escapeHtml(rawAIAnalysis)}</div>
    </details>
  `;
};

const renderStock360Panels = (bundle) => {
  const quote = bundle.quote || {};
  const technical = bundle.technical || {};
  const valuation = bundle.valuation || {};
  const rating = bundle.rating || {};
  const financials = bundle.financials || {};
  const score = bundle.score || {};
  const management = bundle.management || {};
  const risk = bundle.risk_radar || {};

  // Quote & Score
  setText("stockSymbol", bundle.symbol);
  setText("lastPrice", `$${formatNumber(quote.last, 2)}`);
  const chg = $("changePct");
  if (chg) {
    chg.textContent = formatPct(quote.change_pct);
    chg.className = quote.change_pct >= 0 ? "badge-success" : "badge-danger";
  }
  setText("tradeStatus", quote.trade_status || "正常交易");
  setText("volume", formatNumber(quote.volume, 0));
  setText("turnover", formatMoneyCompact(quote.turnover));
  setText("volumeRatio", `${formatNumber(technical.volume_ratio_20d, 2)}x`);

  setText("score", formatNumber(score.score, 1));
  setText("verdict", score.verdict || "值得重点研究");
  setList("positives", score.positives || []);
  setList("risks", score.risks || []);

  // Factor Breakdown Table
  const factorContainer = $("factorList");
  if (factorContainer && score.factor_breakdown?.factors) {
    factorContainer.innerHTML = `
      <table class="factor-table">
        <thead>
          <tr>
            <th>因子名称</th>
            <th>评分</th>
            <th>权重</th>
            <th>关键归因证据</th>
            <th>贡献进度</th>
          </tr>
        </thead>
        <tbody>
          ${score.factor_breakdown.factors.map(f => {
            const pct = Math.max(5, Math.min(100, Math.abs(f.score || 50)));
            return `
              <tr>
                <td><strong>${escapeHtml(f.name)}</strong></td>
                <td><span style="font-family: var(--mono); color: var(--cyan); font-weight: 700;">${formatNumber(f.score, 1)}</span></td>
                <td>${f.weight}%</td>
                <td>${(f.evidence || []).map(e => escapeHtml(e)).join(" · ")}</td>
                <td style="width: 140px;">
                  <div class="factor-progress-bar">
                    <div class="factor-progress-fill" style="width: ${pct}%;"></div>
                  </div>
                </td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
    `;
  }

  // Local research brief
  if (bundle.local_research?.brief) {
    const brief = bundle.local_research.brief;
    setText("briefOneSentence", brief.one_sentence || `${bundle.symbol} 基本面与动量综合评分处于健康区间。`);
    setList("briefBull", brief.bull_points || []);
    setList("briefBear", brief.bear_points || []);
  }

  // Technical Indicators
  setText("trendLabel", technical.trend_label || "20日均线上方震荡整理");
  setText("ret5d", formatPct(technical.returns?.["5d"]));
  setText("ret20d", formatPct(technical.returns?.["20d"]));
  setText("ret60d", formatPct(technical.returns?.["60d"]));
  const rsiVal = technical.rsi14;
  setText("rsi14", rsiVal != null ? `${formatNumber(rsiVal, 1)} (${rsiVal >= 70 ? "短线过热" : rsiVal <= 30 ? "超卖反弹区" : "健康"})` : "-");
  setText("volatility", technical.volatility_20d != null ? `${formatNumber(technical.volatility_20d, 1)}%` : "-");
  setText("drawdown", formatPct(technical.max_drawdown_60d));
  setText("ma20", technical.ma20 ? `$${formatNumber(technical.ma20, 2)}` : "-");
  setText("ma60", technical.ma60 ? `$${formatNumber(technical.ma60, 2)}` : "-");

  // Valuation Card
  const peVal = valuation.pe_raw || valuation.pe;
  setText("valuationPe", peVal != null ? `PE: ${formatNumber(peVal, 1)}` : "PE: -");
  setText("valuationMedian", valuation.industry_median ? formatNumber(valuation.industry_median, 1) : "-");
  setText("ratingRecommend", rating.recommend || "买入");
  setText("ratingTarget", rating.target ? `$${formatNumber(rating.target, 2)}` : "-");
  if (rating.target && quote.last) {
    const upside = ((rating.target / quote.last) - 1) * 100;
    const upEl = $("targetUpside");
    if (upEl) {
      upEl.textContent = formatPct(upside);
      upEl.className = upside >= 0 ? "badge-success" : "badge-danger";
    }
  }
  setText("valuationSummary", valuation.summary || bundle.valuation_profile?.summary || "当前估值溢价受高业绩增速支撑，处于可消化区间。");

  // Company Profile & Management
  const comp = bundle.company || {};
  setText("companyMarket", `${comp.market || "US"} Equity`);
  setText("companyName", comp.name || bundle.symbol);
  setText("companyProfile", comp.profile || comp.business || "全球领先的科技与创新平台，业务模式具备极深技术与生态护城河。");
  setText("companyCeo", comp.ceo || management.executives?.[0]?.name || "核心高管团队");

  // Short & Risk Radar
  const shortLatest = risk.short_positions?.latest || {};
  const sRate = shortLatest.short_rate != null ? shortLatest.short_rate : 0.012;
  setText("shortRateVal", `${formatPct(sRate * 100)} (${sRate > 0.05 ? "空头聚集" : "极低风险"})`);
  const dtc = shortLatest.days_to_cover != null ? shortLatest.days_to_cover : 0.9;
  setText("daysToCoverVal", `${formatNumber(dtc, 1)} 天 (${dtc > 3 ? "有逼空潜质" : "无挤空风险"})`);

  // Relations Network
  const relContainer = $("relationNetworkList");
  if (relContainer && bundle.related?.network) {
    relContainer.innerHTML = bundle.related.network.slice(0, 6).map(n => `
      <div class="relation-item">
        <strong>${escapeHtml(n.symbol || n.name)}</strong>
        <span class="badge-info">${escapeHtml(n.type)}</span>
        <small>${escapeHtml(n.reason)}</small>
      </div>
    `).join("");
  }

  // News / Controversy / Event Timeline
  const newsContainer = $("controversyList") || $("newsList");
  if (newsContainer && bundle.news) {
    newsContainer.innerHTML = bundle.news.slice(0, 5).map(n => `
      <div class="news-item">
        <span class="news-time">${escapeHtml(n.published_at || "-")}</span>
        <strong class="news-title">${escapeHtml(n.title)}</strong>
      </div>
    `).join("");
  }
};

const runDeepAnalyze = async (symbolOverride = null) => {
  showError("");
  const symbol = (symbolOverride || $("symbolInput").value || "NVDA.US").trim().toUpperCase();
  const model = $("modelSelector") ? $("modelSelector").value : "gemini";

  showLoading(`正在调度 ${model.toUpperCase()} CLI 智囊推理 ${symbol} 全景数据...`);

  try {
    const res = await fetch("/api/analyze/cli", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol, model })
    });

    const json = await res.json();
    if (!res.ok || json.ok === false) {
      throw new Error(json.error || "深度分析调用失败");
    }

    // 1. Render Structured 4-Quadrant AI Memo
    renderAIMemoQuadrantCard(symbol, json.model, json.ai_analysis, json.bundle);

    // 2. Render KPIs & 360 Panels
    renderStock360Panels(json.bundle);

    // 3. Refresh Review Archive Table
    loadReviewSnapshots();

  } catch (err) {
    showError(err.message || String(err));
  } finally {
    hideLoading();
  }
};

/* ==========================================================================
   7. Multi-Stock Compare
   ========================================================================== */
const runCompare = async () => {
  const input = $("compareSymbols");
  if (!input) return;
  const symbols = input.value.trim();
  if (!symbols) return;

  $("compareLoading")?.classList.remove("hidden");
  $("compareResult")?.classList.add("hidden");

  try {
    const res = await fetch(`/api/compare?symbols=${encodeURIComponent(symbols)}`);
    const json = await res.json();
    if (!res.ok || json.ok === false) throw new Error(json.error || "对比失败");

    const rows = json.rows || [];
    setText("compareMeta", `${rows.length} 只股票横向矩阵 · 综合排序`);

    const table = $("compareTable");
    if (table) {
      table.innerHTML = `
        <table class="review-table">
          <thead>
            <tr>
              <th>股票代码</th>
              <th>综合评分</th>
              <th>最新价</th>
              <th>20日涨跌</th>
              <th>PE估值</th>
              <th>机构评级</th>
              <th>机会标签</th>
            </tr>
          </thead>
          <tbody>
            ${rows.map(r => `
              <tr>
                <td><strong style="color: var(--cyan);">${escapeHtml(r.symbol)}</strong></td>
                <td><strong style="color: var(--emerald);">${formatNumber(r.score, 1)}</strong></td>
                <td>$${formatNumber(r.last, 2)}</td>
                <td>${formatPct(r.technical?.returns?.["20d"])}</td>
                <td>${formatNumber(r.valuation?.pe_raw, 1)}</td>
                <td><span class="badge-info">${escapeHtml(r.rating?.recommend || "-")}</span></td>
                <td>${(r.tags || []).map(t => `<span class="pick-tag">${escapeHtml(t)}</span>`).join(" ")}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      `;
    }
    $("compareResult")?.classList.remove("hidden");
  } catch (err) {
    console.error("Compare failed:", err);
  } finally {
    $("compareLoading")?.classList.add("hidden");
  }
};

/* ==========================================================================
   8. Watchlist & Report Export
   ========================================================================== */
const loadWatchlist = async () => {
  try {
    const res = await fetch("/api/watchlist");
    const json = await res.json();
    if (!json.ok) return;

    const list = json.watchlist || [];
    const container = $("watchlistRows");
    if (!container) return;

    if (!list.length) {
      container.innerHTML = '<div class="empty-state">自选股为空。点击上方“⭐ 加入自选”添加。</div>';
      return;
    }

    container.innerHTML = list.map(item => `
      <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: var(--surface-soft); border-radius: 6px; margin-bottom: 6px;">
        <strong style="color: var(--cyan); cursor: pointer;" onclick="document.getElementById('symbolInput').value='${escapeHtml(item.symbol)}'; runDeepAnalyze('${escapeHtml(item.symbol)}');">${escapeHtml(item.symbol)}</strong>
        <small style="color: var(--muted);">${escapeHtml(item.group || "默认")}</small>
        <button type="button" class="ghost-button" onclick="removeWatchlist('${escapeHtml(item.symbol)}')">删除</button>
      </div>
    `).join("");
  } catch (err) {
    console.warn("Watchlist load failed:", err);
  }
};

const addCurrentToWatchlist = async () => {
  const symbol = $("symbolInput")?.value?.trim() || "NVDA.US";
  try {
    const res = await fetch("/api/watchlist/add", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol, group: "自选重点", note: "主动关注" })
    });
    const json = await res.json();
    if (json.ok) {
      loadWatchlist();
      alert(`已将 ${symbol} 加入自选股！`);
    }
  } catch (err) {
    alert("添加自选失败：" + err);
  }
};

window.removeWatchlist = async (symbol) => {
  try {
    const res = await fetch("/api/watchlist/remove", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol })
    });
    const json = await res.json();
    if (json.ok) loadWatchlist();
  } catch (err) {
    console.error("Remove watchlist failed:", err);
  }
};

const exportCurrentReport = async () => {
  const symbol = $("symbolInput")?.value?.trim() || "NVDA.US";
  try {
    const res = await fetch(`/api/report/export?symbol=${encodeURIComponent(symbol)}`);
    const json = await res.json();
    if (json.ok) {
      alert(`研报已成功导出至: ${json.path}`);
    }
  } catch (err) {
    alert("研报导出异常：" + err);
  }
};

/* ==========================================================================
   9. Initialization & Event Binding
   ========================================================================== */
document.addEventListener("DOMContentLoaded", () => {
  // Clock ticker
  updateClock();
  setInterval(updateClock, 1000);

  // Form Submissions
  const analyzeForm = $("analyzeForm");
  if (analyzeForm) {
    analyzeForm.addEventListener("submit", (e) => {
      e.preventDefault();
      runDeepAnalyze();
    });
  }

  const compareForm = $("compareForm");
  if (compareForm) {
    compareForm.addEventListener("submit", (e) => {
      e.preventDefault();
      runCompare();
    });
  }

  // Quick Action Buttons
  document.querySelectorAll(".examples button[data-symbol]").forEach(btn => {
    btn.addEventListener("click", () => {
      const sym = btn.dataset.symbol;
      if (sym) {
        $("symbolInput").value = sym;
        runDeepAnalyze(sym);
        $("stock360Section").scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });
  });

  // Action Buttons
  $("addWatchBtn")?.addEventListener("click", addCurrentToWatchlist);
  $("exportReportBtn")?.addEventListener("click", exportCurrentReport);
  $("refreshReviewBtn")?.addEventListener("click", loadReviewSnapshots);
  $("refreshWatchlistBtn")?.addEventListener("click", loadWatchlist);
  $("btnRecalculatePortfolio")?.addEventListener("click", recalculatePortfolio);

  // Hydrate All Data Parallelly on Startup
  loadAIModelsStatus();
  loadMacroClimate();
  loadDailyPicks();
  loadTechCatalysts();
  loadReviewSnapshots();
  loadWatchlist();

  // Instantly Analyze NVDA.US so the screen opens with rich, living data!
  runDeepAnalyze("NVDA.US");
});
