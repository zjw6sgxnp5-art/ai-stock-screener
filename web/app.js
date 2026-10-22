/**
 * AI Stock Research Terminal - Core Frontend Application
 * Google-style Home, History Shelf Drawer, Tab Switching, Component Hot-Refresh,
 * and Interactive Plain-Language Hover Tooltip.
 */

// Global Application State
// Global Application State
const state = {
  currentSymbol: null,
  currentDossier: null,
  activeModule: "valuation_matrix", // Rule P1 10: 档案先给数字，默认落在估值与财务
  activeMainTab: "screenerSection", // Rule 2 & P1 6: 默认进入选股页
  historyList: [],
  macroData: null,
  dailyPicksData: null,
  backtestData: null,
  sensitivityData: null,
  activeSensitivityMetric: "sharpe",
  compareData: null,
  portfolioData: null,
  selectedCompareSymbols: [], // Rule P1 11: 勾选对比标的 (最多5只)
  watchlistSymbols: new Set(), // Rule P1 9: 自选股集合
  screenerFilter: "all", // "all" | "watchlist"
  progressPollingInterval: null,
  existingHoldings: [
    { symbol: "NVDA.US", shares: 100 },
    { symbol: "AAPL.US", shares: 120 },
    { symbol: "MSFT.US", shares: 80 }
  ]
};

// DOM Element Registry
const elements = {
  // Global Navigation & Sections
  globalNavTabs: document.getElementById("globalNavTabs"),
  dossierSection: document.getElementById("dossierSection"),
  screenerSection: document.getElementById("screenerSection"),
  compareSection: document.getElementById("compareSection"),
  backtestSection: document.getElementById("backtestSection"),
  portfolioSection: document.getElementById("portfolioSection"),
  btnGlobalHistory: document.getElementById("btnGlobalHistory"),
  globalHistoryBadge: document.getElementById("globalHistoryBadge"),

  // Top Nav Search (Rule 2)
  topNavSearchForm: document.getElementById("topNavSearchForm"),
  topNavSymbolInput: document.getElementById("topNavSymbolInput"),
  topNavAutocompleteDropdown: document.getElementById("topNavAutocompleteDropdown"),

  // Views inside Dossier
  homeView: document.getElementById("homeView"),
  dossierView: document.getElementById("dossierView"),
  historyModal: document.getElementById("historyModal"),
  smartTooltip: document.getElementById("smartTooltip"),
  globalLoading: document.getElementById("globalLoadingOverlay"),
  loadingTitle: document.getElementById("loadingTitle"),
  loadingDesc: document.getElementById("loadingDesc"),

  // Home controls
  searchForm: document.getElementById("searchForm"),
  symbolInput: document.getElementById("symbolInput"),
  btnClearSearch: document.getElementById("btnClearSearch"),
  quickPills: document.getElementById("quickPills"),
  btnOpenHistory: document.getElementById("btnOpenHistory"),
  historyCountBadge: document.getElementById("historyCountBadge"),

  // Dossier Header & Watchlist (Rule P1 9)
  btnBackHome: document.getElementById("btnBackHome"),
  stockName: document.getElementById("stockName"),
  stockSymbol: document.getElementById("stockSymbol"),
  stockEssenceShort: document.getElementById("stockEssenceShort"),
  stockPrice: document.getElementById("stockPrice"),
  stockChangePct: document.getElementById("stockChangePct"),
  stockValStatus: document.getElementById("stockValStatus"),
  btnSyncPrice: document.getElementById("btnSyncPrice"),
  btnHeaderHistory: document.getElementById("btnHeaderHistory"),
  btnDossierWatchlist: document.getElementById("btnDossierWatchlist"),
  dossierWatchlistIcon: document.getElementById("dossierWatchlistIcon"),
  dossierWatchlistText: document.getElementById("dossierWatchlistText"),

  // Topic Tabs & Stage (Rule P1 10: 估值优先)
  topicTabsBar: document.getElementById("topicTabsBar"),
  topicIcon: document.getElementById("topicIcon"),
  topicTitle: document.getElementById("topicTitle"),
  topicTimestamp: document.getElementById("topicTimestamp"),
  btnRefreshModule: document.getElementById("btnRefreshModule"),
  topicContentArea: document.getElementById("topicContentArea"),

  // Screener Progress & Exceptions (Rule P1 7)
  screenerProgressBox: document.getElementById("screenerProgressBox"),
  screenerProgressText: document.getElementById("screenerProgressText"),
  screenerProgressCount: document.getElementById("screenerProgressCount"),
  screenerProgressBarFill: document.getElementById("screenerProgressBarFill"),
  screenerExceptionsBox: document.getElementById("screenerExceptionsBox"),
  screenerExceptionsText: document.getElementById("screenerExceptionsText"),
  btnRetryExceptions: document.getElementById("btnRetryExceptions"),

  // Screener Filters & Quick Add (Rule P1 9)
  btnFilterAllPool: document.getElementById("btnFilterAllPool"),
  btnFilterWatchlist: document.getElementById("btnFilterWatchlist"),
  screenerAllCount: document.getElementById("screenerAllCount"),
  screenerWatchlistCount: document.getElementById("screenerWatchlistCount"),
  quickAddWatchlistInput: document.getElementById("quickAddWatchlistInput"),
  btnQuickAddWatchlist: document.getElementById("btnQuickAddWatchlist"),

  // Floating Compare Tray (Rule P1 11)
  compareFloatingTray: document.getElementById("compareFloatingTray"),
  traySelectedCount: document.getElementById("traySelectedCount"),
  traySelectedPills: document.getElementById("traySelectedPills"),
  btnLaunchCompare: document.getElementById("btnLaunchCompare"),
  btnClearCompare: document.getElementById("btnClearCompare"),

  // Existing Holdings Table (Rule P2 15)
  holdingsTableBody: document.getElementById("holdingsTableBody"),
  btnAddHoldingRow: document.getElementById("btnAddHoldingRow"),
  btnInspectHoldings: document.getElementById("btnInspectHoldings"),
  holdingsInspectionAlerts: document.getElementById("holdingsInspectionAlerts"),

  // History Modal
  btnCloseHistory: document.getElementById("btnCloseHistory"),
  historyTableBody: document.getElementById("historyTableBody"),

  // Tooltip
  ttBadge: document.getElementById("ttBadge"),
  ttName: document.getElementById("ttName"),
  ttPlain: document.getElementById("ttPlain"),
  ttRule: document.getElementById("ttRule"),
  ttDiagnosis: document.getElementById("ttDiagnosis"),
  ttScenario: document.getElementById("ttScenario")
};

// Module Meta Definition (Rule P1 10: 估值速览排在第一位)
const MODULE_META = {
  valuation_matrix:      { title: "估值与核心财务速览", icon: "💰" },
  technical_compass:     { title: "技术指标与日 K 走廊", icon: "🧭" },
  capital_allocation:    { title: "资产负债与杜邦分析", icon: "🏛️" },
  business_and_industry: { title: "商业模式笔记 (人工整理)", icon: "🏢" },
  core_products:         { title: "产品与技术笔记 (人工整理)", icon: "📦" },
  ai_memo:               { title: "AI 买方投资备忘录", icon: "🧠" }
};

// ==============================================================================
// US Equities Autocomplete Universe (Core 60+ Leaders)
// ==============================================================================
const US_STOCK_UNIVERSE = [
  // AI 算力与半导体核心
  { symbol: "NVDA.US", ticker: "NVDA", name_cn: "英伟达", name_en: "NVIDIA Corp", sector: "AI 算力与 GPU 绝对霸主" },
  { symbol: "MU.US",   ticker: "MU",   name_cn: "美光科技", name_en: "Micron Technology", sector: "HBM3E / DRAM 存储周期龙头" },
  { symbol: "AMD.US",  ticker: "AMD",  name_cn: "超威半导体", name_en: "AMD Inc", sector: "CPU / MI300X 算力芯片" },
  { symbol: "TSM.US",  ticker: "TSM",  name_cn: "台积电", name_en: "TSMC", sector: "全球先进晶圆代工垄断" },
  { symbol: "ASML.US", ticker: "ASML", name_cn: "阿斯麦", name_en: "ASML Holding", sector: "EUV 先进光刻机全球独供" },
  { symbol: "AVGO.US", ticker: "AVGO", name_cn: "博通", name_en: "Broadcom Inc", sector: "数据中心交换机与定制 ASIC" },
  { symbol: "QCOM.US", ticker: "QCOM", name_cn: "高通", name_en: "Qualcomm Inc", sector: "骁龙移动芯片与端侧 AI" },
  { symbol: "INTC.US", ticker: "INTC", name_cn: "英特尔", name_en: "Intel Corp", sector: "x86 处理器与 IFS 代工" },
  { symbol: "ARM.US",  ticker: "ARM",  name_cn: "安谋", name_en: "Arm Holdings", sector: "移动与数据中心低功耗架构 IP" },
  { symbol: "MRVL.US", ticker: "MRVL", name_cn: "迈威尔科技", name_en: "Marvell Technology", sector: "光互联 PAM4 与定制云芯片" },
  { symbol: "AMAT.US", ticker: "AMAT", name_cn: "应用材料", name_en: "Applied Materials", sector: "半导体前道制程核心设备" },
  { symbol: "LRCX.US", ticker: "LRCX", name_cn: "泛林半导体", name_en: "Lam Research", sector: "半导体刻蚀与薄膜沉积设备" },
  { symbol: "KLAC.US", ticker: "KLAC", name_cn: "科磊", name_en: "KLA Corp", sector: "半导体制程检测与良率管理" },
  { symbol: "TXN.US",  ticker: "TXN",  name_cn: "德州仪器", name_en: "Texas Instruments", sector: "模拟芯片与工业嵌入式" },
  { symbol: "DELL.US", ticker: "DELL", name_cn: "戴尔科技", name_en: "Dell Technologies", sector: "企业级 AI 算力服务器集群" },
  { symbol: "SMCI.US", ticker: "SMCI", name_cn: "超微电脑", name_en: "Super Micro Computer", sector: "机架级液冷 AI 服务器" },

  // 美股超级科技七巨头 (Magnificent 7) & 核心平台
  { symbol: "AAPL.US",  ticker: "AAPL",  name_cn: "苹果公司", name_en: "Apple Inc", sector: "消费电子与 Apple Intelligence" },
  { symbol: "MSFT.US",  ticker: "MSFT",  name_cn: "微软", name_en: "Microsoft Corp", sector: "Azure 云与 Copilot 生产力" },
  { symbol: "TSLA.US",  ticker: "TSLA",  name_cn: "特斯拉", name_en: "Tesla Inc", sector: "智能电动车与 FSD / Robotaxi" },
  { symbol: "GOOGL.US", ticker: "GOOGL", name_cn: "谷歌", name_en: "Alphabet Inc", sector: "搜索广告与 GCP 云计算" },
  { symbol: "AMZN.US",  ticker: "AMZN",  name_cn: "亚马逊", name_en: "Amazon.com Inc", sector: "AWS 云计算与全球电商网络" },
  { symbol: "META.US",  ticker: "META",  name_cn: "Meta", name_en: "Meta Platforms", sector: "社交网络与 Llama 开源大模型" },

  // AI 软件 / 企业级 SaaS / 网络安全
  { symbol: "PLTR.US", ticker: "PLTR", name_cn: "Palantir", name_en: "Palantir Technologies", sector: "AIP 平台与企业/国防大数据" },
  { symbol: "ORCL.US", ticker: "ORCL", name_cn: "甲骨文", name_en: "Oracle Corp", sector: "企业数据库与 OCI 算力云" },
  { symbol: "CRM.US",  ticker: "CRM",  name_cn: "赛富时", name_en: "Salesforce Inc", sector: "Agentforce 智能体与 CRM" },
  { symbol: "PANW.US", ticker: "PANW", name_cn: "派拓网络", name_en: "Palo Alto Networks", sector: "企业平台化新一代云网络安全" },
  { symbol: "CRWD.US", ticker: "CRWD", name_cn: "CrowdStrike", name_en: "CrowdStrike Holdings", sector: "Falcon 终端云原生安全" },
  { symbol: "NOW.US",  ticker: "NOW",  name_cn: "ServiceNow", name_en: "ServiceNow Inc", sector: "企业数字化工作流平台" },
  { symbol: "ADBE.US", ticker: "ADBE", name_cn: "奥多比", name_en: "Adobe Inc", sector: "创意设计与 Firefly 生成式 AI" },
  { symbol: "SNOW.US", ticker: "SNOW", name_cn: "Snowflake", name_en: "Snowflake Inc", sector: "云原生数据仓库与共享" },
  { symbol: "NET.US",  ticker: "NET",  name_cn: "Cloudflare", name_en: "Cloudflare Inc", sector: "全球边缘网络与安全连接" },
  { symbol: "UBER.US", ticker: "UBER", name_cn: "优步", name_en: "Uber Technologies", sector: "全球共享出行与外卖履约" },

  // 数字资产与金融科技
  { symbol: "COIN.US",  ticker: "COIN",  name_cn: "Coinbase", name_en: "Coinbase Global", sector: "合规加密资产交易基础设施" },
  { symbol: "MSTR.US",  ticker: "MSTR",  name_cn: "MicroStrategy", name_en: "MicroStrategy Inc", sector: "企业比特币储备与商业智能" },

  // 消费、医疗与巴菲特重仓龙头
  { symbol: "COST.US",  ticker: "COST",  name_cn: "好市多", name_en: "Costco Wholesale", sector: "会员制高周转仓储零售" },
  { symbol: "WMT.US",   ticker: "WMT",   name_cn: "沃尔玛", name_en: "Walmart Inc", sector: "全渠道全美零售霸主" },
  { symbol: "BRK.B.US", ticker: "BRK.B", name_cn: "伯克希尔哈撒韦", name_en: "Berkshire Hathaway", sector: "价值投资航母与多元实业" },
  { symbol: "V.US",     ticker: "V",     name_cn: "Visa", name_en: "Visa Inc", sector: "全球支付交易清算网络" },
  { symbol: "MA.US",    ticker: "MA",    name_cn: "万事达", name_en: "Mastercard Inc", sector: "全球数字支付与跨境转账" },
  { symbol: "JPM.US",   ticker: "JPM",   name_cn: "摩根大通", name_en: "JPMorgan Chase", sector: "全球综合投资银行航母" },
  { symbol: "LLY.US",   ticker: "LLY",   name_cn: "礼来", name_en: "Eli Lilly", sector: "GLP-1 替尔泊肽代谢重磅新药" },
  { symbol: "NVO.US",   ticker: "NVO",   name_cn: "诺和诺德", name_en: "Novo Nordisk", sector: "司美格鲁肽减肥药双寡头" },
  { symbol: "NFLX.US",  ticker: "NFLX",  name_cn: "奈飞", name_en: "Netflix Inc", sector: "全球流媒体付费视频订阅" },

  // 热门优质中概美股
  { symbol: "BABA.US", ticker: "BABA", name_cn: "阿里巴巴", name_en: "Alibaba Group", sector: "中国电商与阿里云计算" },
  { symbol: "PDD.US",  ticker: "PDD",  name_cn: "拼多多", name_en: "PDD Holdings", sector: "国内电商与 Temu 全球出海" },
  { symbol: "JD.US",   ticker: "JD",   name_cn: "京东", name_en: "JD.com Inc", sector: "自营正品与一体化供应链物流" },
  { symbol: "BIDU.US", ticker: "BIDU", name_cn: "百度", name_en: "Baidu Inc", sector: "文心一言与萝卜快跑自动驾驶" },
  { symbol: "NIO.US",  ticker: "NIO",  name_cn: "蔚来汽车", name_en: "NIO Inc", sector: "换电豪华智能纯电车" },
  { symbol: "LI.US",   ticker: "LI",   name_cn: "理想汽车", name_en: "Li Auto Inc", sector: "家庭增程式豪华 SUV" },
  { symbol: "XPEV.US", ticker: "XPEV", name_cn: "小鹏汽车", name_en: "XPeng Inc", sector: "端到端 AI 高阶纯电智驾" },

  // 核心宽基与行业指数 ETF
  { symbol: "SPY.US",  ticker: "SPY",  name_cn: "标普500 ETF", name_en: "SPDR S&P 500 ETF", sector: "美股基准核心宽基指数" },
  { symbol: "QQQ.US",  ticker: "QQQ",  name_cn: "纳斯达克100 ETF", name_en: "Invesco QQQ Trust", sector: "全球科技龙头指数基准" },
  { symbol: "SMH.US",  ticker: "SMH",  name_cn: "半导体精选 ETF", name_en: "VanEck Semiconductor", sector: "全球顶级半导体硬科技指数" },
  { symbol: "SOXX.US", ticker: "SOXX", name_cn: "费城半导体 ETF", name_en: "iShares Semiconductor", sector: "美股费城半导体行业指数" }
];

let selectedSugIndex = 0;
let currentSuggestions = [];

window.addEventListener("DOMContentLoaded", () => {
  elements.autocompleteDropdown = document.getElementById("autocompleteDropdown");
  elements.searchInputWrapper = document.getElementById("searchInputWrapper");
  elements.btnSubmitSearch = document.getElementById("btnSubmitSearch");
  elements.btnGlobalHistory = document.getElementById("btnGlobalHistory");
  elements.globalHistoryBadge = document.getElementById("globalHistoryBadge");

  syncRegisteredStocks();
  initGlobalNavigation();
  initTopNavSearch();
  initEventListeners();
  initWatchlistListeners();
  initScreenerListeners();
  initCompareListeners();
  initBacktestListeners();
  initPortfolioListeners();
  initHoldingsListeners();
  loadHistoryCount();
  loadWatchlist().finally(() => handleUrlRouting());
});

async function syncRegisteredStocks() {
  try {
    const res = await fetch("/api/universe/stocks");
    const data = await res.json();
    if (data.ok && Array.isArray(data.stocks) && data.stocks.length > 0) {
      data.stocks.forEach(s => {
        const idx = US_STOCK_UNIVERSE.findIndex(u => u.ticker === s.ticker);
        const item = {
          symbol: s.symbol,
          ticker: s.ticker,
          name_cn: s.name_zh,
          name_en: s.name_en,
          sector: s.sector,
        };
        if (idx >= 0) {
          US_STOCK_UNIVERSE[idx] = { ...US_STOCK_UNIVERSE[idx], ...item };
        } else {
          US_STOCK_UNIVERSE.push(item);
        }
      });
    }
  } catch (e) {
    // Graceful fallback to static pool
  }
}

window.addEventListener("hashchange", () => {
  handleUrlRouting();
});

function handleUrlRouting() {
  const hash = window.location.hash || "";
  if (hash.startsWith("#/dossier/")) {
    switchMainTab("dossierSection");
    const symbol = hash.replace("#/dossier/", "").trim();
    if (symbol) {
      loadDossier(symbol);
      return;
    }
  } else if (hash === "#/screener") {
    switchMainTab("screenerSection");
    return;
  } else if (hash === "#/compare") {
    switchMainTab("compareSection");
    return;
  } else if (hash === "#/backtest") {
    switchMainTab("backtestSection");
    return;
  } else if (hash === "#/portfolio") {
    switchMainTab("portfolioSection");
    return;
  }
  // Rule 2 & P1 6: 打开页面第一眼是今日名单和淘汰原因，默认进入选股页
  switchMainTab("screenerSection");
}

function showHomeView() {
  state.currentSymbol = null;
  state.currentDossier = null;
  elements.homeView.classList.add("active");
  elements.dossierView.classList.remove("active");
  elements.symbolInput.value = "";
  elements.btnClearSearch.style.display = "none";
  hideAutocompleteDropdown();
  elements.symbolInput.focus();
  loadHistoryCount();
  if (window.location.hash) {
    history.pushState(null, "", window.location.pathname);
  }
}

function showDossierView() {
  elements.homeView.classList.remove("active");
  elements.dossierView.classList.add("active");
  hideAutocompleteDropdown();
}

function normalizeInputSymbol(raw) {
  let sym = (raw || "").trim().toUpperCase();
  if (!sym) return "";
  if (!sym.includes(".")) {
    sym = `${sym}.US`;
  }
  return sym;
}

function normalizeSymbol(raw) {
  return normalizeInputSymbol(raw);
}

// ==============================================================================
// Event Listeners: 纯美股英文限定、智能联想、键盘选择与秒开
// ==============================================================================
function initEventListeners() {
  // 1. 输入事件：只支持输入纯英文字母与点号，实时转大写
  elements.symbolInput.addEventListener("input", () => {
    const raw = elements.symbolInput.value;
    const filtered = raw.replace(/[^a-zA-Z.]/g, "").toUpperCase();
    if (raw !== filtered) {
      elements.symbolInput.value = filtered;
    }

    elements.btnClearSearch.style.display = filtered ? "block" : "none";

    if (filtered) {
      renderAutocompleteDropdown(filtered);
    } else {
      renderDefaultSuggestions();
    }
  });

  // 2. 获得焦点时：若为空则展示最近已检索历史（秒开）或热门美股
  elements.symbolInput.addEventListener("focus", () => {
    const val = elements.symbolInput.value.trim();
    if (val) {
      renderAutocompleteDropdown(val);
    } else {
      renderDefaultSuggestions();
    }
  });

  // 3. 拦截粘贴：剔除非英文字符
  elements.symbolInput.addEventListener("paste", (e) => {
    e.preventDefault();
    const pasteText = (e.clipboardData || window.clipboardData).getData("text") || "";
    const filtered = pasteText.replace(/[^a-zA-Z.]/g, "").toUpperCase();
    const input = elements.symbolInput;
    const start = input.selectionStart || 0;
    const end = input.selectionEnd || 0;
    const current = input.value;
    const updated = current.substring(0, start) + filtered + current.substring(end);
    input.value = updated;
    elements.btnClearSearch.style.display = updated ? "block" : "none";
    if (updated) {
      renderAutocompleteDropdown(updated);
    } else {
      renderDefaultSuggestions();
    }
  });

  // 4. 输入法合成结束（防止输入法输入汉字后残留）
  elements.symbolInput.addEventListener("compositionend", () => {
    const raw = elements.symbolInput.value;
    const filtered = raw.replace(/[^a-zA-Z.]/g, "").toUpperCase();
    elements.symbolInput.value = filtered;
    if (filtered) {
      renderAutocompleteDropdown(filtered);
    } else {
      renderDefaultSuggestions();
    }
  });

  // 5. 键盘交互：↑ / ↓ 上下切换，Enter 默认调阅高亮项，Esc 关闭
  elements.symbolInput.addEventListener("keydown", (e) => {
    const dropdown = elements.autocompleteDropdown;
    const isDropdownVisible = dropdown && dropdown.style.display !== "none" && currentSuggestions.length > 0;

    if (!isDropdownVisible) {
      if (e.key === "Enter") {
        e.preventDefault();
        const val = elements.symbolInput.value.trim();
        if (val) loadDossier(val);
      }
      return;
    }

    const items = dropdown.querySelectorAll(".suggestion-item");
    if (!items.length) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      selectedSugIndex = (selectedSugIndex + 1) % items.length;
      updateSuggestionHighlight(items);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      selectedSugIndex = (selectedSugIndex - 1 + items.length) % items.length;
      updateSuggestionHighlight(items);
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (currentSuggestions[selectedSugIndex]) {
        selectSuggestion(currentSuggestions[selectedSugIndex].symbol);
      } else {
        const val = elements.symbolInput.value.trim();
        if (val) loadDossier(val);
      }
    } else if (e.key === "Escape") {
      hideAutocompleteDropdown();
    }
  });

  // 6. 点击外部区域收起联想面板
  document.addEventListener("click", (e) => {
    if (!e.target.closest("#searchBoxContainer")) {
      hideAutocompleteDropdown();
    }
  });

  // 7. 清空按钮
  elements.btnClearSearch.addEventListener("click", () => {
    elements.symbolInput.value = "";
    elements.btnClearSearch.style.display = "none";
    renderDefaultSuggestions();
    elements.symbolInput.focus();
  });

  // 8. 表单提交（点击搜索按钮或输入框按回车）：默认进入选中的联想词
  elements.searchForm.addEventListener("submit", (e) => {
    e.preventDefault();
    if (currentSuggestions.length > 0 && selectedSugIndex >= 0 && selectedSugIndex < currentSuggestions.length) {
      selectSuggestion(currentSuggestions[selectedSugIndex].symbol);
    } else {
      const val = elements.symbolInput.value.trim();
      if (val) loadDossier(val);
    }
  });

  // 9. 显式按钮点击
  if (elements.btnSubmitSearch) {
    elements.btnSubmitSearch.addEventListener("click", (e) => {
      e.preventDefault();
      if (currentSuggestions.length > 0 && selectedSugIndex >= 0 && selectedSugIndex < currentSuggestions.length) {
        selectSuggestion(currentSuggestions[selectedSugIndex].symbol);
      } else {
        const val = elements.symbolInput.value.trim();
        if (val) loadDossier(val);
      }
    });
  }

  // 10. 热门快速标签点击
  elements.quickPills.addEventListener("click", (e) => {
    const pill = e.target.closest(".pill-btn");
    if (pill) {
      const sym = pill.dataset.symbol;
      loadDossier(sym);
    }
  });

  // 11. 返回首页
  elements.btnBackHome.addEventListener("click", () => {
    showHomeView();
  });

  // 12. 历史档案模态抽屉
  elements.btnOpenHistory.addEventListener("click", openHistoryModal);
  elements.btnHeaderHistory.addEventListener("click", openHistoryModal);
  elements.btnCloseHistory.addEventListener("click", closeHistoryModal);
  elements.historyModal.addEventListener("click", (e) => {
    if (e.target === elements.historyModal) closeHistoryModal();
  });

  // 13. 专题卡片 Tab 切换
  elements.topicTabsBar.addEventListener("click", (e) => {
    const btn = e.target.closest(".topic-tab-btn");
    if (!btn) return;
    const mod = btn.dataset.module;
    if (mod) {
      switchTopicTab(mod);
    }
  });

  // 14. 局部热刷新
  elements.btnRefreshModule.addEventListener("click", () => {
    refreshCurrentModule();
  });

  // 15. 热同步今日最新收盘价
  elements.btnSyncPrice.addEventListener("click", () => {
    hotSyncPrice();
  });
}

// ==============================================================================
// Autocomplete Suggestions Engine
// ==============================================================================

/**
 * 当输入框获得焦点且为空时，呈现默认联想面板：
 * - 若有检索历史：优先展示最近已检索档案（⚡已检索 · 秒开）
 * - 若无历史：展示热门关注美股
 */
function renderDefaultSuggestions() {
  const dropdown = elements.autocompleteDropdown;
  const wrapper = elements.searchInputWrapper;
  if (!dropdown) return;

  const historyItems = state.historyList || [];

  if (historyItems.length > 0) {
    // 渲染最近已检索历史（秒开列表）
    const list = historyItems.slice(0, 6).map(item => {
      const ticker = (item.symbol || "").replace(".US", "");
      // 尝试匹配预设库里的行业描述
      const found = US_STOCK_UNIVERSE.find(u => u.ticker === ticker);
      return {
        symbol: item.symbol,
        ticker: ticker,
        name_cn: item.name || `${ticker} 股票`,
        name_en: found?.name_en || "US Equity Ticker",
        sector: found?.sector || "已归档投研标的",
        isCached: true,
        price: item.price,
        change_pct: item.change_pct
      };
    });

    currentSuggestions = list;
    selectedSugIndex = 0;

    dropdown.innerHTML = `
      <div class="dropdown-header">
        <span>🕒 最近已检索美股档案 · 点击秒开</span>
        <span class="header-badge">${historyItems.length} 标的已入库</span>
      </div>
      <ul class="suggestion-list">
        ${list.map((item, idx) => renderSuggestionItemHtml(item, idx, true)).join("")}
      </ul>
      <div class="dropdown-footer">
        <span class="footer-key-hint">
          <kbd>↑</kbd><kbd>↓</kbd> 切换 · <kbd>↵ Enter</kbd> 默认调阅 · 或输入代码搜索
        </span>
        <span>聚焦美股市场</span>
      </div>
    `;
    attachSuggestionEvents(dropdown);
    dropdown.style.display = "block";
    if (wrapper) wrapper.classList.add("has-dropdown");
  } else {
    // 历史为空：展示精选美股池
    const list = US_STOCK_UNIVERSE.slice(0, 6).map(u => ({ ...u, isCached: false }));
    currentSuggestions = list;
    selectedSugIndex = 0;

    dropdown.innerHTML = `
      <div class="dropdown-header">
        <span>🔥 热门美股直达关注池</span>
        <span class="header-badge">支持任意美股代码</span>
      </div>
      <ul class="suggestion-list">
        ${list.map((item, idx) => renderSuggestionItemHtml(item, idx, false)).join("")}
      </ul>
      <div class="dropdown-footer">
        <span class="footer-key-hint">
          <kbd>↑</kbd><kbd>↓</kbd> 切换 · <kbd>↵ Enter</kbd> 默认调阅
        </span>
        <span>聚焦美股市场</span>
      </div>
    `;
    attachSuggestionEvents(dropdown);
    dropdown.style.display = "block";
    if (wrapper) wrapper.classList.add("has-dropdown");
  }
}

/**
 * 根据键入的美股字母实时匹配联想词
 */
function renderAutocompleteDropdown(query) {
  const q = query.trim().toUpperCase().replace(".US", "");
  const dropdown = elements.autocompleteDropdown;
  const wrapper = elements.searchInputWrapper;

  if (!q) {
    renderDefaultSuggestions();
    return;
  }

  // 1. 构建历史速查 Map
  const historyMap = new Map();
  (state.historyList || []).forEach(item => {
    historyMap.set(item.symbol.toUpperCase(), item);
    historyMap.set(item.symbol.toUpperCase().replace(".US", ""), item);
  });

  // 2. 标的池匹配：优先遍历预置库
  const pool = [...US_STOCK_UNIVERSE];

  // 如果历史中有不在预设池中的自定义标的，也加入联想池
  (state.historyList || []).forEach(hist => {
    const t = hist.symbol.replace(".US", "");
    if (!pool.some(p => p.ticker === t)) {
      pool.push({
        symbol: hist.symbol,
        ticker: t,
        name_cn: hist.name || `${t} 股票`,
        name_en: "Custom US Equity",
        sector: "历史已检索标的"
      });
    }
  });

  // 3. 过滤匹配项（匹配代码前缀、包含、公司中文名、英文名）
  let matches = pool.filter(item => {
    return item.ticker.startsWith(q) ||
           item.ticker.includes(q) ||
           item.name_cn.includes(q) ||
           item.name_en.toUpperCase().includes(q);
  });

  // 4. 排序算法：
  // 规则 A: 精确代码匹配绝对置顶 (ticker === q)
  // 规则 B: 代码前缀匹配优先 (ticker.startsWith(q))
  // 规则 C: 同等前缀下，【已检索过的标的优先置顶并带秒开徽标】 (isCached === true)
  // 规则 D: 按字母字典升序
  matches.sort((a, b) => {
    const aHist = historyMap.has(a.symbol) || historyMap.has(a.ticker);
    const bHist = historyMap.has(b.symbol) || historyMap.has(b.ticker);
    const aExact = a.ticker === q;
    const bExact = b.ticker === q;
    const aPrefix = a.ticker.startsWith(q);
    const bPrefix = b.ticker.startsWith(q);

    if (aExact && !bExact) return -1;
    if (!aExact && bExact) return 1;

    // 前缀匹配优先
    if (aPrefix && !bPrefix) return -1;
    if (!aPrefix && bPrefix) return 1;

    // 在同为前缀匹配（或非前缀）下，已检索过的标的排在最前！
    if (aHist && !bHist) return -1;
    if (!aHist && bHist) return 1;

    return a.ticker.localeCompare(b.ticker);
  });

  // 5. 若当前输入的代码不在匹配列表中，动态增加该美股代码项（支持任意美股代码建档）
  const hasExact = matches.some(m => m.ticker === q);
  if (!hasExact && q.length >= 1) {
    const symFull = `${q}.US`;
    const histItem = historyMap.get(symFull) || historyMap.get(q);
    const customItem = {
      symbol: symFull,
      ticker: q,
      name_cn: histItem?.name || `${q} 美股直通`,
      name_en: "Direct US Equity",
      sector: "实时行情与AI深度建档",
      isCustom: true
    };
    if (matches.length === 0) {
      matches.unshift(customItem);
    } else if (q.length >= 2) {
      matches.push(customItem);
    }
  }

  // 限制展现前 6 项最佳候选
  matches = matches.slice(0, 6);

  currentSuggestions = matches;
  selectedSugIndex = 0; // 默认选中第 0 项

  if (!matches.length) {
    hideAutocompleteDropdown();
    return;
  }

  dropdown.innerHTML = `
    <div class="dropdown-header">
      <span>🎯 美股智能联想 · ↵ Enter 默认调阅</span>
      <span class="header-badge">${matches.length} 候选标的</span>
    </div>
    <ul class="suggestion-list">
      ${matches.map((item, idx) => {
        const hist = historyMap.get(item.symbol) || historyMap.get(item.ticker);
        const isCached = Boolean(hist);
        const price = hist?.price != null ? hist.price : item.price;
        return renderSuggestionItemHtml({ ...item, price }, idx, isCached);
      }).join("")}
    </ul>
    <div class="dropdown-footer">
      <span class="footer-key-hint">
        <kbd>↑</kbd><kbd>↓</kbd> 切换候选词 · <kbd>↵ Enter</kbd> 默认调阅
      </span>
      <span>聚焦美股市场</span>
    </div>
  `;

  attachSuggestionEvents(dropdown);
  dropdown.style.display = "block";
  if (wrapper) wrapper.classList.add("has-dropdown");
}

function renderSuggestionItemHtml(item, idx, isCached) {
  const isSelected = idx === selectedSugIndex;
  const priceStr = item.price != null ? `$${Number(item.price).toFixed(2)}` : null;

  return `
    <li class="suggestion-item ${isSelected ? 'selected' : ''}" data-index="${idx}" data-symbol="${escapeHtml(item.symbol)}">
      <div class="suggestion-left">
        <span class="sug-symbol-badge">${escapeHtml(item.symbol)}</span>
        <div class="sug-info">
          <span class="sug-name-cn">${escapeHtml(item.name_cn)}</span>
          <span class="sug-desc">${escapeHtml(item.sector)} · ${escapeHtml(item.name_en)}</span>
        </div>
      </div>
      <div class="suggestion-right">
        ${priceStr ? `<span class="sug-price-tag">${priceStr}</span>` : ''}
        ${isCached ? `
          <span class="sug-status-badge cached" title="本地数据库已归档，无需等待大模型重新推理，0毫秒极速秒开">
            <span class="badge-pulse-dot"></span>
            <span>⚡ 已检索 · 秒开</span>
          </span>
        ` : `
          <span class="sug-status-badge fresh" title="未在本地归档，调阅时将调用行情接口与大模型深度审计">首次建档</span>
        `}
        <span class="sug-enter-hint"><kbd>↵ 调阅</kbd></span>
      </div>
    </li>
  `;
}

function attachSuggestionEvents(dropdown) {
  const items = dropdown.querySelectorAll(".suggestion-item");
  items.forEach(el => {
    // 鼠标划入时即刻同步选中态
    el.addEventListener("mouseenter", () => {
      const idx = parseInt(el.dataset.index, 10);
      if (!isNaN(idx)) {
        selectedSugIndex = idx;
        updateSuggestionHighlight(items);
      }
    });

    // 点击直接进入下一页调阅详情
    el.addEventListener("click", () => {
      const sym = el.dataset.symbol;
      selectSuggestion(sym);
    });
  });
}

function updateSuggestionHighlight(items) {
  items.forEach((item, idx) => {
    item.classList.toggle("selected", idx === selectedSugIndex);
  });
  if (items[selectedSugIndex]) {
    items[selectedSugIndex].scrollIntoView({ block: "nearest" });
  }
}

function hideAutocompleteDropdown() {
  const dropdown = elements.autocompleteDropdown;
  const wrapper = elements.searchInputWrapper;
  if (dropdown) dropdown.style.display = "none";
  if (wrapper) wrapper.classList.remove("has-dropdown");
  currentSuggestions = [];
  selectedSugIndex = 0;
}

function selectSuggestion(symbol) {
  hideAutocompleteDropdown();
  loadDossier(symbol);
}

// ==============================================================================
// API Communications & Data Flow
// ==============================================================================

/**
 * Fetch or generate dossier for a symbol with instant visual feedback.
 */
async function loadDossier(symbol, force = false) {
  hideAutocompleteDropdown();
  const normSymbol = normalizeInputSymbol(symbol);
  if (!normSymbol) return;

  state.currentSymbol = normSymbol;

  // 1. Instant button loading feedback
  const searchBtn = elements.btnSubmitSearch || document.getElementById("btnSubmitSearch");
  const origBtnHtml = searchBtn ? searchBtn.innerHTML : "";
  if (searchBtn) {
    searchBtn.innerHTML = `<span>调阅中...</span> <span class="icon spinning">🔄</span>`;
    searchBtn.disabled = true;
  }

  // 2. Instant overlay display
  elements.loadingTitle.textContent = `正在调阅【${normSymbol}】全景投研档案...`;
  elements.loadingDesc.textContent = "本地归档 0 毫秒秒开；首次深度建档仅需调阅行情与基本面估值 (约 1~2 秒)";
  elements.globalLoading.style.display = "flex";

  try {
    const resp = await fetch(`/api/dossier?symbol=${encodeURIComponent(normSymbol)}&force=${force ? 1 : 0}`);
    const data = await resp.json();
    if (!data.ok || !data.dossier) {
      throw new Error(data.error || "构建档案失败");
    }
    state.currentDossier = data.dossier;
    renderDossier();
    showDossierView();
    window.location.hash = `#/dossier/${normSymbol}`;
    loadHistoryCount();
  } catch (err) {
    alert(`调阅【${normSymbol}】失败：${err.message}`);
    showHomeView();
  } finally {
    elements.globalLoading.style.display = "none";
    if (searchBtn) {
      searchBtn.innerHTML = origBtnHtml || `<span>深度调阅</span> <kbd>↵</kbd>`;
      searchBtn.disabled = false;
    }
  }
}

/**
 * Component-Level Hot Refresh: Re-computes only the active module.
 */
async function refreshCurrentModule() {
  if (!state.currentSymbol || !state.activeModule) return;
  const mod = state.activeModule;
  const btn = elements.btnRefreshModule;
  const icon = btn.querySelector(".icon");

  icon.classList.add("spinning");
  btn.disabled = true;

  // Add subtle pulse on content area
  elements.topicContentArea.style.opacity = "0.5";

  try {
    const resp = await fetch("/api/dossier/refresh-module", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol: state.currentSymbol, module: mod })
    });
    const res = await resp.json();
    if (!res.ok) throw new Error(res.error || "局部刷新失败");

    // Update in-memory state
    if (state.currentDossier && state.currentDossier.modules) {
      state.currentDossier.modules[mod] = res.module_entry;
    }
    renderTopicStage();
  } catch (err) {
    alert(`刷新专题失败：${err.message}`);
  } finally {
    icon.classList.remove("spinning");
    btn.disabled = false;
    elements.topicContentArea.style.opacity = "1";
  }
}

/**
 * Sub-second price sync without re-running heavy models.
 */
async function hotSyncPrice() {
  if (!state.currentSymbol) return;
  const btn = elements.btnSyncPrice;
  const originalText = btn.innerHTML;
  btn.innerHTML = `<span class="icon spinning">⚡</span> 同步中...`;
  btn.disabled = true;

  try {
    const resp = await fetch("/api/dossier/sync-price", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol: state.currentSymbol })
    });
    const res = await resp.json();
    if (!res.ok) throw new Error(res.error || "同步失败");

    state.currentDossier = res.dossier;
    renderHeaderInfo();
    // If currently viewing valuation or technical, refresh stage
    if (["valuation_matrix", "technical_compass"].includes(state.activeModule)) {
      renderTopicStage();
    }
  } catch (err) {
    console.error("Sync price failed:", err);
  } finally {
    btn.innerHTML = originalText;
    btn.disabled = false;
  }
}

// ==============================================================================
// Rendering: Header & Stage
// ==============================================================================

function renderDossier() {
  if (!state.currentDossier) return;
  renderHeaderInfo();
  switchTopicTab(state.activeModule || "business_and_industry");
}

function renderHeaderInfo() {
  const d = state.currentDossier;
  const sym = d.symbol;
  const name = d.name || sym;
  const p = d.price != null ? `$${Number(d.price).toFixed(2)}` : "--";
  const chg = d.change_pct != null ? Number(d.change_pct).toFixed(2) : "0.00";

  elements.stockName.textContent = name;
  elements.stockSymbol.textContent = sym;
  elements.stockPrice.textContent = p;

  const chgPill = elements.stockChangePct;
  chgPill.textContent = `${chg >= 0 ? "+" : ""}${chg}%`;
  chgPill.className = `stock-change-pill ${chg > 0 ? "positive" : chg < 0 ? "negative" : "neutral"}`;

  elements.stockValStatus.textContent = d.valuation_status || "估值分析中";

  // Short essence
  const bizData = (d.modules?.business_and_industry?.data) || {};
  const essenceText = typeof bizData.essence === "object" ? (bizData.essence?.summary || "") : (bizData.essence || "");
  elements.stockEssenceShort.textContent = essenceText || "正在提取商业模式与护城河...";
}

function switchTopicTab(moduleName) {
  state.activeModule = moduleName;
  const allBtns = elements.topicTabsBar.querySelectorAll(".topic-tab-btn");
  allBtns.forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.module === moduleName);
  });
  renderTopicStage();
}

function renderTopicStage() {
  const mod = state.activeModule;
  const meta = MODULE_META[mod] || { title: "专题分析", icon: "📄" };
  const modEntry = state.currentDossier?.modules?.[mod] || {};
  const data = modEntry.data || {};

  elements.topicIcon.textContent = meta.icon;
  elements.topicTitle.textContent = meta.title;

  const updatedTime = modEntry.updated_at ? formatTimeAgo(modEntry.updated_at) : "刚刚";
  elements.topicTimestamp.textContent = `🕒 本专题更新于：${updatedTime}`;

  const container = elements.topicContentArea;
  container.innerHTML = "";

  switch (mod) {
    case "business_and_industry":
      renderBusinessAndIndustry(container, data);
      break;
    case "core_products":
      renderCoreProducts(container, data);
      break;
    case "valuation_matrix":
      renderValuationMatrix(container, data);
      break;
    case "technical_compass":
      renderTechnicalCompass(container, data);
      break;
    case "capital_allocation":
      renderCapitalAllocation(container, data);
      break;
    case "ai_memo":
      renderAiMemo(container, data);
      break;
    default:
      container.innerHTML = `<p class="text-muted">暂无内容</p>`;
  }
}

// ==============================================================================
// Topic Renderers
// ==============================================================================

/**
 * Module 1: Business Essence & Industry Peers (Deepened & Institutional)
 */
function renderBusinessAndIndustry(container, data) {
  const ind = data.industry || {};
  const peers = ind.competitors || [];

  // 1. Essence and Profit Engine extraction
  const isObjEssence = typeof data.essence === "object" && data.essence !== null;
  const summaryText = isObjEssence ? (data.essence.summary || "长桥未返回公司简介") : (data.essence || "长桥未返回公司简介");
  const profitEngineText = isObjEssence ? (data.essence.profit_engine || "") : "";
  const flywheelText = isObjEssence ? (data.essence.flywheel || "") : "";
  const segmentsList = isObjEssence ? (data.essence.segments || []) : [];
  const isPreset = !!data.is_preset;
  const missingNote = "未从单期财报得出该项结论。";

  // 2. Lifecycle. Missing fields stay blank. Do not invent a cash-cow stage.
  const lc = typeof ind.lifecycle === "object" && ind.lifecycle !== null ? ind.lifecycle : {
    current_stage: typeof ind.lifecycle === "string" && ind.lifecycle ? ind.lifecycle : "未披露",
    stage_index: -1,
    all_stages: [],
    characteristics: missingNote,
    is_good_or_bad: {
      pros: missingNote,
      cons: missingNote
    },
    long_term_strategy: "单期快照不足以给出配置建议。"
  };

  const currentIdx = typeof lc.stage_index === "number" ? lc.stage_index : -1;
  const allStages = Array.isArray(lc.all_stages) ? lc.all_stages : [];

  const prosText = lc.is_good_or_bad?.pros || missingNote;
  const consText = lc.is_good_or_bad?.cons || missingNote;
  const strategyText = lc.long_term_strategy || "单期快照不足以给出配置建议。";
  const prosTitle = isPreset ? "✅ 好在哪里？(阶段买方红利与确定性)" : "单期已披露";
  const consTitle = isPreset ? "⚠️ 坏在哪里？(阶段隐患与增长枷锁)" : "尚未取得";
  const strategyTitle = isPreset ? "🎯 中长线投资研判指引：" : "配置建议：";
  const lifecycleHeading = isPreset ? "⏳ 企业生命周期五阶段演进罗盘" : "⏳ 单期营收同比";
  const lifecycleSub = isPreset ? "（全周期坐标体系与买方好坏评判）" : "（未取得多期序列，不判断生命周期）";

  container.innerHTML = `
    <!-- 数据来源真实性透明披露 -->
    ${data.is_preset ? `
      <div style="background:rgba(234, 179, 8, 0.12); color:#fbbf24; border:1px solid rgba(234, 179, 8, 0.35); padding:8px 12px; border-radius:6px; margin-bottom:14px; font-size:12px; font-weight:600; display:flex; align-items:center; gap:6px;">
        <span>⚠️ 数据源标注：人工投研预置库整理 · 未与本期官方审计财报逐项核对</span>
      </div>
    ` : `
      <div style="background:rgba(56, 189, 248, 0.12); color:#38bdf8; border:1px solid rgba(56, 189, 248, 0.35); padding:8px 12px; border-radius:6px; margin-bottom:14px; font-size:12px; font-weight:600; display:flex; align-items:center; gap:6px;">
        <span>📋 数据源标注：非预置标的 · 仅展示长桥公司简介原文与单期财务同比（未做人工商业模式与同业笔记）</span>
      </div>
    `}

    <!-- 1. 商业本质与底层盈利引擎看板 (合并主营业务，深度剖析) -->
    <div class="profit-engine-box">
      <div class="profit-summary-title">
        <span>🏢 商业本质与底层盈利引擎 (Business Model & Profit Engine)</span>
      </div>
      <p style="font-size:14px; color:#f1f5f9; line-height:1.6; margin-bottom:14px;">
        <strong>【战略定位】</strong>${escapeHtml(summaryText)}
      </p>

      ${profitEngineText ? `
        <div class="profit-truth-content">
          ${escapeHtml(profitEngineText)}
        </div>
      ` : ""}

      ${flywheelText ? `
        <div class="flywheel-flow">
          <span class="flywheel-badge">🔄 核心业务飞轮</span>
          <span>${escapeHtml(flywheelText)}</span>
        </div>
      ` : ""}

      ${segmentsList.length ? `
        <div class="segments-role-grid">
          ${segmentsList.map(s => `
            <div class="segment-role-card">
              <div class="segment-role-header">
                <span class="segment-role-name">${escapeHtml(s.name)}</span>
                <span class="segment-role-ratio">${escapeHtml(s.ratio || "")}</span>
              </div>
              <div class="segment-role-desc">${escapeHtml(s.role || "")}</div>
            </div>
          `).join("")}
        </div>
      ` : ""}
    </div>

    <!-- 2. 公司基本事实与经营档案 (赛道严禁显示交易所) -->
    <h4 class="section-headline">📊 公司基本事实与赛道界定</h4>
    <div class="facts-row-grid">
      <div class="fact-stat-card">
        <div class="fact-stat-label">所处核心赛道 (精准行业)</div>
        <div class="fact-stat-value" style="font-size:13px; color:#38bdf8;">${escapeHtml(ind.sector || "未归类")}</div>
      </div>
      <div class="fact-stat-card">
        <div class="fact-stat-label">生命周期坐标</div>
        <div class="fact-stat-value" style="font-size:13px;">${escapeHtml(lc.current_stage || "未披露")}</div>
      </div>
      <div class="fact-stat-card">
        <div class="fact-stat-label">全球全职员工</div>
        <div class="fact-stat-value">${data.employees ? Number(data.employees).toLocaleString() + " 人" : "未披露"}</div>
      </div>
      <div class="fact-stat-card">
        <div class="fact-stat-label">管理层掌门人 (CEO)</div>
        <div class="fact-stat-value">${escapeHtml(data.manager || "未披露")}</div>
      </div>
    </div>

    <!-- 3. 企业生命周期五阶段演进罗盘与好坏评判 -->
    <div class="lifecycle-stepper-container">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
        <h4 style="margin:0; font-size:15px; color:#fff; display:flex; align-items:center; gap:8px;">
          <span>${lifecycleHeading}</span>
          <span style="font-size:11px; font-weight:normal; color:var(--text-dim);">${lifecycleSub}</span>
        </h4>
        <span style="font-size:12px; color:#93c5fd; background:rgba(59,130,246,0.15); padding:2px 8px; border-radius:4px;">
          ${currentIdx >= 0 ? `当前坐标：第 ${currentIdx + 1} 阶段` : escapeHtml(lc.current_stage || "未披露")}
        </span>
      </div>

      ${allStages.length ? `<div class="lifecycle-stepper">
        <div class="stepper-line"></div>
        ${allStages.map((st, idx) => {
          const isPassed = idx < currentIdx;
          const isActive = idx === currentIdx;
          return `
            <div class="stepper-step ${isActive ? 'active' : isPassed ? 'passed' : ''}">
              <div class="stepper-circle">${isPassed ? '✓' : idx + 1}</div>
              <span class="stepper-label">${escapeHtml(st.name)}</span>
              ${isActive ? `<span class="stepper-badge-current">当前阶段</span>` : `<span style="font-size:10px; color:var(--text-dim); margin-top:4px;">${escapeHtml(st.desc)}</span>`}
            </div>
          `;
        }).join("")}
      </div>` : ""}

      <div class="lifecycle-pro-con-grid">
        <div class="verdict-box pros">
          <div class="verdict-title">
            <span>${prosTitle}</span>
          </div>
          <div>${escapeHtml(prosText)}</div>
        </div>
        <div class="verdict-box cons">
          <div class="verdict-title">
            <span>${consTitle}</span>
          </div>
          <div>${escapeHtml(consText)}</div>
        </div>
      </div>

      <div class="lifecycle-strategy-box">
        <span style="color:#93c5fd; font-weight:bold;">${strategyTitle}</span>
        <span>${escapeHtml(strategyText)}</span>
      </div>
    </div>

    <!-- 4. 宏观经济形势结合与中观行业空间 (TAM) -->
    <div class="macro-backdrop-box">
      <span class="macro-tag">🌍 宏观经济形势与中观赛道渗透 (Macro & TAM)</span>
      ${ind.macro_backdrop ? `
        <p style="margin:6px 0 12px; color:#e2e8f0; font-size:13px; line-height:1.65;">
          ${escapeHtml(ind.macro_backdrop)}
        </p>
      ` : ""}
      <div style="background:rgba(0,0,0,0.25); padding:10px 14px; border-radius:8px; border-left:3px solid #8b5cf6;">
        <strong style="color:#c4b5fd;">行业总潜在空间 (TAM) 与中观空间：</strong>
        <span style="color:#cbd5e1; font-size:13px;">${escapeHtml(ind.tam || "未取得官方口径市场空间。")}</span>
      </div>
    </div>

    <!-- 5. 同行业竞争格局与中微观博弈天梯 (Peer Matrix) -->
    <h4 class="section-headline">⚔️ 同行业竞争格局与竞对天梯 (Peer Matrix)</h4>
    <div class="peer-table-container">
      <table class="peer-table">
        <thead>
          <tr>
            <th style="width: 22%;">主要竞争对手</th>
            <th style="width: 12%;">威胁等级</th>
            <th style="width: 32%;">市场地位与中观博弈点</th>
            <th style="width: 34%;">本公司微观差异化突围战略</th>
          </tr>
        </thead>
        <tbody>
          ${peers.length ? peers.map(p => {
            const symBadge = p.symbol ? `<span class="peer-symbol">${escapeHtml(p.symbol)}</span>` : "";
            const threatClass = p.threat?.includes('高') ? 'high' : p.threat?.includes('中') ? 'mid' : 'low';
            const diffText = p.bj_differentiation || p.differentiation || p.status || "--";
            const compText = p.comparison || p.status || p.market_position || "--";

            return `
              <tr>
                <td>
                  <strong>${escapeHtml(p.name)}</strong>
                  ${symBadge}
                  ${p.market_position ? `<div style="font-size:11px; color:var(--text-dim); margin-top:2px;">${escapeHtml(p.market_position)}</div>` : ''}
                </td>
                <td>
                  <span class="badge-threat ${threatClass}">
                    ${escapeHtml(p.threat || '中')}
                  </span>
                </td>
                <td style="color:#cbd5e1; line-height:1.5;">${escapeHtml(compText)}</td>
                <td class="differentiation-cell">${escapeHtml(diffText)}</td>
              </tr>
            `;
          }).join("") : `<tr><td colspan="4" class="text-muted">${isPreset ? "暂无竞对细分数据" : "未取得经核对的同业名单。"}</td></tr>`}
        </tbody>
      </table>
    </div>
  `;
}

/**
 * Module 2: Core Products & Tech Teardown (Killer Feature)
 */
/**
 * Module 2: Core Products & Tech Teardown (Institutional 4-Dimension Teardown)
 */
function renderCoreProducts(container, data) {
  const products = data.products || [];
  const chain = data.supply_chain || {};
  const spofList = chain.spof_bottlenecks || [];
  const bargaining = chain.customer_bargaining || {};

  function getRoleBadgeClass(roleStr) {
    if (!roleStr) return { cls: "role-default", icon: "🏷️" };
    if (roleStr.includes("增长") || roleStr.includes("爆发") || roleStr.includes("引擎") || roleStr.includes("Growth")) {
      return { cls: "role-growth", icon: "🚀" };
    }
    if (roleStr.includes("现金牛") || roleStr.includes("压舱石") || roleStr.includes("收割") || roleStr.includes("Cash")) {
      return { cls: "role-cash", icon: "💰" };
    }
    if (roleStr.includes("防御") || roleStr.includes("护城河") || roleStr.includes("盾") || roleStr.includes("生态") || roleStr.includes("Shield")) {
      return { cls: "role-defense", icon: "🛡️" };
    }
    if (roleStr.includes("期权") || roleStr.includes("颠覆") || roleStr.includes("第二曲线") || roleStr.includes("Option")) {
      return { cls: "role-option", icon: "⚡" };
    }
    return { cls: "role-growth", icon: "📌" };
  }

  function getSwitchingCostBadge(costStr) {
    if (!costStr || costStr.includes("未")) return `<span class="switching-cost-badge" style="background:rgba(148,163,184,0.15);color:#94a3b8;border:1px solid rgba(148,163,184,0.3);">未做笔记</span>`;
    let cls = "mid";
    if (costStr.includes("极高")) cls = "extreme";
    else if (costStr.includes("高")) cls = "high";
    else if (costStr.includes("低")) cls = "low";
    return `<span class="switching-cost-badge ${cls}">${escapeHtml(costStr)}</span>`;
  }

  function getSpofThreatBadge(lvl) {
    if (!lvl) return `<span class="spof-threat-badge mid">中</span>`;
    let cls = "mid";
    if (lvl.includes("极高")) cls = "extreme";
    else if (lvl.includes("高")) cls = "high";
    else if (lvl.includes("低")) cls = "low";
    return `<span class="spof-threat-badge ${cls}">${escapeHtml(lvl)}威胁</span>`;
  }

  container.innerHTML = `
    <!-- 产品页透明标注 (Rule P0 2) -->
    ${data.is_preset ? `
      <div style="background:rgba(234, 179, 8, 0.12); color:#fbbf24; border:1px solid rgba(234, 179, 8, 0.35); padding:8px 12px; border-radius:6px; margin-bottom:14px; font-size:12px; font-weight:600; display:flex; align-items:center; gap:6px;">
        <span>⚠️ 数据源标注：产品笔记为人工投研整理，非长桥或官方审计分部财报披露；毛利率与市占为行业估计笔记</span>
      </div>
    ` : `
      <div style="background:rgba(56, 189, 248, 0.12); color:#38bdf8; border:1px solid rgba(56, 189, 248, 0.35); padding:8px 12px; border-radius:6px; margin-bottom:14px; font-size:12px; font-weight:600; display:flex; align-items:center; gap:6px;">
        <span>📋 数据源标注：非人工预置标的 · 仅展示长桥官方主营概况，未录入细分产品与产业链人工笔记</span>
      </div>
    `}

    <div class="highlight-box">
      <strong>【买方机构级透视：核心产品四维解构与产业链排雷】</strong><br/>
      买股票本质是买产品矩阵、技术壁垒与客户黏性。拒绝泛泛而谈，穿透拆解产品战略定位、预估毛利率区间、客户弃用替换成本 (Switching Cost)，以及产业链单一故障点 (SPOF) 瓶颈。
    </div>

    <div class="submodule-header-row">
      <h4 class="section-headline" style="margin-bottom:0;">📦 核心拳头产品矩阵与战略梯队 (Strategic Products Matrix)</h4>
      <span class="text-muted" style="font-size:12px;">共穿透剖析 ${products.length} 个核心产品/业务线</span>
    </div>

    <div class="products-cards-grid">
      ${products.length > 0 ? products.map(item => {
        const roleInfo = getRoleBadgeClass(item.strategic_role || "");
        const revRatio = item.revenue_ratio || "主营构成";
        const marginStr = item.gross_margin || "行业优势毛利";
        const barrierTitle = item.barrier_type || "底层核心技术与制造壁垒";
        const barrierDetail = item.barrier_detail || item.barrier || "具备深厚专利与先发技术壁垒。";
        const sCurve = item.s_curve_stage || "成熟收割期";
        const prospect = item.prospect_and_catalysts || item.prospect || "受益于行业升级与渗透率稳健扩张。";
        const marketShare = item.market_share || "全球细分市场重要龙头";
        const bizModel = item.business_model || "软硬件直销与配套服务";

        return `
          <div class="product-teardown-card">
            <div class="product-teardown-header">
              <div class="product-title-group">
                <span class="product-name-title">${escapeHtml(item.name || "核心产品")}</span>
                <span class="product-category-pill">${escapeHtml(item.category || "主营业务")}</span>
                ${item.strategic_role ? `
                  <span class="strategic-role-badge ${roleInfo.cls}">
                    ${roleInfo.icon} ${escapeHtml(item.strategic_role)}
                  </span>
                ` : ""}
              </div>

              <div class="product-financial-metrics">
                <div class="metric-pair">
                  <span class="metric-pair-label">营收占比 (笔记):</span>
                  <span class="metric-pair-val highlight">${escapeHtml(revRatio)}</span>
                </div>
                <span style="color:rgba(255,255,255,0.2);">|</span>
                <div class="metric-pair">
                  <span class="metric-pair-label">毛利率估算 (笔记):</span>
                  <span class="metric-pair-val" style="color:#fbbf24;">${escapeHtml(marginStr)}</span>
                </div>
              </div>
            </div>

            <div class="product-quad-grid">
              <!-- Cell 1: Technical Moat -->
              <div class="quad-cell">
                <div class="quad-cell-header">
                  <div class="quad-cell-title title-moat">🛡️ 核心技术壁垒与研发护城河</div>
                  <span class="text-muted" style="font-size:11px;">技术本质</span>
                </div>
                <div style="font-size:12px; font-weight:700; color:#93c5fd;">
                  ${escapeHtml(barrierTitle)}
                </div>
                <div class="quad-cell-desc">
                  ${escapeHtml(barrierDetail)}
                </div>
              </div>

              <!-- Cell 2: Switching Cost & Lock-in -->
              <div class="quad-cell">
                <div class="quad-cell-header">
                  <div class="quad-cell-title title-switching">🔒 客户迁移替换成本 (笔记)</div>
                  ${getSwitchingCostBadge(item.switching_cost || "中高")}
                </div>
                <div class="quad-cell-desc">
                  ${item.barrier_detail && (item.barrier_detail.includes("迁移") || item.barrier_detail.includes("替换"))
                    ? escapeHtml(item.barrier_detail) 
                    : (data.is_preset ? `客户弃用或转向竞品面临高重构与适配成本；深度嵌入构筑防御盾。` : `未做人工替换成本笔记（长桥单期快照未披露客户迁移壁垒）。`)}
                </div>
                <div class="quad-sub-highlight">
                  💡 <b>买方防御性研判:</b> 替换成本越高，提价韧性越强，越能抵御逆周期冲击。
                </div>
              </div>

              <!-- Cell 3: S-Curve & Catalysts -->
              <div class="quad-cell">
                <div class="quad-cell-header">
                  <div class="quad-cell-title title-scurve">📈 S型生命周期与关键催化剂</div>
                  <span style="font-size:11px; color:#c084fc; font-weight:600;">阶段: ${escapeHtml(sCurve)}</span>
                </div>
                <div class="quad-cell-desc">
                  <b>未来 6~24 个月催化节点:</b> ${escapeHtml(prospect)}
                </div>
              </div>

              <!-- Cell 4: Market Share & Monetization -->
              <div class="quad-cell">
                <div class="quad-cell-header">
                  <div class="quad-cell-title title-market">💼 市占率估算 (笔记) 与商业变现</div>
                  <span style="font-size:11px; color:#34d399; font-weight:600;">变现闭环</span>
                </div>
                <div class="quad-cell-desc">
                  <b>市场份额 (笔记):</b> ${escapeHtml(marketShare)}<br/>
                  <b>商业模式:</b> ${escapeHtml(bizModel)}
                </div>
              </div>
            </div>
          </div>
        `;
      }).join("") : `<div class="text-muted" style="padding:16px;">长桥官方接口已返回公司主营简介；分部产品拆解属于深度人工投研整理，当前标的暂未录入人工笔记。</div>`}
    </div>

    <!-- Supply Chain & SPOF Bottlenecks (仅在人工预置标的中展示，库外标的杜绝套话) -->
    ${data.is_preset === true && (chain.upstream_dependency || chain.downstream_concentration || spofList.length > 0) ? `
      <div class="submodule-header-row" style="margin-top:28px;">
        <h4 class="section-headline" style="margin-bottom:0;">🔗 产业链咽喉、单一故障点 (SPOF) 与上下游博弈排雷 (人工投研笔记)</h4>
        <span class="text-muted" style="font-size:12px;">买方供应链黑天鹅推演</span>
      </div>

      <div class="supply-chain-cockpit">
        <div class="facts-row-grid" style="grid-template-columns: 1fr 1fr;">
          <div class="fact-stat-card">
            <div class="fact-stat-label">⛓️ 上游供应链依赖 (笔记)</div>
            <div class="fact-stat-value" style="font-size:13px; font-weight:normal; margin-top:6px; line-height:1.5;">
              ${escapeHtml(chain.upstream_dependency || "保持多源供应与核心元器件备份。")}
            </div>
          </div>
          <div class="fact-stat-card">
            <div class="fact-stat-label">👥 下游大客户集中度 (笔记)</div>
            <div class="fact-stat-value" style="font-size:13px; font-weight:normal; margin-top:6px; line-height:1.5;">
              ${escapeHtml(chain.downstream_concentration || "客户结构均衡，单一客户依赖度适中。")}
            </div>
          </div>
        </div>

        ${spofList.length > 0 ? `
          <div style="margin-top:14px;">
            <div style="font-size:12px; font-weight:700; color:#f87171; margin-bottom:8px; display:flex; align-items:center; gap:6px;">
              🚨 单一故障点 (Single Point of Failure / SPOF) 瓶颈排雷
            </div>
            <div class="spof-grid">
              ${spofList.map(item => `
                <div class="spof-card">
                  <div class="spof-card-header">
                    <span class="spof-node-name">⚠️ ${escapeHtml(item.node)}</span>
                    ${getSpofThreatBadge(item.threat_level)}
                  </div>
                  <div class="spof-impact-text">
                    ${escapeHtml(item.impact)}
                  </div>
                </div>
              `).join("")}
            </div>
          </div>
        ` : ""}
      </div>
    ` : `
      <div style="background:rgba(56, 189, 248, 0.08); color:#94a3b8; border:1px solid rgba(56, 189, 248, 0.2); border-radius:6px; padding:10px 14px; margin-top:20px; font-size:12px; line-height:1.5;">
        ℹ️ <strong>数据真实性披露：</strong>长桥官方接口未披露分部产业链细节；系统严格遵守「无来源不编造」准则，杜绝为库外股票自动填充虚假元器件供应链与大客户集中度套话。
      </div>
    `}
  `;
}

/**
 * Module 3: Institutional Valuation Matrix
 */
/**
 * Module 3: Institutional Valuation Matrix (Cockpit 2.0)
 */
function renderValuationMatrix(container, data) {
  const mult = data.multiples || {};
  const currentPrice = Number(data.current_price || 0);
  const prem = mult.peer_premium_pct;
  const indLabel = mult.indicator || "P/E";
  const metricVal = mult.metric_value != null ? mult.metric_value : (mult.pe_raw || mult.ps_raw || "--");
  const medianVal = mult.industry_median != null ? mult.industry_median : "--";

  let premClass = "blue";
  let premLabel = "平价合理";
  if (prem != null) {
    if (prem > 50) {
      premClass = "red";
      premLabel = `溢价 +${prem}% (估值偏贵)`;
    } else if (prem > 15) {
      premClass = "yellow";
      premLabel = `溢价 +${prem}% (适度偏高)`;
    } else if (prem >= -15) {
      premClass = "blue";
      premLabel = `贴近中位 (平价合理)`;
    } else {
      premClass = "green";
      premLabel = `折价 ${prem}% (具备防守边际)`;
    }
  }

  const isInsufficient = data.status === "数据不足，不能评级" || (mult.pe_raw == null && mult.ps_raw == null && mult.pb_raw == null);
  const finSum = data.financials_summary || {};
  const targetPriceStr = data.target_price ? `$${Number(data.target_price).toFixed(2)}` : "--";
  const upsideStr = data.target_upside_pct != null ? `${data.target_upside_pct >= 0 ? '+' : ''}${Number(data.target_upside_pct).toFixed(1)}%` : "";
  const ret20Str = data.returns_20d != null ? `${data.returns_20d >= 0 ? '+' : ''}${Number(data.returns_20d).toFixed(1)}%` : "--";
  const stopLossStr = data.trailing_stop_2atr ? `$${Number(data.trailing_stop_2atr).toFixed(2)}` : "--";
  const revStr = finSum.revenue ? `$${(Number(finSum.revenue) / 1e8).toFixed(2)} 亿美元` : "--";
  const revYoyStr = finSum.revenue_yoy != null ? `${finSum.revenue_yoy >= 0 ? '+' : ''}${Number(finSum.revenue_yoy).toFixed(1)}%` : "--";
  const netStr = finSum.net_income ? `$${(Number(finSum.net_income) / 1e8).toFixed(2)} 亿美元` : "--";
  const netYoyStr = finSum.net_income_yoy != null ? `${finSum.net_income_yoy >= 0 ? '+' : ''}${Number(finSum.net_income_yoy).toFixed(1)}%` : "--";
  const debtStr = finSum.debt_to_assets != null ? `${Number(finSum.debt_to_assets).toFixed(1)}%` : "--";

  container.innerHTML = `
    ${isInsufficient ? `
      <!-- Yahoo 降级无假财务警示 (Rule P0 1) -->
      <div style="background:rgba(239, 68, 68, 0.12); color:#fca5a5; border:1px solid rgba(239, 68, 68, 0.35); padding:12px 16px; border-radius:8px; margin-bottom:16px; font-size:13px; font-weight:600; line-height:1.5;">
        ⚠️ <strong>仅行情模式 (长桥官方财务与估值离线)</strong>：数据不足，不能评级。系统已如实保留 Yahoo 真实价格与日 K，估值、评级与财务严格留空，杜绝造假。
      </div>
    ` : ""}

    <!-- 档案先给数字：8维核心估值与单期财务硬数大屏 (Rule P1 10) -->
    <div style="margin-bottom:12px; display:flex; justify-content:space-between; align-items:center;">
      <h4 class="section-headline" style="margin-bottom:0;">📊 核心估值、财务与风控硬数速览 (Verified Hard Facts)</h4>
      <span class="text-muted" style="font-size:12px;">长桥官方披露单期报表与实时行情 · 拒绝虚拟折现</span>
    </div>

    <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:12px; margin-bottom:14px;">
      <div style="background:rgba(15,23,42,0.7); border:1px solid rgba(148,163,184,0.18); border-radius:8px; padding:12px 14px;">
        <div style="font-size:11.5px; color:#94a3b8;">最新市价 (Real-time Price)</div>
        <div style="font-size:22px; font-weight:700; color:#ffffff; font-family:var(--font-mono); margin-top:4px;">
          ${currentPrice > 0 ? `$${currentPrice.toFixed(2)}` : "--"}
        </div>
        <div style="font-size:11px; color:#64748b; margin-top:2px;">长桥 / Yahoo 真实成交价</div>
      </div>

      <div style="background:rgba(15,23,42,0.7); border:1px solid rgba(148,163,184,0.18); border-radius:8px; padding:12px 14px;">
        <div style="font-size:11.5px; color:#94a3b8;">估值乘数 (PE / PS / PB)</div>
        <div style="font-size:16px; font-weight:700; color:#38bdf8; font-family:var(--font-mono); margin-top:6px;">
          ${mult.pe_raw != null ? `${Number(mult.pe_raw).toFixed(1)}x` : "--"} / ${mult.ps_raw != null ? `${Number(mult.ps_raw).toFixed(1)}x` : "--"} / ${mult.pb_raw != null ? `${Number(mult.pb_raw).toFixed(1)}x` : "--"}
        </div>
        <div style="font-size:11px; color:#64748b; margin-top:2px;">长桥官方发布实数</div>
      </div>

      <div style="background:rgba(15,23,42,0.7); border:1px solid rgba(148,163,184,0.18); border-radius:8px; padding:12px 14px;">
        <div style="font-size:11.5px; color:#94a3b8;">目标价与空间 (Target Price)</div>
        <div style="font-size:18px; font-weight:700; color:${data.target_upside_pct != null && data.target_upside_pct > 0 ? '#34d399' : '#f8fafc'}; font-family:var(--font-mono); margin-top:6px;">
          ${targetPriceStr} ${upsideStr ? `<span style="font-size:13px;">(${upsideStr})</span>` : ""}
        </div>
        <div style="font-size:11px; color:#64748b; margin-top:2px;">${escapeHtml(data.rating_label || "华尔街分析师共识")}</div>
      </div>

      <div style="background:rgba(15,23,42,0.7); border:1px solid rgba(148,163,184,0.18); border-radius:8px; padding:12px 14px;">
        <div style="font-size:11.5px; color:#94a3b8;">2×ATR 止损价 (Trailing Stop)</div>
        <div style="font-size:20px; font-weight:700; color:#ef4444; font-family:var(--font-mono); margin-top:4px;">
          ${stopLossStr}
        </div>
        <div style="font-size:11px; color:#64748b; margin-top:2px;">20日动量: <span class="${data.returns_20d != null ? (data.returns_20d >= 0 ? 'text-success' : 'text-danger') : 'text-muted'}">${ret20Str}</span></div>
      </div>
    </div>

    <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:12px; margin-bottom:20px;">
      <div style="background:rgba(15,23,42,0.7); border:1px solid rgba(148,163,184,0.18); border-radius:8px; padding:12px 14px;">
        <div style="font-size:11.5px; color:#94a3b8;">单期营业收入 (Single-period Revenue)</div>
        <div style="font-size:17px; font-weight:700; color:#f8fafc; font-family:var(--font-mono); margin-top:4px;">
          ${revStr}
        </div>
        <div style="font-size:11.5px; color:${finSum.revenue_yoy != null ? (finSum.revenue_yoy >= 0 ? '#34d399' : '#f87171') : '#94a3b8'}; margin-top:2px;">
          同比: <strong>${revYoyStr}</strong>
        </div>
      </div>

      <div style="background:rgba(15,23,42,0.7); border:1px solid rgba(148,163,184,0.18); border-radius:8px; padding:12px 14px;">
        <div style="font-size:11.5px; color:#94a3b8;">单期净利润 (Single-period Net Income)</div>
        <div style="font-size:17px; font-weight:700; color:#f8fafc; font-family:var(--font-mono); margin-top:4px;">
          ${netStr}
        </div>
        <div style="font-size:11.5px; color:${finSum.net_income_yoy != null ? (finSum.net_income_yoy >= 0 ? '#34d399' : '#f87171') : '#94a3b8'}; margin-top:2px;">
          同比: <strong>${netYoyStr}</strong>
        </div>
      </div>

      <div style="background:rgba(15,23,42,0.7); border:1px solid rgba(148,163,184,0.18); border-radius:8px; padding:12px 14px;">
        <div style="font-size:11.5px; color:#94a3b8;">资产负债率 (Debt to Assets)</div>
        <div style="font-size:17px; font-weight:700; color:#f8fafc; font-family:var(--font-mono); margin-top:4px;">
          ${debtStr}
        </div>
        <div style="font-size:11px; color:#64748b; margin-top:2px;">总负债 / 总资产杠杆结构</div>
      </div>
    </div>

    <!-- Top Cockpit: Relative Valuation Radar Header -->
    <div class="fair-value-cockpit" style="grid-template-columns: 240px 1fr;">
      <div class="verdict-gauge-box">
        <div class="safety-margin-num ${premClass}">
          ${prem != null ? `${prem >= 0 ? "+" : ""}${prem}%` : "--"}
        </div>
        <div class="safety-margin-label" style="background:${premClass === 'green' ? 'rgba(52,211,153,0.15)' : premClass === 'yellow' ? 'rgba(251,191,36,0.15)' : premClass === 'blue' ? 'rgba(56,189,248,0.15)' : 'rgba(248,113,113,0.15)'}; color:${premClass === 'green' ? '#34d399' : premClass === 'yellow' ? '#fbbf24' : premClass === 'blue' ? '#38bdf8' : '#f87171'}">
          ${escapeHtml(data.status || premLabel)}
        </div>
        <small style="color:#94a3b8; margin-top:8px;">相对行业中位数溢价率</small>
        <div style="font-size:11.5px; color:#64748b; margin-top:4px;">
          ${prem != null ? (prem > 0 ? "估值高于行业中枢" : "估值低于行业中枢") : "同业中位未披露"}
        </div>
      </div>

      <div class="corridor-display-box">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <div style="font-size:14px; font-weight:700; color:#93c5fd;">🏛️ 长桥同业相对估值雷达 (Relative Multiples Radar)</div>
          <span style="font-size:12px; color:#cbd5e1;">当前市价: <b style="color:#ffffff; font-family:var(--font-mono); font-size:14px;">${currentPrice > 0 ? `$${currentPrice.toFixed(2)}` : '--'}</b></span>
        </div>

        <div class="corridor-range-cards" style="grid-template-columns: repeat(3, 1fr); margin-top:14px;">
          <div class="corridor-pill-card">
            <small>当前 ${escapeHtml(indLabel)} 倍数</small>
            <strong style="color:#f8fafc;">${metricVal}x</strong>
          </div>
          <div class="corridor-pill-card mid">
            <small>行业中位数 (${escapeHtml(indLabel)})</small>
            <strong style="color:#38bdf8;">${medianVal}x</strong>
          </div>
          <div class="corridor-pill-card">
            <small>同业溢折率 (Premium/Discount)</small>
            <strong style="color:${prem != null && prem > 30 ? '#f87171' : (prem != null && prem < -10 ? '#34d399' : '#38bdf8')};">
              ${prem != null ? `${prem >= 0 ? "+" : ""}${prem}%` : "--"}
            </strong>
          </div>
        </div>

        <!-- 严肃买方准则提示 (Rule 1 & P0 3) -->
        <div style="background:rgba(15, 23, 42, 0.6); border:1px solid rgba(148, 163, 184, 0.2); border-radius:6px; padding:10px 12px; margin-top:12px; font-size:12px; color:#94a3b8; line-height:1.5;">
          🛡️ <strong>严肃买方投研准则：</strong>长桥单期报表未返回现金流量表（缺少经营现金流与资本开支 Capex），系统杜绝通过市盈率倒数编造自由现金流(FCF)与虚拟公允价走廊，质量分已封顶 70 分，以确保研究结论的严肃客观。
        </div>
      </div>
    </div>

    <!-- Peer Ranking & Distribution Cockpit -->
    <div class="facts-row-grid" style="grid-template-columns: 1fr 1fr; margin-top:18px;">
      <!-- Card 1: 真实同业估值排位梯队 -->
      <div class="fact-stat-card">
        <div class="fact-stat-label">👥 行业横向排位透视 (Peer Group Distribution)</div>
        <div style="margin-top:12px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <span style="font-size:13px; font-weight:700; color:#f1f5f9;">同业排位位次</span>
            <span style="font-size:13px; color:#38bdf8; font-weight:700;">
              ${mult.peer_rank != null && mult.peer_total ? `第 ${mult.peer_rank} / ${mult.peer_total} 名` : "未披露排位样本"}
            </span>
          </div>
          <div style="font-size:14px; font-weight:700; color:#fbbf24; margin-bottom:8px;">
            ${escapeHtml(mult.rank_tier || "同业排位数据分析中")}
          </div>
          <div style="font-size:12px; color:#cbd5e1; line-height:1.6; background:rgba(0,0,0,0.25); padding:10px 12px; border-radius:6px;">
            ${escapeHtml(mult.rank_desc || "长桥单期行业对比样本未披露完整排位明细。")}
          </div>
        </div>
      </div>

      <!-- Card 2: 核心估值乘数快照 -->
      <div class="fact-stat-card">
        <div class="fact-stat-label">📊 核心估值倍数矩阵 (Verified Multiples Matrix)</div>
        <div class="multiples-metric-grid" style="grid-template-columns: 1fr 1fr; gap:10px; margin-top:10px;">
          <div class="multi-metric-item">
            <div class="multi-metric-title">市盈率 P/E (TTM/静)</div>
            <div class="multi-metric-value">${mult.pe_raw != null ? `${Number(mult.pe_raw).toFixed(1)}x` : "--"}</div>
            <div class="multi-metric-sub">长桥官方已公布实数</div>
          </div>
          <div class="multi-metric-item">
            <div class="multi-metric-title">市销率 P/S</div>
            <div class="multi-metric-value">${mult.ps_raw != null ? `${Number(mult.ps_raw).toFixed(1)}x` : "--"}</div>
            <div class="multi-metric-sub">长桥官方已公布实数</div>
          </div>
          <div class="multi-metric-item">
            <div class="multi-metric-title">市净率 P/B</div>
            <div class="multi-metric-value">${mult.pb_raw != null ? `${Number(mult.pb_raw).toFixed(1)}x` : "--"}</div>
            <div class="multi-metric-sub">长桥官方已公布实数</div>
          </div>
          <div class="multi-metric-item">
            <div class="multi-metric-title">股息收益率 (Dividend)</div>
            <div class="multi-metric-value" style="color:${mult.dividend_yield != null ? '#34d399' : '#94a3b8'};">${mult.dividend_yield != null ? `${Number(mult.dividend_yield).toFixed(2)}%` : "--"}</div>
            <div class="multi-metric-sub">已核实派息回报</div>
          </div>
        </div>
      </div>
    </div>
  `;
}

/**
 * Module 4: Interactive Technical Compass & Volume-Price Dynamics
 */
function renderTechnicalCompass(container, data) {
  const verdict = data.plain_verdict || "技术面处于观察期。";
  const items = data.compass_items || [];
  const resonance = data.trend_resonance || {};
  const vAction = data.volume_action || {};
  const ladder = data.price_ladder || {};
  const checklist = data.tactical_checklist || [];

  // Resonance score styling
  const resScore = resonance.score != null ? resonance.score : "--";
  let scoreClass = "neutral";
  if (resScore >= 70) scoreClass = "bull";
  else if (resScore < 40) scoreClass = "bear";

  let resBadgeClass = "pullback";
  if (resonance.badge === "STRONG_BULL") resBadgeClass = "strong-bull";
  else if (resonance.badge === "REBOUND") resBadgeClass = "rebound";
  else if (resonance.badge === "BEARISH") resBadgeClass = "bearish";

  const cycles = resonance.cycles || {};
  const cShort = cycles.short_20d || { name: "短期动量 (20日)", status: "待定", ok: false };
  const cMid = cycles.mid_60d || { name: "中期波段 (60日)", status: "待定", ok: false };
  const cLong = cycles.long_200d || { name: "长期牛熊 (200日)", status: "待定", ok: false };

  // Price Ladder data
  const currPrice = ladder.current_price ? Number(ladder.current_price).toFixed(2) : "--";
  const r2 = ladder.r2_major || {};
  const r1 = ladder.r1_near || {};
  const s1 = ladder.s1_near || {};
  const s2 = ladder.s2_defense || {};
  const klines = data.klines || [];
  const stopPrice = data.trailing_stop_2atr || (s2 && s2.price) || null;

  container.innerHTML = `
    <div class="highlight-box">
      <strong>【买方技术面与量价综合体检】</strong><br/>
      ${escapeHtml(verdict)}
    </div>

    <!-- 0. Daily K-Line Chart & Moving Averages (Rule P1 8) -->
    <div class="kline-chart-container">
      <div class="kline-chart-header">
        <div class="kline-legend">
          <span class="legend-item"><span class="legend-color close-line"></span>收盘价</span>
          <span class="legend-item"><span class="legend-color ma20-line"></span>MA20 (月线)</span>
          <span class="legend-item"><span class="legend-color ma60-line"></span>MA60 (季线)</span>
          <span class="legend-item"><span class="legend-color atr-stop-line"></span>2×ATR 止损线 (${stopPrice ? '$' + Number(stopPrice).toFixed(2) : '--'})</span>
        </div>
        <span class="kline-chart-badge">${klines.length ? `收盘日 K · 共 ${klines.length} 根` : 'K线加载中'}</span>
      </div>
      <div class="kline-canvas-wrapper" id="klineCanvasWrapper">
        <canvas id="dossierKLineCanvas" height="260"></canvas>
        <div id="klineTooltip" class="kline-tooltip" style="display: none;"></div>
      </div>
    </div>

    <!-- 1. Trend Resonance & Volume-Price Dynamics Panel -->
    <div class="tech-dashboard-row">
      <!-- Left: Trend Resonance -->
      <div class="resonance-card">
        <div>
          <div class="resonance-head">
            <div>
              <div style="font-size:12px; color:#94a3b8; margin-bottom:4px; font-weight:600;">趋势三周期共振仪 (Trend Resonance)</div>
              <div class="resonance-score-box">
                <span class="resonance-score-num ${scoreClass}">${resScore}</span>
                <span class="resonance-score-max">/ 100</span>
              </div>
            </div>
            <span class="resonance-badge ${resBadgeClass}">
              ${escapeHtml(resonance.status || "均线交织")}
            </span>
          </div>
          <div class="resonance-alignment-title">${escapeHtml(resonance.alignment || "")}</div>
          <div class="resonance-desc">${escapeHtml(resonance.desc || "")}</div>
        </div>
        <div class="cycle-pills-row">
          <div class="cycle-pill-item">
            <div class="cycle-pill-name">${escapeHtml(cShort.name)}</div>
            <div class="cycle-pill-status ${cShort.ok ? 'pass' : 'fail'}">${escapeHtml(cShort.status)}</div>
          </div>
          <div class="cycle-pill-item">
            <div class="cycle-pill-name">${escapeHtml(cMid.name)}</div>
            <div class="cycle-pill-status ${cMid.ok ? 'pass' : 'fail'}">${escapeHtml(cMid.status)}</div>
          </div>
          <div class="cycle-pill-item">
            <div class="cycle-pill-name">${escapeHtml(cLong.name)}</div>
            <div class="cycle-pill-status ${cLong.ok ? 'pass' : 'fail'}">${escapeHtml(cLong.status)}</div>
          </div>
        </div>
      </div>

      <!-- Right: Volume-Price Action Diagnostic -->
      <div class="volume-action-card">
        <div>
          <div class="volume-action-head">
            <div style="font-size:12px; color:#94a3b8; font-weight:600;">主力筹码与量价行为诊断</div>
            <span class="badge" style="background:rgba(96, 165, 250, 0.15); color:#93c5fd; border:1px solid rgba(96, 165, 250, 0.3);">
              ${escapeHtml(vAction.badge || "NEUTRAL")}
            </span>
          </div>
          <div class="volume-ratio-banner">
            <span class="volume-ratio-val">${vAction.volume_ratio != null ? `${Number(vAction.volume_ratio).toFixed(2)}x` : "--"}</span>
            <span class="volume-ratio-label">20日成交量比 (Volume Ratio)</span>
          </div>
          <div style="font-size:14px; font-weight:700; color:#f1f5f9; margin-bottom:10px;">
            ${escapeHtml(vAction.category || "常态换手整理")}
          </div>
        </div>
        <div class="volume-verdict-box">
          💡 ${escapeHtml(vAction.verdict || "成交量与价格维持在历史常态区间。")}
        </div>
      </div>
    </div>

    <!-- 2. Support & Resistance Ladder -->
    <div class="price-ladder-container">
      <div class="ladder-header">
        <div class="ladder-header-title">
          <span>🪜 买方量价关键阶梯 (Support & Resistance Ladder)</span>
        </div>
        <div style="font-size:12px; color:#94a3b8;">
          实战挂单与止损风控标尺 · 顺势低吸与阻力止盈
        </div>
      </div>

      <div class="ladder-steps-list">
        <!-- R2 -->
        <div class="ladder-step-row r2">
          <div class="ladder-step-name">${escapeHtml(r2.name || "强阻力 R2 (波段高点)")}</div>
          <div class="ladder-step-price">$${r2.price ? Number(r2.price).toFixed(2) : "--"}</div>
          <div class="ladder-step-diff pos">${r2.diff_pct != null ? '+' + Number(r2.diff_pct).toFixed(1) + '%' : '--'}</div>
          <div class="ladder-step-desc">${escapeHtml(r2.desc || "")}</div>
        </div>

        <!-- R1 -->
        <div class="ladder-step-row r1">
          <div class="ladder-step-name">${escapeHtml(r1.name || "第一阻力 R1 (布林/均线反压)")}</div>
          <div class="ladder-step-price">$${r1.price ? Number(r1.price).toFixed(2) : "--"}</div>
          <div class="ladder-step-diff pos">${r1.diff_pct != null ? '+' + Number(r1.diff_pct).toFixed(1) + '%' : '--'}</div>
          <div class="ladder-step-desc">${escapeHtml(r1.desc || "")}</div>
        </div>

        <!-- Current Price Anchor -->
        <div class="ladder-step-row current">
          <div class="ladder-step-name">🎯 当前最新收盘价 (Current Price)</div>
          <div class="ladder-step-price">$${currPrice}</div>
          <div class="ladder-step-diff curr">现价锚点</div>
          <div class="ladder-step-desc">实时量价博弈基准线，观察与下方支撑的风险报酬比</div>
        </div>

        <!-- S1 -->
        <div class="ladder-step-row s1">
          <div class="ladder-step-name">${escapeHtml(s1.name || "第一支撑 S1 (核心均线)")}</div>
          <div class="ladder-step-price">$${s1.price ? Number(s1.price).toFixed(2) : "--"}</div>
          <div class="ladder-step-diff neg">${s1.diff_pct != null ? Number(s1.diff_pct).toFixed(1) + '%' : '--'}</div>
          <div class="ladder-step-desc">${escapeHtml(s1.desc || "")}</div>
        </div>

        <!-- S2 -->
        <div class="ladder-step-row s2">
          <div class="ladder-step-name">${escapeHtml(s2.name || "生命防守 S2 (2xATR 止损线)")}</div>
          <div class="ladder-step-price">$${s2.price ? Number(s2.price).toFixed(2) : "--"}</div>
          <div class="ladder-step-diff neg">${s2.diff_pct != null ? Number(s2.diff_pct).toFixed(1) + '%' : '--'}</div>
          <div class="ladder-step-desc">${escapeHtml(s2.desc || "")}</div>
        </div>
      </div>
    </div>

    <!-- 3. Tactical Checklist (Traffic Lights) -->
    <div style="margin-bottom:8px;">
      <h4 class="section-headline" style="margin:0 0 10px 0;">🚦 买方战术准入信号灯 (Buy-Side Tactical Checklist)</h4>
    </div>
    <div class="tactical-checklist-grid">
      ${checklist.map(item => `
        <div class="tactical-card">
          <div class="tactical-card-top">
            <span class="tactical-card-title">${escapeHtml(item.name)}</span>
            <span class="tactical-card-light ${item.pass ? 'pass' : 'alert'}"></span>
          </div>
          <div class="tactical-card-status ${item.pass ? 'pass' : 'alert'}">
            ${escapeHtml(item.status_text)}
          </div>
          <div class="tactical-card-rule">
            ${escapeHtml(item.rule)}
          </div>
        </div>
      `).join("")}
    </div>

    <!-- 4. Technical Compass 8 Cards Grid -->
    <div style="display:flex; justify-content:space-between; align-items:center; margin:20px 0 12px 0;">
      <h4 class="section-headline" style="margin:0;">🧭 8 维技术指标罗盘 (悬停卡片查看深度教学与好坏标准)</h4>
      <span style="font-size:12px; color:#93c5fd;">💡 鼠标悬停任意卡片可唤起通俗大白话浮层</span>
    </div>

    <div class="technical-compass-grid" id="techCompassGrid">
      ${items.map(item => `
        <div class="indicator-interactive-card" data-indicator-id="${item.id}">
          <div class="indicator-card-head">
            <span class="indicator-name">
              ${escapeHtml(item.name)}
              <span class="hover-tip-icon">ℹ️</span>
            </span>
            <span class="indicator-badge-pill ${item.status || 'neutral'}">
              ${escapeHtml(item.badge)}
            </span>
          </div>
          <div class="indicator-val-huge">${escapeHtml(item.value_display)}</div>
          <div class="indicator-mini-diag">${escapeHtml(item.current_diagnosis)}</div>
        </div>
      `).join("")}
    </div>
  `;

  // Attach hover events for interactive tooltip
  bindTooltipEvents(items);

  // Render Daily K-Line Chart with MA20, MA60, and 2xATR Stop (Rule P1 8)
  if (klines && klines.length > 0) {
    setTimeout(() => {
      drawDossierKLineChart("dossierKLineCanvas", klines, stopPrice);
    }, 40);
  }
}

/**
 * Draw 260-Day K-Line Chart with MA20, MA60, and 2xATR Stop on Canvas (Rule P1 8)
 */
function drawDossierKLineChart(canvasId, klines, stopPrice) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const wrapper = canvas.parentElement;
  const tooltip = document.getElementById("klineTooltip");
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const width = wrapper ? wrapper.clientWidth || 800 : 800;
  const height = 260;
  const dpr = window.devicePixelRatio || 1;

  canvas.width = width * dpr;
  canvas.height = height * dpr;
  canvas.style.width = width + "px";
  canvas.style.height = height + "px";
  ctx.scale(dpr, dpr);

  const n = klines.length;
  if (n === 0) return;

  // Calculate MA20 and MA60
  const ma20 = [];
  const ma60 = [];
  for (let i = 0; i < n; i++) {
    const c = Number(klines[i].close);
    if (i >= 19) {
      let sum20 = 0;
      for (let j = i - 19; j <= i; j++) sum20 += Number(klines[j].close);
      ma20.push(sum20 / 20);
    } else {
      ma20.push(null);
    }
    if (i >= 59) {
      let sum60 = 0;
      for (let j = i - 59; j <= i; j++) sum60 += Number(klines[j].close);
      ma60.push(sum60 / 60);
    } else {
      ma60.push(null);
    }
  }

  // Find min and max price across close, high, low, MAs, and stopPrice
  let minP = Infinity;
  let maxP = -Infinity;
  for (let i = 0; i < n; i++) {
    const k = klines[i];
    const c = Number(k.close);
    const h = k.high != null ? Number(k.high) : c;
    const l = k.low != null ? Number(k.low) : c;
    if (h > maxP) maxP = h;
    if (l < minP) minP = l;
    if (ma20[i] != null) {
      if (ma20[i] > maxP) maxP = ma20[i];
      if (ma20[i] < minP) minP = ma20[i];
    }
    if (ma60[i] != null) {
      if (ma60[i] > maxP) maxP = ma60[i];
      if (ma60[i] < minP) minP = ma60[i];
    }
  }
  if (stopPrice != null && !isNaN(stopPrice) && stopPrice > 0) {
    if (stopPrice < minP) minP = Number(stopPrice);
    if (stopPrice > maxP) maxP = Number(stopPrice);
  }

  const padding = (maxP - minP) * 0.08 || 5;
  minP -= padding;
  maxP += padding;

  const padLeft = 12;
  const padRight = 75;
  const padTop = 15;
  const padBottom = 26;
  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;

  function getX(i) {
    return padLeft + (i / (n - 1 || 1)) * plotW;
  }
  function getY(p) {
    return padTop + ((maxP - p) / (maxP - minP || 1)) * plotH;
  }

  // Clear canvas
  ctx.clearRect(0, 0, width, height);

  // Draw background grid lines (4 horizontal price lines)
  ctx.strokeStyle = "rgba(148, 163, 184, 0.12)";
  ctx.lineWidth = 1;
  ctx.fillStyle = "#94a3b8";
  ctx.font = "10px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
  ctx.textAlign = "left";

  const gridSteps = 4;
  for (let g = 0; g <= gridSteps; g++) {
    const p = minP + (g / gridSteps) * (maxP - minP);
    const y = getY(p);
    ctx.beginPath();
    ctx.moveTo(padLeft, y);
    ctx.lineTo(width - padRight + 6, y);
    ctx.stroke();
    ctx.fillText(`$${p.toFixed(2)}`, width - padRight + 10, y + 3);
  }

  // Draw date labels at bottom (start, middle, end)
  ctx.fillStyle = "#64748b";
  ctx.textAlign = "left";
  const startDateStr = klines[0].timestamp || klines[0].time || klines[0].date || "";
  const endDateStr = klines[n - 1].timestamp || klines[n - 1].time || klines[n - 1].date || "";
  const midIdx = Math.floor(n / 2);
  const midDateStr = klines[midIdx].timestamp || klines[midIdx].time || klines[midIdx].date || "";
  ctx.fillText(String(startDateStr).slice(0, 10), padLeft, height - 8);
  ctx.textAlign = "center";
  ctx.fillText(String(midDateStr).slice(0, 10), getX(midIdx), height - 8);
  ctx.textAlign = "right";
  ctx.fillText(String(endDateStr).slice(0, 10), width - padRight, height - 8);

  // Draw 2xATR Stop horizontal dashed line
  if (stopPrice != null && !isNaN(stopPrice) && stopPrice > 0) {
    const stopY = getY(Number(stopPrice));
    ctx.save();
    ctx.strokeStyle = "#ef4444";
    ctx.lineWidth = 1.5;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(padLeft, stopY);
    ctx.lineTo(width - padRight, stopY);
    ctx.stroke();
    ctx.restore();

    ctx.fillStyle = "#ef4444";
    ctx.font = "10px -apple-system, sans-serif";
    ctx.textAlign = "left";
    ctx.fillText(`止损 $${Number(stopPrice).toFixed(2)}`, width - padRight + 8, stopY + 3);
  }

  // Draw Close price gradient fill under curve
  ctx.save();
  const grad = ctx.createLinearGradient(0, padTop, 0, height - padBottom);
  grad.addColorStop(0, "rgba(56, 189, 248, 0.22)");
  grad.addColorStop(1, "rgba(56, 189, 248, 0.0)");
  ctx.fillStyle = grad;
  ctx.beginPath();
  ctx.moveTo(getX(0), getY(Number(klines[0].close)));
  for (let i = 1; i < n; i++) {
    ctx.lineTo(getX(i), getY(Number(klines[i].close)));
  }
  ctx.lineTo(getX(n - 1), height - padBottom);
  ctx.lineTo(getX(0), height - padBottom);
  ctx.closePath();
  ctx.fill();
  ctx.restore();

  // Draw Close Line (Sky Blue)
  ctx.strokeStyle = "#38bdf8";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(getX(0), getY(Number(klines[0].close)));
  for (let i = 1; i < n; i++) {
    ctx.lineTo(getX(i), getY(Number(klines[i].close)));
  }
  ctx.stroke();

  // Draw MA20 Line (Gold/Amber)
  let ma20Started = false;
  ctx.strokeStyle = "#fbbf24";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  for (let i = 0; i < n; i++) {
    if (ma20[i] != null) {
      const x = getX(i);
      const y = getY(ma20[i]);
      if (!ma20Started) {
        ctx.moveTo(x, y);
        ma20Started = true;
      } else {
        ctx.lineTo(x, y);
      }
    }
  }
  ctx.stroke();

  // Draw MA60 Line (Pink/Purple)
  let ma60Started = false;
  ctx.strokeStyle = "#ec4899";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  for (let i = 0; i < n; i++) {
    if (ma60[i] != null) {
      const x = getX(i);
      const y = getY(ma60[i]);
      if (!ma60Started) {
        ctx.moveTo(x, y);
        ma60Started = true;
      } else {
        ctx.lineTo(x, y);
      }
    }
  }
  ctx.stroke();

  // Mouse interactivity on wrapper
  if (wrapper && tooltip) {
    wrapper.onmousemove = function (e) {
      const rect = canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      if (mouseX < padLeft || mouseX > width - padRight) {
        tooltip.style.display = "none";
        return;
      }
      const ratio = (mouseX - padLeft) / plotW;
      const idx = Math.min(n - 1, Math.max(0, Math.round(ratio * (n - 1))));
      const k = klines[idx];
      const dateStr = String(k.timestamp || k.time || k.date || "").slice(0, 10);
      const closeVal = Number(k.close).toFixed(2);
      const m20Val = ma20[idx] != null ? `$${ma20[idx].toFixed(2)}` : "--";
      const m60Val = ma60[idx] != null ? `$${ma60[idx].toFixed(2)}` : "--";
      const stopVal = stopPrice ? `$${Number(stopPrice).toFixed(2)}` : "--";

      tooltip.innerHTML = `
        <div style="font-weight:700; color:#38bdf8; margin-bottom:2px;">📅 ${escapeHtml(dateStr)}</div>
        <div>收盘价: <strong style="color:#ffffff;">$${closeVal}</strong></div>
        <div>MA20: <span style="color:#fbbf24;">${m20Val}</span></div>
        <div>MA60: <span style="color:#ec4899;">${m60Val}</span></div>
        <div>2×ATR 止损: <span style="color:#ef4444;">${stopVal}</span></div>
      `;
      tooltip.style.display = "block";
      const tooltipX = Math.min(width - 150, Math.max(10, mouseX - 60));
      tooltip.style.left = tooltipX + "px";
      tooltip.style.top = "20px";
    };

    wrapper.onmouseleave = function () {
      tooltip.style.display = "none";
    };
  }
}

/**
 * Module 5: Capital Allocation & Shareholder Yield
 */
/**
 * Module 5: Capital Allocation & Shareholder Returns (4-Pillar Buy-Side Framework)
 */
function renderCapitalAllocation(container, data) {
  const verdict = data.summary_verdict || "资本配置与股东回报分析就绪。";
  const persona = data.capital_persona || { name: "稳健资本管家", tagline: "平衡再投资与股东回报", badge: "BALANCED" };
  const waterfall = data.cash_waterfall || { items: [] };
  const spread = data.economic_spread || {};
  const dupont = data.dupont_decomposition || {};
  const sy = data.shareholder_yield || {};
  const bf = data.balance_sheet_fortress || {};

  // Spread score styling
  const hasSpread = spread.spread_pct != null;
  const spreadNum = hasSpread ? spread.spread_pct : null;
  let spreadClass = "solid";
  if (hasSpread) {
    if (spreadNum >= 25) spreadClass = "elite";
    else if (spreadNum < 0) spreadClass = "danger";
  }

  // Persona badge class
  let personaClass = "balanced";
  if (persona.badge === "COMPOUNDER") personaClass = "compounder";
  else if (persona.badge === "CASH_COW") personaClass = "cash-cow";

  // Shield badge class
  const shieldIcon = bf.badge === "FORTRESS" ? "🛡️" : (bf.badge === "HEALTHY" ? "✅" : "⚠️");

  const hasWaterfall = Array.isArray(waterfall.items) && waterfall.items.length > 0;

  container.innerHTML = `
    <!-- Top Highlight Box -->
    <div class="highlight-box">
      <strong>【买方财报审计：资产负债健康度、杠杆风险与杜邦回报拆解】</strong><br/>
      ${escapeHtml(verdict)}
    </div>

    <!-- Capital Persona Banner -->
    <div class="capital-persona-banner">
      <div>
        <div class="capital-persona-title">
          <span>🏛️ 资产负债与资本稳健度风格：${escapeHtml(persona.name)}</span>
        </div>
        <div class="capital-persona-tagline">${escapeHtml(persona.tagline)}</div>
      </div>
      <span class="capital-persona-badge ${personaClass}">
        ${escapeHtml(persona.badge || "CAPITAL_STEWARD")}
      </span>
    </div>

    <!-- Pillar 1: Cash Allocation Waterfall -->
    <div class="capital-waterfall-card">
      <div class="waterfall-header">
        <div style="font-size:15px; font-weight:700; color:#f8fafc; display:flex; align-items:center; gap:8px;">
          <span>🌊 自由现金流去向透视 (Cash Allocation Waterfall)</span>
        </div>
        <span style="font-size:12px; color:#94a3b8;">
          营运现金流拆解：再投资 vs 回购 vs 派息 vs 留存
        </span>
      </div>

      ${hasWaterfall ? `
        <!-- Segmented Track -->
        <div class="waterfall-track">
          ${waterfall.items.map(item => `
            <div class="waterfall-segment" style="width: ${item.pct}%; background: ${item.color};" title="${escapeHtml(item.name)}: ${item.pct}%"></div>
          `).join("")}
        </div>

        <!-- Legend Items Grid -->
        <div class="waterfall-legend-grid">
          ${waterfall.items.map(item => `
            <div class="waterfall-legend-item">
              <div class="waterfall-item-head">
                <span class="waterfall-item-name">
                  <span class="waterfall-dot" style="background:${item.color};"></span>
                  ${escapeHtml(item.name)}
                </span>
                <span class="waterfall-item-pct" style="color:${item.color};">${item.pct}%</span>
              </div>
              <div class="waterfall-item-desc">${escapeHtml(item.desc)}</div>
            </div>
          `).join("")}
        </div>
      ` : `
        <div style="padding:14px 16px; background:rgba(255,255,255,0.02); border-radius:6px; border:1px dashed rgba(255,255,255,0.08); font-size:12px; color:#94a3b8; line-height:1.6;">
          <span style="color:#fbbf24; font-weight:600;">⚠️ 自由现金流拆解未取得：</span>长桥单期快照接口未披露完整现金流量表（无经营现金流及资本开支明细）。本终端严格拒绝经验插值反推伪造现金流瀑布图，待多期财报审计数据齐备后呈现。
        </div>
      `}
    </div>

    <!-- Pillar 2: Economic Spread & DuPont Dual Row -->
    <div class="capital-dual-grid">
      <!-- Left: Economic Spread -->
      <div class="capital-box-card">
        <div>
          <div class="capital-box-header">
            <div>
              <div style="font-size:12px; color:#94a3b8; margin-bottom:4px; font-weight:600;">经济商誉利差 (Economic Value Spread)</div>
              <div class="spread-score-huge ${spreadClass}">
                ${hasSpread ? `${spreadNum >= 0 ? "+" : ""}${spreadNum}%` : "--"}
              </div>
            </div>
            <span class="badge" style="background:rgba(52, 211, 153, 0.15); color:#34d399; border:1px solid rgba(52, 211, 153, 0.3);">
              ${escapeHtml(spread.badge || (hasSpread ? "VALUE_CREATOR" : "DATA_PENDING"))}
            </span>
          </div>

          <div style="font-size:14px; font-weight:700; color:#f1f5f9; margin-bottom:8px;">
            ${escapeHtml(spread.tier || "待多期数据核验")}
          </div>

          <!-- Comparative Bars -->
          <div class="spread-bars-container">
            <div class="spread-bar-row">
              <span class="spread-bar-label">资本回报 (ROIC)</span>
              <div class="spread-bar-track">
                <div class="spread-bar-fill" style="width: ${spread.roic_pct != null ? Math.min(100, Math.max(0, spread.roic_pct * 1.1)) : 0}%; background: #34d399;"></div>
              </div>
              <span class="spread-bar-val" style="color:#34d399;">${spread.roic_pct != null ? `${spread.roic_pct}%` : "--"}</span>
            </div>
            <div class="spread-bar-row">
              <span class="spread-bar-label">资本成本 (WACC)</span>
              <div class="spread-bar-track">
                <div class="spread-bar-fill" style="width: ${spread.wacc_pct != null ? Math.min(100, Math.max(0, spread.wacc_pct * 4)) : 0}%; background: #94a3b8;"></div>
              </div>
              <span class="spread-bar-val" style="color:#94a3b8;">${spread.wacc_pct != null ? `${spread.wacc_pct}%` : "--"}</span>
            </div>
          </div>
        </div>

        <div style="font-size:12px; color:#cbd5e1; line-height:1.5; background:rgba(0,0,0,0.2); padding:10px 12px; border-radius:6px;">
          💡 ${escapeHtml(spread.verdict || "ROIC 与 WACC 利差反映企业是否在内生创造超额经济价值。")}
        </div>
      </div>

      <!-- Right: DuPont Decomposition -->
      <div class="capital-box-card">
        <div>
          <div class="capital-box-header">
            <div>
              <div style="font-size:12px; color:#94a3b8; margin-bottom:4px; font-weight:600;">杜邦三因子动力拆解 (DuPont Engine)</div>
              <div style="font-size:18px; font-weight:800; color:#38bdf8;">
                ROE: ${dupont.roe_pct != null ? `${dupont.roe_pct}%` : "--"}
              </div>
            </div>
            <span class="badge" style="background:rgba(56, 189, 248, 0.15); color:#7dd3fc; border:1px solid rgba(56, 189, 248, 0.3);">
              三因子透视
            </span>
          </div>

          <div style="font-size:13px; font-weight:700; color:#f1f5f9; margin-bottom:4px;">
            ${escapeHtml(dupont.core_driver || "综合平衡型")}
          </div>

          <div class="dupont-factors-row">
            <div class="dupont-factor-item">
              <div class="dupont-factor-name">销售净利率</div>
              <div class="dupont-factor-val">${dupont.net_margin_pct != null ? `${dupont.net_margin_pct}%` : "--"}</div>
            </div>
            <div class="dupont-factor-item">
              <div class="dupont-factor-name">资产周转率</div>
              <div class="dupont-factor-val">${dupont.asset_turnover != null ? `${dupont.asset_turnover}x` : "--"}</div>
            </div>
            <div class="dupont-factor-item">
              <div class="dupont-factor-name">权益乘数(杠杆)</div>
              <div class="dupont-factor-val" style="${dupont.equity_multiplier != null && dupont.equity_multiplier < 0 ? 'color:#f87171;' : ''}">${dupont.equity_multiplier != null ? `${dupont.equity_multiplier}x` : "--"}</div>
            </div>
          </div>
        </div>

        <div style="font-size:12px; color:#cbd5e1; line-height:1.5; background:rgba(0,0,0,0.2); padding:10px 12px; border-radius:6px;">
          🔍 ${escapeHtml(dupont.desc || "")}
        </div>
      </div>
    </div>

    <!-- Pillar 3 & 4: Shareholder Yield & Balance Sheet Fortress Dual Row -->
    <div class="capital-dual-grid">
      <!-- Left: Shareholder Yield & Buyback Quality -->
      <div class="capital-box-card">
        <div>
          <div class="capital-stats-card-head">
            <div style="font-size:13px; font-weight:700; color:#cbd5e1;">真实综合股东回报 (Shareholder Yield)</div>
            <span class="badge" style="background:rgba(16, 185, 129, 0.15); color:#34d399; border:1px solid rgba(16, 185, 129, 0.3);">
              ${escapeHtml(sy.buyback_quality || "股东回馈透视")}
            </span>
          </div>

          <div class="yield-number-banner">
            <span class="yield-number-val">${sy.total_yield_pct != null ? `${sy.total_yield_pct}%` : "--"}</span>
            <span style="font-size:12px; color:#94a3b8;">年化综合现金回馈底线</span>
          </div>

          <div class="yield-split-pills">
            <div class="yield-split-pill">
              现金股息率: <strong>${sy.dividend_yield_pct != null ? `${sy.dividend_yield_pct}%` : "-- (未披露)"}</strong>
            </div>
            <div class="yield-split-pill">
              净回购收益率: <strong>${sy.buyback_yield_pct != null ? `${sy.buyback_yield_pct}%` : "-- (未披露)"}</strong>
            </div>
          </div>
        </div>

        <div style="font-size:12px; color:#cbd5e1; line-height:1.5; background:rgba(0,0,0,0.2); padding:10px 12px; border-radius:6px;">
          🏷️ <strong>回购动机诊断:</strong> ${escapeHtml(sy.comment || "长桥单期财务未披露回购明细。")}
        </div>
      </div>

      <!-- Right: Balance Sheet Fortress & Stress Test -->
      <div class="capital-box-card">
        <div>
          <div class="capital-stats-card-head">
            <div style="font-size:13px; font-weight:700; color:#cbd5e1;">资产负债表安全垫与压力测试</div>
            <span class="badge" style="background:rgba(59, 130, 246, 0.15); color:#60a5fa; border:1px solid rgba(59, 130, 246, 0.3);">
              ${escapeHtml(bf.badge || "FORTRESS")}
            </span>
          </div>

          <div class="fortress-shield-banner">
            <span class="fortress-shield-icon">${shieldIcon}</span>
            <div>
              <div class="fortress-grade-title">${escapeHtml(bf.grade || "稳健投资级")}</div>
              <div style="font-size:11px; color:#94a3b8;">在加息与衰退周期具备极高生存抗风险韧性</div>
            </div>
          </div>

          <div class="fortress-ratios-list">
            <div class="fortress-ratio-item">
              <div class="fortress-ratio-label">资产负债率 (Debt/Assets)</div>
              <div class="fortress-ratio-val">${bf.debt_to_assets_pct != null ? `${bf.debt_to_assets_pct}%` : "--"}</div>
            </div>
            <div class="fortress-ratio-item">
              <div class="fortress-ratio-label">利息保障倍数 (Coverage)</div>
              <div class="fortress-ratio-val" style="color:#34d399;">${bf.interest_coverage_x != null ? `${bf.interest_coverage_x}x` : (bf.coverage_display || "-- (未披露)")}</div>
            </div>
          </div>
        </div>

        <div style="font-size:12px; color:#cbd5e1; line-height:1.5; background:rgba(0,0,0,0.2); padding:10px 12px; border-radius:6px;">
          🛡️ <strong>压力测试结论:</strong> ${escapeHtml(bf.stress_test || "长桥财务指标未见短期违约异动。")}
        </div>
      </div>
    </div>
  `;
}

/**
 * Module 6: Institutional Buy-Side Investment Memo
 */
/**
 * Module 6: Institutional Buy-Side Investment Memo & IC Decision Board
 */
function renderAiMemo(container, data) {
  if (data && data.isGenerating) {
    container.innerHTML = `
      <div class="highlight-box" style="border-left-color: #3b82f6;">
        <strong>【买方投审会 (IC) 备忘录正在由双大模型推演中】</strong><br/>
        系统正在调用 Grok CLI 与 Gemini CLI 进行深度多空答辩与终审表决。由于双模型交叉质询，耗时约 15~25 秒，您可继续浏览其他板块，完成将自动更新。
      </div>

      <div class="ai-memo-loading-box">
        <div class="ai-shimmer-progress"></div>
        <div class="ai-loading-steps">
          <div class="ai-step-row active">
            <span class="ai-step-indicator">1</span>
            <span>调度 Grok / Gemini 分别扮演【多头买方分析师】与【空头风控审计员】...</span>
          </div>
          <div class="ai-step-row active">
            <span class="ai-step-indicator">2</span>
            <span>进行 3 轮多空交叉答辩，质询估值安全边际与资本分配...</span>
          </div>
          <div class="ai-step-row active">
            <span class="ai-step-indicator">3</span>
            <span>投资委员会终审裁决，输出建议持有久期与动态硬止损线...</span>
          </div>
        </div>
      </div>
    `;
    return;
  }

  const isPending = !data || data.pending || data.status === "PENDING_REVIEW" || !data.ic_verdict || Object.keys(data.ic_verdict).length === 0;

  if (isPending) {
    const rawMemo = data ? (data.memo || "") : "";
    container.innerHTML = `
      <div class="highlight-box" style="border-left-color: #f59e0b;">
        <strong>【买方投审会 (IC) 备忘录待生成状态提示】</strong><br/>
        长桥行情与核心财务事实已调阅完毕。投审会深度多空辩论与终审决议依赖大模型研判。
      </div>

      <div class="ai-memo-pending-card">
        <div class="memo-icon">🧠</div>
        <h3>买方投资备忘录未生成</h3>
        <p>${escapeHtml(rawMemo || "本系统严格遵循买方实证准则，绝不使用预设静态看多模板冒充真实研判结论。点击下方按钮即可一键调度 Grok 与 Gemini 双模型进行全自动多空答辩与投资评议。")}</p>
        <button type="button" class="btn-generate-memo" id="btnTriggerMemoGen" onclick="triggerAiMemoGeneration()">
          <span>⚡</span>
          <span>一键生成买方投资备忘录 (双模型互审)</span>
        </button>
      </div>
    `;
    return;
  }

  const verdict = data.ic_verdict;
  const matrix = data.bull_bear_matrix || { bull_theses: [], bear_risks: [] };
  const catalysts = data.catalysts_checklist || [];
  const rawMemo = data.memo || "";
  const formattedHtml = parseMarkdownToHtml(rawMemo);

  container.innerHTML = `
    <!-- Top Highlight Box -->
    <div class="highlight-box">
      <strong>【买方对冲基金投审会 (IC) 长线投资决议】</strong><br/>
      ${escapeHtml(verdict.core_rationale || "")}
    </div>

    <!-- 1. IC Decision Banner -->
    <div class="ic-verdict-banner">
      <div class="ic-verdict-head">
        <div>
          <div style="font-size:12px; color:#94a3b8; font-weight:600; margin-bottom:4px;">
            投审会终审决议 (Investment Committee Verdict)
          </div>
          <div style="font-size:18px; font-weight:800; color:#f1f5f9;">
            ${escapeHtml(data.company_name || data.symbol || "")} 资产配置研判
          </div>
        </div>
        <span class="ic-rating-badge ${verdict.badge_class || 'accumulate'}">
          ${escapeHtml(verdict.rating_label || verdict.rating || "OBSERVE")}
        </span>
      </div>

      <!-- 4 Key Allocation Parameters -->
      <div class="ic-meta-grid">
        <div class="ic-meta-card">
          <div class="ic-meta-label">建议持有久期</div>
          <div class="ic-meta-val">${escapeHtml(verdict.time_horizon || "12~36 个月")}</div>
        </div>
        <div class="ic-meta-card">
          <div class="ic-meta-label">目标配置仓位</div>
          <div class="ic-meta-val" style="color:#60a5fa;">${escapeHtml(verdict.target_allocation || "--")}</div>
        </div>
        <div class="ic-meta-card">
          <div class="ic-meta-label">建议建仓价格区间</div>
          <div class="ic-meta-val" style="color:#34d399;">${escapeHtml(verdict.buy_zone || "--")}</div>
        </div>
        <div class="ic-meta-card">
          <div class="ic-meta-label">2xATR 动态硬止损线</div>
          <div class="ic-meta-val" style="color:#f87171;">${escapeHtml(verdict.stop_loss || "--")}</div>
        </div>
      </div>
    </div>

    <!-- 2. Bull vs. Bear Debate Matrix -->
    <div style="margin-bottom:10px;">
      <h4 class="section-headline" style="margin:0 0 12px 0;">⚔️ 多空攻防辩论对决矩阵 (Bull vs. Bear Debate Matrix)</h4>
    </div>
    <div class="bull-bear-matrix-grid">
      <!-- Bull Column -->
      <div class="bull-box">
        <div class="debate-head">
          <span style="font-size:18px;">🟢</span>
          <div>
            <div style="font-size:14px; font-weight:800; color:#34d399;">做多买方确定性论据 (Top 3 Theses)</div>
            <div style="font-size:11px; color:#94a3b8;">驱动股价未来 1~3 年复合上行的核心抓手</div>
          </div>
        </div>
        ${(matrix.bull_theses || []).length > 0 ? (matrix.bull_theses || []).map((b, i) => `
          <div class="debate-card">
            <div class="debate-card-title">
              <span style="color:#f1f5f9;">${i + 1}. ${escapeHtml(b.title)}</span>
              <span class="badge" style="background:rgba(52, 211, 153, 0.15); color:#34d399; font-size:10px;">${escapeHtml(b.pillar || "确信")}</span>
            </div>
            <div class="debate-card-desc">${escapeHtml(b.evidence)}</div>
          </div>
        `).join("") : `<div style="font-size:12px; color:#94a3b8; padding:8px 0;">暂无论据</div>`}
      </div>

      <!-- Bear Column -->
      <div class="bear-box">
        <div class="debate-head">
          <span style="font-size:18px;">🔴</span>
          <div>
            <div style="font-size:14px; font-weight:800; color:#f87171;">做空证伪点与一票否决红线 (Kill Switches)</div>
            <div style="font-size:11px; color:#94a3b8;">触发即证明逻辑破绽，必须无条件离场减仓</div>
          </div>
        </div>
        ${(matrix.bear_risks || []).length > 0 ? (matrix.bear_risks || []).map((r, i) => `
          <div class="debate-card">
            <div class="debate-card-title">
              <span style="color:#f1f5f9;">${i + 1}. ${escapeHtml(r.title)}</span>
              <span class="badge" style="background:rgba(239, 68, 68, 0.15); color:#f87171; font-size:10px;">${escapeHtml(r.threshold || "红线")}</span>
            </div>
            <div class="debate-card-desc">${escapeHtml(r.kill_switch)}</div>
          </div>
        `).join("") : `<div style="font-size:12px; color:#94a3b8; padding:8px 0;">暂无红线</div>`}
      </div>
    </div>

    <!-- 3. Key Catalysts Checklist -->
    ${catalysts.length > 0 ? `
      <div class="catalysts-card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; padding-bottom:10px; border-bottom:1px solid rgba(255,255,255,0.06);">
          <div style="font-size:14px; font-weight:800; color:#f8fafc; display:flex; align-items:center; gap:8px;">
            <span>📅 未来 12 个月关键跟踪催化剂与里程碑 (Upcoming Milestones)</span>
          </div>
          <span style="font-size:12px; color:#94a3b8;">投后持续性跟踪验证清单</span>
        </div>

        <div>
          ${catalysts.map(cat => `
            <div class="catalyst-item-row">
              <span class="catalyst-window-pill">${escapeHtml(cat.window)}</span>
              <div>
                <div style="font-size:13px; font-weight:700; color:#e2e8f0; margin-bottom:4px;">
                  ${escapeHtml(cat.event)}
                </div>
                <div style="font-size:12px; color:#94a3b8; line-height:1.4;">
                  ${escapeHtml(cat.focus)}
                </div>
              </div>
            </div>
          `).join("")}
        </div>
      </div>
    ` : ""}

    <!-- 4. Full Markdown Institutional Memo -->
    ${rawMemo ? `
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
        <h4 class="section-headline" style="margin:0;">📝 买方长线投资备忘录全文 (Detailed Memo)</h4>
        <span style="font-size:12px; color:#93c5fd;">
          模型引擎: ${escapeHtml(data.model || "长桥事实与大模型交叉审议")}
        </span>
      </div>

      <div class="memo-markdown-container">
        ${formattedHtml}
      </div>
    ` : ""}
  `;
}

// ==============================================================================
// Tooltip & Micro-Interactions
// ==============================================================================

function bindTooltipEvents(items) {
  const grid = document.getElementById("techCompassGrid");
  if (!grid) return;

  const tooltip = elements.smartTooltip;
  const itemMap = new Map(items.map(it => [it.id, it]));

  const cards = grid.querySelectorAll(".indicator-interactive-card");
  cards.forEach(card => {
    card.addEventListener("mouseenter", (e) => {
      const id = card.dataset.indicatorId;
      const it = itemMap.get(id);
      if (!it) return;

      elements.ttName.textContent = it.name;
      elements.ttBadge.textContent = it.badge;
      elements.ttPlain.textContent = it.plain_english;
      elements.ttRule.textContent = it.good_bad_rule;
      elements.ttDiagnosis.textContent = it.current_diagnosis;
      elements.ttScenario.textContent = it.scenario;

      positionTooltip(card);
      tooltip.style.display = "block";
    });

    card.addEventListener("mouseleave", () => {
      tooltip.style.display = "none";
    });
  });
}

function positionTooltip(targetEl) {
  const tt = elements.smartTooltip;
  const rect = targetEl.getBoundingClientRect();
  const ttWidth = 360;
  const ttHeight = 320;

  let left = rect.right + 12;
  let top = rect.top - 20;

  // Prevent right overflow
  if (left + ttWidth > window.innerWidth) {
    left = rect.left - ttWidth - 12;
  }
  // Prevent bottom overflow
  if (top + ttHeight > window.innerHeight) {
    top = window.innerHeight - ttHeight - 20;
  }
  if (top < 10) top = 10;

  tt.style.left = `${left}px`;
  tt.style.top = `${top}px`;
}

// ==============================================================================
// History Shelf Management
// ==============================================================================

async function loadHistoryCount() {
  try {
    const res = await fetch("/api/dossiers/history");
    const data = await res.json();
    if (data.ok && Array.isArray(data.history)) {
      if (elements.historyCountBadge) elements.historyCountBadge.textContent = data.history.length;
      if (elements.globalHistoryBadge) elements.globalHistoryBadge.textContent = data.history.length;
      updateQuickPillsCachedStatus();
    }
  } catch (err) {
    console.error("Load history count error:", err);
  }
}

function updateQuickPillsCachedStatus() {
  const pills = elements.quickPills ? elements.quickPills.querySelectorAll(".pill-btn") : [];
  const historySet = new Set((state.historyList || []).map(h => (h.symbol || "").toUpperCase()));

  pills.forEach(pill => {
    const sym = (pill.dataset.symbol || "").toUpperCase();
    const isCached = historySet.has(sym);
    pill.classList.toggle("cached", isCached);

    let tag = pill.querySelector(".pill-cached-tag");
    if (isCached && !tag) {
      tag = document.createElement("span");
      tag.className = "pill-cached-tag";
      tag.textContent = "⚡已检索";
      pill.appendChild(tag);
    } else if (!isCached && tag) {
      tag.remove();
    }
  });
}

async function openHistoryModal() {
  elements.historyModal.style.display = "flex";
  await refreshHistoryTable();
}

function closeHistoryModal() {
  elements.historyModal.style.display = "none";
}

async function refreshHistoryTable() {
  const tbody = elements.historyTableBody;
  tbody.innerHTML = `<tr><td colspan="7" class="text-muted" style="text-align:center; padding:20px;">加载中...</td></tr>`;

  try {
    const res = await fetch("/api/dossiers/history");
    const data = await res.json();
    if (!data.ok || !Array.isArray(data.history)) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-muted" style="text-align:center;">暂无记录</td></tr>`;
      return;
    }

    state.historyList = data.history;
    elements.historyCountBadge.textContent = data.history.length;

    if (!data.history.length) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-muted" style="text-align:center; padding:30px;">暂无历史归档标的，可在首页搜索并建立档案。</td></tr>`;
      return;
    }

    tbody.innerHTML = data.history.map(item => {
      const chg = item.change_pct != null ? Number(item.change_pct).toFixed(2) : "0.00";
      const p = item.price != null ? `$${Number(item.price).toFixed(2)}` : "--";
      const updatedStr = formatTimeAgo(item.updated_at);

      return `
        <tr class="history-row">
          <td><strong>${escapeHtml(item.symbol)}</strong></td>
          <td>${escapeHtml(item.name || item.symbol)}</td>
          <td><b>${p}</b></td>
          <td>
            <span class="stock-change-pill ${chg > 0 ? 'positive' : chg < 0 ? 'negative' : 'neutral'}" style="font-size:11px;">
              ${chg >= 0 ? "+" : ""}${chg}%
            </span>
          </td>
          <td>
            <span style="font-size:12px; font-weight:600;">
              ${escapeHtml(item.valuation_status || "分析中")}
            </span>
          </td>
          <td style="color:var(--text-dim); font-size:12px;">${updatedStr}</td>
          <td>
            <button type="button" class="btn-action-view" onclick="onViewHistorySymbol('${item.symbol}')">进入详情</button>
            <button type="button" class="btn-action-delete" title="删除归档" onclick="onDeleteHistorySymbol('${item.symbol}', event)">🗑️</button>
          </td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-muted" style="color:var(--rose);">加载失败: ${err.message}</td></tr>`;
  }
}

// Global actions for inline HTML handlers
window.onViewHistorySymbol = function(symbol) {
  closeHistoryModal();
  loadDossier(symbol);
};

window.onDeleteHistorySymbol = async function(symbol, evt) {
  if (evt) evt.stopPropagation();
  if (!confirm(`确认从档案书架删除【${symbol}】吗？`)) return;

  try {
    const res = await fetch("/api/dossiers/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol })
    });
    const d = await res.json();
    if (d.ok) {
      await refreshHistoryTable();
      loadHistoryCount();
    }
  } catch (err) {
    alert("删除失败: " + err.message);
  }
};

// ==============================================================================
// Utility Helpers
// ==============================================================================

async function triggerAiMemoGeneration() {
  if (!state.currentSymbol) return;
  const sym = state.currentSymbol;

  if (!state.currentDossier) state.currentDossier = {};
  if (!state.currentDossier.modules) state.currentDossier.modules = {};
  state.currentDossier.modules.ai_memo = {
    updated_at: new Date().toISOString(),
    data: { isGenerating: true }
  };
  renderTopicStage();

  try {
    const resp = await fetch("/api/dossier/refresh-module", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol: sym, module: "ai_memo" })
    });
    const res = await resp.json();
    if (!res.ok) throw new Error(res.error || "生成备忘录失败");

    if (state.currentSymbol === sym && state.currentDossier && state.currentDossier.modules) {
      state.currentDossier.modules.ai_memo = res.module_entry;
      renderTopicStage();
    }
  } catch (err) {
    if (state.currentSymbol === sym && state.currentDossier && state.currentDossier.modules) {
      state.currentDossier.modules.ai_memo = {
        updated_at: new Date().toISOString(),
        data: { memo: `生成异常：${err.message}` }
      };
      renderTopicStage();
    }
  }
}

function formatTimeAgo(isoStr) {
  if (!isoStr) return "刚刚";
  try {
    const date = new Date(isoStr);
    const now = new Date();
    const diffSec = Math.floor((now - date) / 1000);

    if (diffSec < 60) return "刚刚";
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)} 分钟前`;
    if (diffSec < 86400) return `${Math.floor(diffSec / 3600)} 小时前`;
    const days = Math.floor(diffSec / 86400);
    if (days === 1) return "昨天";
    if (days < 30) return `${days} 天前`;
    return date.toISOString().split("T")[0];
  } catch {
    return isoStr;
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function parseMarkdownToHtml(md) {
  if (!md) return "";
  let html = md;
  // Headers
  html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
  html = html.replace(/^## (.*$)/gim, '<h3>$1</h3>');
  // Bold
  html = html.replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>');
  // Lists
  html = html.replace(/^\- (.*$)/gim, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>)/gim, '<ul>$1</ul>');
  // Clean double ul tags
  html = html.replace(/<\/ul>\s*<ul>/gim, '');
  // Linebreaks
  html = html.replace(/\n\n/gim, '<br/>');
  return html;
}

// ==============================================================================
// Global Workbench Multi-Tab Navigation & Cross-Linking
// ==============================================================================

function initGlobalNavigation() {
  const tabs = document.querySelectorAll(".global-nav-tab");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      const targetView = tab.getAttribute("data-view");
      if (targetView) {
        switchMainTab(targetView);
      }
    });
  });

  if (elements.btnGlobalHistory) {
    elements.btnGlobalHistory.addEventListener("click", openHistoryModal);
  }
}

function switchMainTab(targetSectionId) {
  state.activeMainTab = targetSectionId;

  // Toggle tab buttons
  document.querySelectorAll(".global-nav-tab").forEach(tab => {
    tab.classList.toggle("active", tab.getAttribute("data-view") === targetSectionId);
  });

  // Toggle sections
  document.querySelectorAll(".workbench-section").forEach(sec => {
    const isTarget = sec.id === targetSectionId;
    sec.style.display = isTarget ? "block" : "none";
    if (isTarget) sec.classList.add("active");
    else sec.classList.remove("active");
  });

  // Hash update & tab data load
  if (targetSectionId === "screenerSection") {
    if (window.location.hash !== "#/screener") history.pushState(null, "", "#/screener");
    loadScreenerTab();
  } else if (targetSectionId === "compareSection") {
    if (window.location.hash !== "#/compare") history.pushState(null, "", "#/compare");
    loadCompareTab();
  } else if (targetSectionId === "backtestSection") {
    if (window.location.hash !== "#/backtest") history.pushState(null, "", "#/backtest");
    loadBacktestTab();
  } else if (targetSectionId === "portfolioSection") {
    if (window.location.hash !== "#/portfolio") history.pushState(null, "", "#/portfolio");
    loadPortfolioTab();
  } else if (targetSectionId === "dossierSection") {
    if (state.currentSymbol) {
      if (window.location.hash !== `#/dossier/${state.currentSymbol}`) {
        history.pushState(null, "", `#/dossier/${state.currentSymbol}`);
      }
      showDossierView();
    } else {
      if (window.location.hash) history.pushState(null, "", window.location.pathname);
      showHomeView();
    }
  }
}

function jumpToDossier(symbol) {
  if (!symbol) return;
  switchMainTab("dossierSection");
  loadDossier(symbol);
}

function appendCompareSymbol(symbol) {
  if (!symbol) return;
  switchMainTab("compareSection");
  const input = document.getElementById("compareSymbolsInput");
  if (input) {
    let current = input.value.split(",").map(s => s.trim().toUpperCase()).filter(Boolean);
    const clean = symbol.trim().toUpperCase();
    if (!current.includes(clean)) {
      current.push(clean);
      if (current.length > 5) current = current.slice(-5);
      input.value = current.join(", ");
    }
    runCompare();
  }
}

// ==============================================================================
// Screener Tab Implementation
// ==============================================================================

function initScreenerListeners() {
  const btnRefresh = document.getElementById("btnRefreshDailyPicks");
  if (btnRefresh) {
    btnRefresh.addEventListener("click", () => loadScreenerTab(true));
  }

  const btnToggle = document.getElementById("btnToggleCulled");
  if (btnToggle) {
    btnToggle.addEventListener("click", () => {
      const content = document.getElementById("culledContent");
      if (content) {
        const isHidden = content.style.display === "none";
        content.style.display = isHidden ? "block" : "none";
        const icon = btnToggle.querySelector(".toggle-icon");
        if (icon) icon.textContent = isHidden ? "▲" : "▼";
      }
    });
  }

  const screenerForm = document.getElementById("customScreenerForm");
  if (screenerForm) {
    screenerForm.addEventListener("submit", (e) => {
      e.preventDefault();
      runCustomScreener();
    });
  }

  document.querySelectorAll(".custom-screener-presets .preset-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const symbols = chip.getAttribute("data-symbols");
      const input = document.getElementById("customUniverseInput");
      if (input && symbols) {
        input.value = symbols;
        runCustomScreener();
      }
    });
  });
}

let screenerLoadSeq = 0;

function formatMacroChange(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return { text: "--", cls: "neutral" };
  const sign = n > 0 ? "+" : "";
  return {
    text: `${sign}${n.toFixed(2)}%`,
    cls: n > 0 ? "positive" : n < 0 ? "negative" : "neutral",
  };
}

function vixBandLabel(value) {
  const n = Number(value);
  if (!Number.isFinite(n) || n <= 0) return "--";
  if (n > 28) return "极度恐慌";
  if (n > 22) return "情绪扰动";
  if (n >= 17.5) return "常态波动";
  return "低波动";
}

function scoringWeightChips(weights) {
  const factors = [
    ["quality", "财务质量"],
    ["valuation", "估值合理"],
    ["momentum", "价格动量"],
    ["liquidity", "资金流动性"],
  ];
  const rows = factors.map(([key, label]) => ({
    label,
    value: Number(weights && weights[key]) || 0,
  }));
  const sum = rows.reduce((total, row) => total + row.value, 0);
  if (sum <= 0) {
    return '<span class="weight-chip">权重未返回</span><span class="weight-chip" style="opacity:0.6;border-style:dashed;">催化 0% (不占分)</span>';
  }
  const pieces = rows.map(row => {
    const exact = (row.value / sum) * 100;
    return { label: row.label, floor: Math.floor(exact), frac: exact - Math.floor(exact) };
  });
  let leftover = 100 - pieces.reduce((total, row) => total + row.floor, 0);
  pieces
    .map((row, index) => ({ index, frac: row.frac }))
    .sort((a, b) => b.frac - a.frac)
    .forEach(item => {
      if (leftover > 0) {
        pieces[item.index].floor += 1;
        leftover -= 1;
      }
    });
  const chips = pieces
    .map(row => `<span class="weight-chip">${row.label} ${row.floor}%</span>`)
    .join("");
  return `${chips}<span class="weight-chip" style="opacity:0.6;border-style:dashed;">催化 0% (不占分)</span>`;
}

function renderMacroCockpit(macro) {
  if (!macro) return;
  const regime = macro.regime || {};
  const badge = document.getElementById("screenerRegimeBadge");
  if (badge) {
    const code = String(regime.code || "").toUpperCase();
    const tone = code === "RISK_ON" ? "risk-on" : code === "CAUTION" ? "caution" : code === "PANIC" ? "panic" : "neutral";
    badge.className = `regime-badge ${tone}`;
    badge.textContent = regime.level || "宏观未返回";
  }

  const sourceEl = document.getElementById("macroDataSourceBadge");
  if (sourceEl) {
    const yahoo = macro.data_source_mode === "YAHOO_FINANCE";
    sourceEl.textContent = yahoo ? "Yahoo 日线" : "长桥行情";
  }

  const paintIndex = (valueId, changeId, quote, asPrice) => {
    const valueEl = document.getElementById(valueId);
    const changeEl = document.getElementById(changeId);
    const last = Number(quote && quote.last);
    if (valueEl) {
      valueEl.textContent = Number.isFinite(last) && last > 0 ? (asPrice ? `$${last.toFixed(2)}` : last.toFixed(2)) : "--";
    }
    if (changeEl) {
      const change = formatMacroChange(quote && quote.change_pct);
      changeEl.textContent = change.text;
      changeEl.className = `stat-pill ${change.cls}`;
    }
  };
  paintIndex("spyStatVal", "spyStatChange", macro.spy, true);
  paintIndex("qqqStatVal", "qqqStatChange", macro.qqq, true);

  const vix = macro.vix || {};
  const vixVal = document.getElementById("vixStatVal");
  const vixChange = document.getElementById("vixStatChange");
  const vixLast = Number(vix.last);
  if (vixVal) vixVal.textContent = Number.isFinite(vixLast) && vixLast > 0 ? vixLast.toFixed(2) : "--";
  if (vixChange) {
    const band = vixBandLabel(vixLast);
    const change = formatMacroChange(vix.change_pct);
    vixChange.textContent = band === "--" ? "--" : `${band} ${change.text}`;
    const tone = band === "极度恐慌" || band === "情绪扰动" ? "negative" : band === "低波动" ? "positive" : "neutral";
    vixChange.className = `stat-pill ${tone}`;
  }

  const exposureEl = document.getElementById("screenerMacroExposure");
  if (exposureEl) exposureEl.textContent = regime.suggested_exposure || "--";
  const actionEl = document.getElementById("screenerMacroAction");
  if (actionEl) actionEl.textContent = regime.strategy_style || regime.action_advice || "宏观策略未返回。";
  const weightsEl = document.getElementById("screenerFactorWeights");
  if (weightsEl) {
    const weights = (regime.factor_matrix && regime.factor_matrix.weights) || {};
    weightsEl.innerHTML = scoringWeightChips(weights);
  }
}

async function loadScreenerTab(force = false) {
  const seq = ++screenerLoadSeq;
  // 1. Load Macro Climate
  try {
    const macroRes = await fetch("/api/macro/climate");
    const macroJson = await macroRes.json();
    if (seq !== screenerLoadSeq) return;
    if (macroJson.ok && macroJson.macro) {
      renderMacroCockpit(macroJson.macro);
    }
  } catch (err) {
    console.error("Macro climate load error:", err);
  }
  if (seq !== screenerLoadSeq) return;

  // 2. Load Daily Picks with Progress Polling (Rule P1 7)
  const grid = document.getElementById("dailyPicksGrid");
  const progressBox = document.getElementById("screenerProgressBox");
  const progressText = document.getElementById("screenerProgressText");
  const progressCount = document.getElementById("screenerProgressCount");
  const progressBarFill = document.getElementById("screenerProgressBarFill");
  const exceptionsBox = document.getElementById("screenerExceptionsBox");
  const exceptionsText = document.getElementById("screenerExceptionsText");

  if (grid && (!state.dailyPicksData || force)) {
    grid.innerHTML = '<div class="card-loading-placeholder">正在并发拉取长桥实时行情、单期财报并计算多因子评分与风险平价防线...</div>';
  }

  if (progressBox && (!state.dailyPicksData || force)) {
    progressBox.style.display = "block";
    if (progressText) progressText.textContent = "正在并发拉取股票池行情与单期财报并打分...";
    if (progressCount) progressCount.textContent = "0/22";
    if (progressBarFill) progressBarFill.style.width = "5%";
  }

  // Clear previous progress polling interval if exists
  if (state.progressPollingInterval) {
    clearInterval(state.progressPollingInterval);
    state.progressPollingInterval = null;
  }

  // Start polling /api/screener/progress every 1000ms
  const pollId = setInterval(async () => {
    try {
      const pRes = await fetch("/api/screener/progress");
      const pData = await pRes.json();
      if (pData.ok && pData.progress) {
        const p = pData.progress;
        const comp = p.current || p.completed || 0;
        const tot = p.total || 22;
        if (progressCount) progressCount.textContent = `${comp}/${tot}`;
        if (progressBarFill) progressBarFill.style.width = `${Math.min(100, Math.round((comp / (tot || 1)) * 100))}%`;
        if (progressText && p.current_symbol) {
          progressText.textContent = `正在并发计算 [${p.current_symbol}] 多因子评分与趋势闸门...`;
        }
        if (exceptionsBox && exceptionsText && (p.rate_limited_count > 0 || p.failed_count > 0)) {
          exceptionsBox.style.display = "block";
          exceptionsText.textContent = `当前长桥频控隔离 ${p.rate_limited_count} 只，请求异常 ${p.failed_count} 只（已单独隔离，不混入技术破位淘汰）`;
        }
      }
    } catch (e) {
      // Ignore polling errors
    }
  }, 1000);
  state.progressPollingInterval = pollId;

  try {
    const res = await fetch(`/api/screener/daily?force=${force ? 1 : 0}`);
    if (seq !== screenerLoadSeq) return;
    const data = await res.json();
    if (data.ok && data.screener) {
      state.dailyPicksData = data.screener;
      renderDailyPicks(data.screener);

      // Handle exceptions / rate limits display
      const rls = data.screener.rate_limited_symbols || [];
      const ex = data.screener.exceptions || [];
      if (exceptionsBox && exceptionsText) {
        if (rls.length > 0 || ex.length > 0) {
          exceptionsBox.style.display = "block";
          exceptionsText.textContent = `已隔离频控限制标的 [${rls.join(', ')}]，异常标的 [${ex.map(e => e.symbol).join(', ')}]，不计入流动性/趋势技术破位。`;
        } else {
          exceptionsBox.style.display = "none";
        }
      }
    } else if (grid) {
      const message = (data && data.error) || "每日选股没有返回结果";
      grid.innerHTML = `<div class="card-loading-placeholder text-danger">${escapeHtml(message)}</div>`;
    }
  } catch (err) {
    if (seq !== screenerLoadSeq) return;
    console.error("Daily screener load error:", err);
    if (grid) grid.innerHTML = `<div class="card-loading-placeholder text-danger">加载每日精选失败：${escapeHtml(err.message)}</div>`;
  } finally {
    clearInterval(pollId);
    if (state.progressPollingInterval === pollId) {
      state.progressPollingInterval = null;
      if (progressBox) progressBox.style.display = "none";
    }
  }
}

function renderDailyPicks(screener) {
  const grid = document.getElementById("dailyPicksGrid");
  if (!grid) return;

  const rawPicks = screener.picks || [];

  // Pipeline numbers (read both funnel_pipeline and pipeline)
  const pipeline = screener.pipeline || {};
  const funnel = screener.funnel_pipeline || {};
  const totalCount = pipeline.total_screened || funnel.raw_universe?.valid_count || funnel.raw_universe?.count || 22;
  const trendCount = funnel.layer_2_hard_quant?.passed_count || pipeline.trend_passed || rawPicks.length;

  const totalEl = document.getElementById("funnelTotalCount");
  const trendEl = document.getElementById("funnelTrendPassed");
  const topEl = document.getElementById("funnelTopPicks");
  if (totalEl) totalEl.textContent = `${totalCount} 只`;
  if (trendEl) trendEl.textContent = `${trendCount} 只`;
  if (topEl) topEl.textContent = `Top ${rawPicks.length}`;

  const allCountEl = document.getElementById("screenerAllCount");
  const watchCountEl = document.getElementById("screenerWatchlistCount");
  if (allCountEl) allCountEl.textContent = totalCount;
  if (watchCountEl) watchCountEl.textContent = state.watchlistSymbols ? state.watchlistSymbols.size : 0;

  // Filter picks if watchlist active (Rule P1 9)
  let displayPicks = rawPicks;
  if (state.screenerFilter === "watchlist" && state.watchlistSymbols) {
    displayPicks = rawPicks.filter(p => state.watchlistSymbols.has(p.symbol) || state.watchlistSymbols.has(normalizeSymbol(p.symbol)));
  }

  if (!displayPicks.length) {
    grid.innerHTML = state.screenerFilter === "watchlist"
      ? '<div class="card-loading-placeholder">你的自选池中暂无今日入选 Top 6 的标的（可查看下方淘汰原因明细表）</div>'
      : '<div class="card-loading-placeholder">当前宏观环境下暂无符合买方闸门的标的</div>';
  } else {
    grid.innerHTML = displayPicks.map((p, idx) => {
      const hasChange = p.change_pct != null;
      const isUp = hasChange && p.change_pct >= 0;
      const changeText = hasChange ? `${isUp ? '+' : ''}${p.change_pct.toFixed(2)}%` : '--';
      const changeClass = hasChange ? (isUp ? 'positive' : 'negative') : 'neutral';
      const scoreNum = typeof p.score === "number" && !Number.isNaN(p.score) ? p.score : null;
      const scoreClass = scoreNum == null ? "neutral" : (scoreNum >= 80 ? "strong-buy" : "buy");
      const scoreLabel = scoreNum == null ? "未评分" : `${scoreNum.toFixed(1)} 分 · ${p.verdict || "规则阈值"}`;
      const tagsHtml = (p.tags || []).slice(0, 3).map(t => `<span class="pick-sector-tag">${escapeHtml(t)}</span>`).join("");
      const tech = p.technical || {};
      const ret20Val = tech.returns ? tech.returns['20d'] : undefined;
      const ret20Text = ret20Val !== undefined && ret20Val !== null ? `${ret20Val >= 0 ? '+' : ''}${Number(ret20Val).toFixed(1)}%` : '--';
      const trendLabel = tech.trend_label || (tech.above_ma20 ? '均线上方' : '稳健');
      const isCompared = state.selectedCompareSymbols && state.selectedCompareSymbols.includes(p.symbol);
      const isWatched = state.watchlistSymbols && (state.watchlistSymbols.has(p.symbol) || state.watchlistSymbols.has(normalizeSymbol(p.symbol)));

      return `
        <div class="daily-pick-card">
          <div class="pick-card-header">
            <div class="pick-title-group">
              <span class="pick-rank-badge">#${idx + 1}</span>
              <span class="pick-symbol">${escapeHtml(p.symbol)}</span>
              <span class="pick-name-cn">${escapeHtml(p.name || "")}</span>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
              <span class="pick-score-badge ${scoreClass}" title="规则阈值，未做 T+5/T+20 样本闭环验证">${scoreLabel}</span>
              <button type="button" class="btn-card-watchlist ${isWatched ? 'active' : ''}" onclick="onToggleWatchlist('${escapeHtml(p.symbol)}', this)">
                ${isWatched ? '★ 已自选' : '☆ 加自选'}
              </button>
            </div>
          </div>
          <div class="pick-price-row">
            <div class="pick-price-box">
              <span class="pick-price">$${typeof p.last === 'number' ? p.last.toFixed(2) : p.last}</span>
              <span class="stat-pill ${changeClass}">${changeText}</span>
            </div>
            <div class="pick-tags-box">
              <span class="pick-sector-tag">${escapeHtml(p.sector || "核心科技")}</span>
              ${tagsHtml}
            </div>
          </div>
          <div class="pick-kpi-strip">
            <div class="pick-kpi-item">
              <span class="label">20日动量</span>
              <span class="val ${ret20Val != null ? (ret20Val >= 0 ? 'text-success' : 'text-danger') : 'text-muted'}">
                ${ret20Text}
              </span>
            </div>
            <div class="pick-kpi-item">
              <span class="label">量能比(20D)</span>
              <span class="val">${p.volume_ratio != null ? Number(p.volume_ratio).toFixed(2) + 'x' : '--'}</span>
            </div>
            <div class="pick-kpi-item">
              <span class="label">均线形态</span>
              <span class="val text-truncate">${escapeHtml(trendLabel)}</span>
            </div>
          </div>
          <div class="pick-defense-box">
            <span class="icon">🛡️</span>
            <span>${escapeHtml(p.primary_defense || (p.stop_loss ? `2×ATR 止损价 $${p.stop_loss}` : '2×ATR 跟踪止损'))}</span>
          </div>
          <p class="pick-rationale">${escapeHtml(p.core_rationale || "多因子量化评分领先，量价多头排列。")}</p>
          <div class="pick-actions-row">
            <button type="button" class="btn-card-action primary" onclick="jumpToDossier('${escapeHtml(p.symbol)}')">
              <span>🔍 深度调阅档案</span>
            </button>
            <label class="card-compare-label" style="display:inline-flex; align-items:center; gap:4px; font-size:12px; color:#cbd5e1; cursor:pointer;">
              <input type="checkbox" class="compare-checkbox" data-symbol="${escapeHtml(p.symbol)}" ${isCompared ? 'checked' : ''} onchange="onToggleCompareSymbol('${escapeHtml(p.symbol)}', this.checked)">
              <span>对比</span>
            </label>
          </div>
        </div>
      `;
    }).join("");
  }

  // Render culled / near-miss details (Rule 2 & P1 9 & P1 11)
  const culledList = screener.culled_details || screener.near_misses || [];
  const culledCard = document.getElementById("culledDetailsCard");
  const culledCountBadge = document.getElementById("culledCountBadge");
  const culledTableBody = document.getElementById("culledTableBody");

  let displayCulled = culledList;
  if (state.screenerFilter === "watchlist" && state.watchlistSymbols) {
    displayCulled = culledList.filter(c => state.watchlistSymbols.has(c.symbol) || state.watchlistSymbols.has(normalizeSymbol(c.symbol)));
  }

  if (culledCard && culledList.length > 0) {
    culledCard.style.display = "block";
    if (culledCountBadge) culledCountBadge.textContent = displayCulled.length;
    if (culledTableBody) {
      if (!displayCulled.length) {
        culledTableBody.innerHTML = '<tr><td colspan="7" class="text-center text-muted" style="padding:20px;">自选池中暂无被淘汰标的</td></tr>';
      } else {
        culledTableBody.innerHTML = displayCulled.map(c => {
          const isCompared = state.selectedCompareSymbols && state.selectedCompareSymbols.includes(c.symbol);
          const isWatched = state.watchlistSymbols && (state.watchlistSymbols.has(c.symbol) || state.watchlistSymbols.has(normalizeSymbol(c.symbol)));

          return `
            <tr>
              <td>
                <input type="checkbox" class="compare-checkbox" data-symbol="${escapeHtml(c.symbol)}" ${isCompared ? 'checked' : ''} onchange="onToggleCompareSymbol('${escapeHtml(c.symbol)}', this.checked)">
              </td>
              <td><strong class="font-mono text-primary cursor-pointer" onclick="jumpToDossier('${escapeHtml(c.symbol)}')">${escapeHtml(c.symbol)}</strong> <small class="text-muted ml-1">${escapeHtml(c.name || '')}</small></td>
              <td class="font-mono">$${c.last ? Number(c.last).toFixed(2) : '--'}</td>
              <td class="font-mono ${c.ret20 != null ? (c.ret20 >= 0 ? 'text-success' : 'text-danger') : 'text-muted'}">${c.ret20 !== undefined && c.ret20 !== null ? (c.ret20 >= 0 ? '+' : '') + Number(c.ret20).toFixed(1) + '%' : '--'}</td>
              <td class="font-mono">${c.score !== undefined && c.score !== null ? c.score + '分' : '<span class="text-muted">--</span>'}</td>
              <td><span class="badge-culled">${escapeHtml(c.category_label || c.verdict || '淘汰')}</span> <span class="text-muted text-xs ml-1">${escapeHtml(c.reason || c.cull_reason || '未入选')}</span></td>
              <td>
                <button type="button" class="btn-table-watchlist ${isWatched ? 'active' : ''}" onclick="onToggleWatchlist('${escapeHtml(c.symbol)}', this)">
                  ${isWatched ? '★' : '☆'}
                </button>
              </td>
            </tr>
          `;
        }).join("");
      }
    }
  }
}

async function runCustomScreener() {
  const input = document.getElementById("customUniverseInput");
  const resultsContainer = document.getElementById("customScreenerResults");
  const tbody = document.getElementById("customScreenerTableBody");
  const btn = document.getElementById("btnRunCustomScreener");

  const symbols = (input ? input.value : "").trim();
  if (!symbols) return;

  if (btn) btn.disabled = true;
  if (resultsContainer) resultsContainer.style.display = "block";
  if (tbody) tbody.innerHTML = '<tr><td colspan="11" class="text-center text-muted">正在并发请求行情并计算多因子分...</td></tr>';

  try {
    const res = await fetch(`/api/screener/run?symbols=${encodeURIComponent(symbols)}&limit=25`);
    const data = await res.json();
    const rows = data.all || data.rows || (Array.isArray(data) ? data : null);
    if ((data.ok || rows) && Array.isArray(rows)) {
      renderCustomScreenerTable(rows);
    } else {
      if (tbody) tbody.innerHTML = `<tr><td colspan="11" class="text-center text-danger">筛选失败：${escapeHtml(data.error || '未知错误')}</td></tr>`;
    }
  } catch (err) {
    if (tbody) tbody.innerHTML = `<tr><td colspan="11" class="text-center text-danger">网络异常：${escapeHtml(err.message)}</td></tr>`;
  } finally {
    if (btn) btn.disabled = false;
  }
}

function renderCustomScreenerTable(rows) {
  const tbody = document.getElementById("customScreenerTableBody");
  if (!tbody) return;

  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="11" class="text-center text-muted">无符合条件的标的</td></tr>';
    return;
  }

  tbody.innerHTML = rows.map((r, i) => {
    const hasChange = r.change_pct != null;
    const isUp = hasChange && r.change_pct >= 0;
    const changeText = hasChange ? `${isUp ? '+' : ''}${r.change_pct.toFixed(2)}%` : '--';
    const changeClass = hasChange ? (isUp ? 'text-success' : 'text-danger') : 'text-muted';
    const ret20 = r.technical && r.technical.returns && r.technical.returns['20d'];
    const stopLoss = (r.technical && r.technical.trailing_stop_2atr) || (r.last ? (r.last * 0.93).toFixed(2) : '--');
    const scoreVal = (r.score !== undefined && r.score !== null) ? `${r.score} 分` : '--';
    const verdictLabel = r.fail_reason || r.verdict || (r.trend_passed === false ? '趋势淘汰' : '观察');
    return `
      <tr>
        <td class="font-mono text-muted">#${i + 1}</td>
        <td>
          <strong class="font-mono text-primary cursor-pointer" onclick="jumpToDossier('${escapeHtml(r.symbol)}')">${escapeHtml(r.symbol)}</strong>
          <small class="text-muted ml-1">${escapeHtml(r.name || '')}</small>
        </td>
        <td class="font-mono">$${typeof r.last === 'number' ? r.last.toFixed(2) : r.last}</td>
        <td class="font-mono ${changeClass}">${changeText}</td>
        <td><strong class="font-mono ${r.score != null ? 'text-emerald' : 'text-muted'}">${scoreVal}</strong></td>
        <td><span class="badge-verdict">${escapeHtml(verdictLabel)}</span></td>
        <td class="text-muted">${escapeHtml(r.sector || '综合')}</td>
        <td class="font-mono ${ret20 != null ? (ret20 >= 0 ? 'text-success' : 'text-danger') : 'text-muted'}">${ret20 !== undefined && ret20 !== null ? (ret20 >= 0 ? '+' : '') + Number(ret20).toFixed(1) + '%' : '--'}</td>
        <td class="font-mono">${r.technical && r.technical.volume_ratio_20d ? Number(r.technical.volume_ratio_20d).toFixed(2) + 'x' : '--'}</td>
        <td class="font-mono text-rose">$${stopLoss}</td>
        <td>
          <button type="button" class="btn-ghost-sm" onclick="jumpToDossier('${escapeHtml(r.symbol)}')">调阅</button>
        </td>
      </tr>
    `;
  }).join("");
}

// ==============================================================================
// Compare Tab Implementation
// ==============================================================================

function initCompareListeners() {
  const btnRun = document.getElementById("btnRunCompare");
  if (btnRun) {
    btnRun.addEventListener("click", () => runCompare());
  }

  document.querySelectorAll(".compare-presets-strip .preset-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const symbols = chip.getAttribute("data-compare");
      const input = document.getElementById("compareSymbolsInput");
      if (input && symbols) {
        input.value = symbols;
        runCompare();
      }
    });
  });
}

async function loadCompareTab() {
  if (!state.compareData) {
    runCompare();
  }
}

async function runCompare() {
  const input = document.getElementById("compareSymbolsInput");
  const symbols = (input ? input.value : "").trim() || "NVDA.US, AMD.US, AVGO.US";
  const btn = document.getElementById("btnRunCompare");
  const theadRow = document.getElementById("compareTableHeadRow");
  const tbody = document.getElementById("compareTableBody");

  if (btn) btn.disabled = true;
  if (tbody) tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">正在并发请求多股指标并生成对比矩阵...</td></tr>';

  try {
    const res = await fetch(`/api/compare?symbols=${encodeURIComponent(symbols)}`);
    const data = await res.json();
    const rows = data.rows || (Array.isArray(data) ? data : null);
    if ((data.ok || rows) && Array.isArray(rows)) {
      state.compareData = data;
      renderCompareView(data);
    } else {
      if (tbody) tbody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">对比失败：${escapeHtml(data.error || '未知错误')}</td></tr>`;
    }
  } catch (err) {
    if (tbody) tbody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">网络异常：${escapeHtml(err.message)}</td></tr>`;
  } finally {
    if (btn) btn.disabled = false;
  }
}

function renderCompareView(data) {
  const leaders = data.leaders || {};
  const rows = data.rows || [];

  // Update leaders
  const lScore = leaders["综合评分"] || {};
  const lScoreSym = document.getElementById("leaderScoreSym");
  const lScoreVal = document.getElementById("leaderScoreVal");
  if (lScoreSym) lScoreSym.textContent = lScore.symbol || "--";
  if (lScoreVal) lScoreVal.textContent = lScore.value ? `${lScore.value} 分` : "--";

  const lMom = leaders["20日涨跌"] || {};
  const lMomSym = document.getElementById("leaderMomentumSym");
  const lMomVal = document.getElementById("leaderMomentumVal");
  if (lMomSym) lMomSym.textContent = lMom.symbol || "--";
  if (lMomVal) lMomVal.textContent = lMom.value !== undefined ? `${lMom.value >= 0 ? '+' : ''}${Number(lMom.value).toFixed(1)}%` : "--";

  const lVal = leaders["估值PE"] || {};
  const lValSym = document.getElementById("leaderValuationSym");
  const lValVal = document.getElementById("leaderValuationVal");
  if (lValSym) lValSym.textContent = lVal.symbol || "--";
  if (lValVal) {
    if (typeof lVal.value === "string") {
      lValVal.textContent = lVal.value;
    } else if (typeof lVal.value === "number") {
      lValVal.textContent = `PE ${lVal.value.toFixed(1)}x`;
    } else {
      lValVal.textContent = "--";
    }
  }

  const lTurn = leaders["成交额"] || {};
  const lTurnSym = document.getElementById("leaderTurnoverSym");
  const lTurnVal = document.getElementById("leaderTurnoverVal");
  if (lTurnSym) lTurnSym.textContent = lTurn.symbol || "--";
  if (lTurnVal) lTurnVal.textContent = lTurn.value ? `$${(lTurn.value / 1e8).toFixed(1)} 亿` : "--";

  // Table header
  const theadRow = document.getElementById("compareTableHeadRow");
  if (theadRow) {
    theadRow.innerHTML = `<th>维度 / 核心量化指标</th>` + rows.map(r => `
      <th class="text-center">
        <div class="cursor-pointer" onclick="jumpToDossier('${escapeHtml(r.symbol)}')">
          <strong class="text-primary font-mono">${escapeHtml(r.symbol)}</strong>
          <div class="text-muted text-xs">${escapeHtml(r.name || '')}</div>
        </div>
      </th>
    `).join("");
  }

  // Table rows
  const tbody = document.getElementById("compareTableBody");
  if (!tbody) return;

  const metricDefs = [
    { label: "选股闸门状态", fn: r => {
      const isTrend = r.trend_passed !== false;
      return isTrend 
        ? '<span class="stat-pill positive">✅ 趋势达标 (入选候选池)</span>' 
        : '<span class="stat-pill negative" title="20日动量为负且跌破20日均线，在每日选股中被 Gate 2 硬规则汰除">❌ Gate 2 趋势破位淘汰</span>';
    }},
    { label: "最新收盘价", fn: r => `$${typeof r.last === 'number' ? r.last.toFixed(2) : r.last}` },
    { label: "日内涨跌幅", fn: r => {
      if (r.change_pct == null) return '<span class="font-mono text-muted">--</span>';
      const isUp = r.change_pct >= 0;
      return `<span class="${isUp ? 'text-success' : 'text-danger'} font-mono">${isUp ? '+' : ''}${r.change_pct.toFixed(2)}%</span>`;
    }},
    { label: "综合量化评分", fn: r => {
      const isTrend = r.trend_passed !== false;
      if (!isTrend) {
        return `<span class="text-rose font-mono font-weight-500">${r.score != null ? r.score : '--'} 分</span> <span class="badge badge-warning text-xs" title="该标的未通过趋势硬规则闸门 (破位)，评分仅供横向参考，不作为买入推荐">⚠️ 破位淘汰 (仅供对比诊断)</span>`;
      }
      return `<strong class="text-emerald font-mono">${r.score != null ? r.score + ' 分' : '--'}</strong> (${r.verdict || '--'})`;
    }},
    { label: "20日动量收益", fn: r => {
      const v = r.technical && r.technical.returns && r.technical.returns['20d'];
      return `<span class="${v != null ? (v >= 0 ? 'text-success' : 'text-danger') : 'text-muted'} font-mono">${v != null ? (v >= 0 ? '+' : '') + Number(v).toFixed(1) + '%' : '--'}</span>`;
    }},
    { label: "60日动量收益", fn: r => {
      const v = r.technical && r.technical.returns && r.technical.returns['60d'];
      return `<span class="${v != null ? (v >= 0 ? 'text-success' : 'text-danger') : 'text-muted'} font-mono">${v != null ? (v >= 0 ? '+' : '') + Number(v).toFixed(1) + '%' : '--'}</span>`;
    }},
    { label: "均线多空形态", fn: r => {
      const isTrend = r.trend_passed !== false;
      const label = r.technical ? r.technical.trend_label || '均线上方' : '--';
      return `<span class="${isTrend ? 'text-success' : 'text-danger'} font-mono font-weight-500">${escapeHtml(label)}${!isTrend ? ' (跌破20日线)' : ''}</span>`;
    }},
    { label: "RSI(14) 强弱度", fn: r => r.technical && r.technical.rsi14 ? `<span class="font-mono">${r.technical.rsi14.toFixed(1)}</span>` : '--' },
    { label: "市盈率 PE (TTM)", fn: r => r.valuation && r.valuation.pe ? `<span class="font-mono">${r.valuation.pe.toFixed(1)}x</span>` : '--' },
    { label: "机构平均目标价", fn: r => r.rating && r.rating.target ? `<span class="font-mono">$${r.rating.target}</span>` : '--' },
    { label: "目标价潜在空间", fn: r => {
      if (r.rating && r.rating.target && r.last) {
        const upside = ((r.rating.target / r.last) - 1) * 100;
        return `<span class="${upside >= 0 ? 'text-success' : 'text-danger'} font-mono">${upside >= 0 ? '+' : ''}${upside.toFixed(1)}%</span>`;
      }
      return '--';
    }},
    { label: "第一止损防线", fn: r => `<span class="text-rose font-mono">$${(r.technical && r.technical.trailing_stop_2atr) || (r.last ? (r.last * 0.93).toFixed(2) : '--')}</span>` },
    { label: "深度投研档案", fn: r => `<button type="button" class="btn-ghost-sm" onclick="jumpToDossier('${escapeHtml(r.symbol)}')">调阅全景</button>` },
  ];

  tbody.innerHTML = metricDefs.map(m => `
    <tr>
      <td class="text-muted font-weight-500">${m.label}</td>
      ${rows.map(r => `<td class="text-center">${m.fn(r)}</td>`).join("")}
    </tr>
  `).join("");
}

// ==============================================================================
// Backtest Tab Implementation & Interactive SVG Equity Curve
// ==============================================================================

function initBacktestListeners() {
  const btnRun = document.getElementById("btnRunBacktest");
  if (btnRun) {
    btnRun.addEventListener("click", () => loadBacktestTab(true));
  }

  document.querySelectorAll("#sensitivityMetricTabs .tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#sensitivityMetricTabs .tab-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      state.activeSensitivityMetric = btn.getAttribute("data-metric") || "sharpe";
      if (state.sensitivityData) {
        renderSensitivityTable(state.sensitivityData);
      }
    });
  });
}

async function loadBacktestTab(force = false) {
  const range = (document.getElementById("btRangeSelect") || {}).value || "2y";
  const freq = (document.getElementById("btFreqSelect") || {}).value || "15";
  const topN = (document.getElementById("btTopNSelect") || {}).value || "3";
  const atr = (document.getElementById("btAtrSelect") || {}).value || "2.5";
  const btn = document.getElementById("btnRunBacktest");

  if (btn) btn.disabled = true;

  try {
    const res = await fetch(`/api/backtest/run?range=${range}&rebalance_freq=${freq}&top_n=${topN}&atr_mult=${atr}&force=${force ? 1 : 0}`);
    const data = await res.json();
    const bt = data.backtest || (data.performance ? { ...data, ...data.performance } : data);
    if (bt && (bt.strategy_total_return_pct !== undefined || data.ok)) {
      state.backtestData = bt;
      renderBacktestMetrics(bt);

      const disclaimerEl = document.getElementById("btDisclaimerText");
      if (disclaimerEl && bt.disclaimer) {
        disclaimerEl.textContent = bt.disclaimer;
      }

      let curve = bt.equity_curve || (Array.isArray(data.equity_curve) ? data.equity_curve : null);
      if (Array.isArray(curve)) {
        renderEquityChart(curve);
      } else if (curve && Array.isArray(curve.dates)) {
        const transformed = curve.dates.map((d, i) => ({
          date: d,
          strategy_nav: (curve.strategy && curve.strategy[i]) ?? 100000,
          benchmark_nav: (curve.benchmark && curve.benchmark[i]) ?? 100000
        }));
        renderEquityChart(transformed);
      }
    }
  } catch (err) {
    console.error("Backtest load error:", err);
  } finally {
    if (btn) btn.disabled = false;
  }

  // Load sensitivity matrix
  loadSensitivityMatrix(range, topN, force);
}

function renderBacktestMetrics(bt) {
  const sRet = bt.strategy_total_return_pct ?? bt.performance?.strategy_total_return_pct ?? 0;
  const bRet = bt.benchmark_total_return_pct ?? bt.performance?.benchmark_total_return_pct ?? 0;
  const alpha = bt.alpha_pct ?? bt.performance?.alpha_pct ?? (sRet - bRet);

  const sRetEl = document.getElementById("btStrategyRet");
  if (sRetEl) {
    sRetEl.textContent = `${sRet >= 0 ? '+' : ''}${sRet.toFixed(1)}%`;
    sRetEl.className = `bt-metric-val ${sRet >= 0 ? 'positive' : 'negative'}`;
  }
  const sCagr = bt.strategy_cagr_pct ?? bt.performance?.strategy_cagr_pct;
  const sCagrEl = document.getElementById("btStrategyCagr");
  if (sCagrEl) sCagrEl.textContent = `CAGR: ${sCagr != null ? (sCagr >= 0 ? '+' : '') + sCagr.toFixed(1) + '%' : '--'}`;

  const bRetEl = document.getElementById("btBenchmarkRet");
  if (bRetEl) {
    bRetEl.textContent = `${bRet >= 0 ? '+' : ''}${bRet.toFixed(1)}%`;
    bRetEl.className = `bt-metric-val ${bRet >= 0 ? 'positive' : 'negative'}`;
  }
  const bCagr = bt.benchmark_cagr_pct ?? bt.performance?.benchmark_cagr_pct;
  const bCagrEl = document.getElementById("btBenchmarkCagr");
  if (bCagrEl) bCagrEl.textContent = `CAGR: ${bCagr != null ? (bCagr >= 0 ? '+' : '') + bCagr.toFixed(1) + '%' : '--'}`;

  const alphaEl = document.getElementById("btAlpha");
  if (alphaEl) {
    alphaEl.textContent = `${alpha >= 0 ? '+' : ''}${alpha.toFixed(1)}%`;
    alphaEl.className = `bt-metric-val ${alpha >= 0 ? 'positive' : 'negative'}`;
  }

  const sharpe = bt.sharpe_ratio ?? bt.performance?.sharpe_ratio;
  const sharpeEl = document.getElementById("btSharpe");
  if (sharpeEl) sharpeEl.textContent = typeof sharpe === 'number' ? sharpe.toFixed(2) : '--';

  const mdd = bt.strategy_max_drawdown_pct ?? bt.max_drawdown_pct ?? bt.performance?.strategy_max_drawdown_pct ?? bt.performance?.max_drawdown_pct ?? 0.0;
  const mddEl = document.getElementById("btMaxDd");
  if (mddEl) mddEl.textContent = `${Number(mdd).toFixed(1)}%`;

  const bMdd = bt.benchmark_max_drawdown_pct ?? bt.performance?.benchmark_max_drawdown_pct;
  const bMddEl = document.getElementById("btBenchDd");
  if (bMddEl) bMddEl.textContent = `基准回撤: ${bMdd != null ? Number(bMdd).toFixed(1) + '%' : '--'}`;

  const win = bt.win_rate_pct ?? bt.performance?.win_rate_pct ?? 0.0;
  const winEl = document.getElementById("btWinRate");
  if (winEl) winEl.textContent = `${Number(win).toFixed(1)}%`;

  const trades = bt.total_trades ?? bt.total_rebalance_events ?? bt.performance?.total_trades ?? bt.performance?.total_rebalance_events ?? 0;
  const tradesEl = document.getElementById("btTotalTrades");
  if (tradesEl) tradesEl.textContent = `总调仓: ${trades} 次`;
}

function renderEquityChart(equityCurve) {
  const svg = document.getElementById("equityChartSvg");
  const wrapper = document.getElementById("equityChartWrapper");
  const tooltip = document.getElementById("chartTooltip");
  if (!svg || !equityCurve || equityCurve.length < 2) return;

  const N = equityCurve.length;
  const width = 900;
  const height = 320;
  const padLeft = 50;
  const padRight = 20;
  const padTop = 20;
  const padBottom = 30;

  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;

  const allVals = equityCurve.flatMap(p => [p.strategy_nav || 100000, p.benchmark_nav || 100000]);
  const minV = Math.min(...allVals) * 0.98;
  const maxV = Math.max(...allVals) * 1.02;

  const getX = (i) => padLeft + (i / (N - 1)) * plotW;
  const getY = (val) => padTop + plotH - ((val - minV) / (maxV - minV)) * plotH;

  // Paths
  let sPath = `M ${getX(0)} ${getY(equityCurve[0].strategy_nav || 100000)}`;
  let bPath = `M ${getX(0)} ${getY(equityCurve[0].benchmark_nav || 100000)}`;
  for (let i = 1; i < N; i++) {
    sPath += ` L ${getX(i)} ${getY(equityCurve[i].strategy_nav || 100000)}`;
    bPath += ` L ${getX(i)} ${getY(equityCurve[i].benchmark_nav || 100000)}`;
  }

  // Strategy Area
  const areaPath = `${sPath} L ${getX(N - 1)} ${padTop + plotH} L ${getX(0)} ${padTop + plotH} Z`;

  // Grid lines
  const gridLines = [0.25, 0.5, 0.75].map(ratio => {
    const y = padTop + plotH * ratio;
    const v = minV + (1 - ratio) * (maxV - minV);
    const retPct = ((v / 100000 - 1) * 100).toFixed(0);
    return `
      <line x1="${padLeft}" y1="${y}" x2="${width - padRight}" y2="${y}" stroke="rgba(255,255,255,0.06)" stroke-dasharray="4,4" />
      <text x="${padLeft - 6}" y="${y + 4}" fill="#64748b" font-size="10" text-anchor="end" font-family="JetBrains Mono">${retPct > 0 ? '+' : ''}${retPct}%</text>
    `;
  }).join("");

  svg.innerHTML = `
    <defs>
      <linearGradient id="strategyGrad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.3" />
        <stop offset="100%" stop-color="#38bdf8" stop-opacity="0.0" />
      </linearGradient>
    </defs>
    ${gridLines}
    <path d="${areaPath}" fill="url(#strategyGrad)" />
    <path d="${bPath}" fill="none" stroke="#64748b" stroke-width="1.5" stroke-dasharray="3,3" />
    <path d="${sPath}" fill="none" stroke="#38bdf8" stroke-width="2.5" />
    <line id="cursorLine" x1="0" y1="${padTop}" x2="0" y2="${padTop + plotH}" stroke="rgba(255,255,255,0.4)" stroke-dasharray="2,2" style="display:none;" />
  `;

  // Hover interaction
  if (wrapper && tooltip) {
    wrapper.onmousemove = (e) => {
      const rect = wrapper.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const svgX = (mouseX / rect.width) * width;
      if (svgX < padLeft || svgX > width - padRight) {
        tooltip.style.display = "none";
        const cur = svg.querySelector("#cursorLine");
        if (cur) cur.style.display = "none";
        return;
      }
      const idx = Math.min(N - 1, Math.max(0, Math.round(((svgX - padLeft) / plotW) * (N - 1))));
      const pt = equityCurve[idx];
      const cur = svg.querySelector("#cursorLine");
      if (cur) {
        cur.setAttribute("x1", getX(idx));
        cur.setAttribute("x2", getX(idx));
        cur.style.display = "block";
      }
      const sRet = ((pt.strategy_nav / 100000 - 1) * 100).toFixed(1);
      const bRet = ((pt.benchmark_nav / 100000 - 1) * 100).toFixed(1);
      tooltip.style.display = "block";
      tooltip.style.left = `${Math.min(rect.width - 160, Math.max(10, mouseX + 12))}px`;
      tooltip.style.top = `20px`;
      tooltip.innerHTML = `
        <div class="font-mono text-muted mb-1">${pt.date || ''}</div>
        <div class="text-cyan font-mono">策略: $${Math.round(pt.strategy_nav).toLocaleString()} (${sRet > 0 ? '+' : ''}${sRet}%)</div>
        <div class="text-muted font-mono">标普: $${Math.round(pt.benchmark_nav).toLocaleString()} (${bRet > 0 ? '+' : ''}${bRet}%)</div>
      `;
    };
    wrapper.onmouseleave = () => {
      tooltip.style.display = "none";
      const cur = svg.querySelector("#cursorLine");
      if (cur) cur.style.display = "none";
    };
  }
}

async function loadSensitivityMatrix(range = "2y", topN = 3, force = false) {
  const tbody = document.getElementById("sensitivityTableBody");
  try {
    const res = await fetch(`/api/backtest/sensitivity?range=${range}&top_n=${topN}&force=${force ? 1 : 0}`);
    const data = await res.json();
    const sens = data.sensitivity || data;
    if (sens && (sens.grid || sens.matrix)) {
      state.sensitivityData = sens;
      renderSensitivityTable(sens);
    }
  } catch (err) {
    if (tbody) tbody.innerHTML = `<tr><td class="text-center text-muted">敏感度矩阵载入失败：${escapeHtml(err.message)}</td></tr>`;
  }
}

function renderSensitivityTable(sens) {
  const tbody = document.getElementById("sensitivityTableBody");
  if (!tbody || (!sens.grid && !sens.matrix)) return;

  const metric = state.activeSensitivityMetric || "sharpe";
  const freqs = sens.rebalance_freqs || sens.frequencies || [5, 10, 15, 20];
  const atrs = sens.atr_multipliers || [2.0, 2.5, 3.0];
  const optimal = sens.optimal || sens.optimal_frontier || {};

  // Build unified cellMap supporting both grid and matrix layouts
  const cellMap = {};
  if (sens.grid && typeof sens.grid === "object") {
    Object.assign(cellMap, sens.grid);
  }
  if (Array.isArray(sens.matrix)) {
    sens.matrix.forEach(row => {
      if (Array.isArray(row)) {
        row.forEach(cell => {
          if (cell) {
            const f = cell.freq ?? cell.rebal_days ?? cell.rebalance_freq;
            const a = cell.atr_mult ?? cell.atr ?? cell.atr_multiplier;
            if (f != null && a != null) {
              cellMap[`${f}d_${a}x`] = cell;
              cellMap[`${f}d_${Number(a).toFixed(1)}x`] = cell;
            }
          }
        });
      }
    });
  }

  let headerHtml = `<tr><th>调仓频率 \\ 跟踪止损</th>` + atrs.map(a => `<th>${a}× ATR</th>`).join("") + `</tr>`;
  let rowsHtml = freqs.map(freq => {
    let cells = atrs.map(atr => {
      const key = `${freq}d_${atr}x`;
      const keyF = `${freq}d_${Number(atr).toFixed(1)}x`;
      const item = cellMap[key] || cellMap[keyF] || {};

      let val;
      if (metric === "sharpe") {
        val = item.sharpe ?? item.sharpe_ratio;
      } else if (metric === "total_return") {
        val = item.total_return ?? item.strat_return_pct ?? item.strategy_return ?? item.strategy_total_return_pct;
      } else if (metric === "max_drawdown") {
        val = item.max_drawdown ?? item.max_drawdown_pct ?? item.strategy_max_drawdown_pct;
        if (typeof val === "number") val = Math.abs(val);
      }

      let displayVal = "--";
      let cellBg = "rgba(255,255,255,0.03)";
      let textColor = "#f3f4f6";

      if (metric === "sharpe" && typeof val === 'number') {
        displayVal = val.toFixed(2);
        if (val >= 1.5) cellBg = "rgba(16, 185, 129, 0.35)";
        else if (val >= 1.0) cellBg = "rgba(16, 185, 129, 0.18)";
        else if (val >= 0.5) cellBg = "rgba(245, 158, 11, 0.15)";
        else cellBg = "rgba(239, 68, 68, 0.15)";
      } else if (metric === "total_return" && typeof val === 'number') {
        displayVal = `${val >= 0 ? '+' : ''}${val.toFixed(1)}%`;
        cellBg = val >= 50 ? "rgba(16, 185, 129, 0.35)" : (val >= 20 ? "rgba(16, 185, 129, 0.18)" : "rgba(245, 158, 11, 0.15)");
      } else if (metric === "max_drawdown" && typeof val === 'number') {
        displayVal = `-${val.toFixed(1)}%`;
        cellBg = val <= 15 ? "rgba(16, 185, 129, 0.35)" : (val <= 25 ? "rgba(245, 158, 11, 0.15)" : "rgba(239, 68, 68, 0.25)");
      }

      const isOpt = (optimal.rebalance_freq === freq && Math.abs((optimal.atr_multiplier || 0) - atr) < 0.05) ||
                    (optimal.freq === freq && Math.abs((optimal.atr || 0) - atr) < 0.05) ||
                    ((optimal.best_sharpe?.freq === freq) && Math.abs((optimal.best_sharpe?.atr_mult || 0) - atr) < 0.05);
      const border = isOpt ? "border: 2px solid #38bdf8;" : "border: 1px solid rgba(255,255,255,0.08);";

      return `<td style="background: ${cellBg}; color: ${textColor}; ${border}" title="${key}">${displayVal} ${isOpt ? '★' : ''}</td>`;
    }).join("");
    return `<tr><th>每 ${freq} 交易日</th>${cells}</tr>`;
  }).join("");

  tbody.innerHTML = headerHtml + rowsHtml;
}

// ==============================================================================
// Portfolio Tab Implementation
// ==============================================================================

function initPortfolioListeners() {
  const btn = document.getElementById("btnRecalculatePortfolio");
  if (btn) {
    btn.addEventListener("click", () => recalculatePortfolio());
  }
}

async function loadPortfolioTab() {
  const macroCapInput = document.getElementById("portMacroCap");
  if (macroCapInput) {
    const macroExp = state.macroData?.regime?.suggested_exposure || state.dailyPicksData?.macro_target_exposure;
    if (typeof macroExp === "number") {
      macroCapInput.value = macroExp;
    } else if (typeof macroExp === "string" && macroExp.includes("-")) {
      const nums = macroExp.match(/\d+/g);
      if (nums && nums.length >= 2) {
        macroCapInput.value = Math.round((parseInt(nums[0]) + parseInt(nums[1])) / 2);
      }
    } else if (state.dailyPicksData?.macro_target_exposure) {
      macroCapInput.value = state.dailyPicksData.macro_target_exposure;
    }
  }

  if (!state.portfolioData) {
    recalculatePortfolio();
  }
}

async function recalculatePortfolio() {
  const capital = parseFloat((document.getElementById("portTotalCapital") || {}).value || 100000);
  const riskPct = parseFloat((document.getElementById("portRiskPct") || {}).value || 1.5);
  const sectorCap = parseFloat((document.getElementById("portSectorCap") || {}).value || 30.0);
  const singleCap = parseFloat((document.getElementById("portSingleCap") || {}).value || 25.0);
  const macroCap = parseFloat((document.getElementById("portMacroCap") || {}).value || 80.0);
  const btn = document.getElementById("btnRecalculatePortfolio");
  const tbody = document.getElementById("portfolioTableBody");

  if (btn) btn.disabled = true;
  if (tbody) tbody.innerHTML = '<tr><td colspan="11" class="text-center text-muted">正在根据 ATR(14) 风险平价与行业限额重测组合...</td></tr>';

  try {
    const res = await fetch("/api/portfolio/calculate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        total_capital: capital,
        risk_per_trade_pct: riskPct,
        max_sector_exposure_pct: sectorCap,
        max_single_stock_pct: singleCap,
        macro_exposure_limit_pct: macroCap
      })
    });
    const data = await res.json();
    if (data.ok && data.portfolio) {
      state.portfolioData = data.portfolio;
      renderPortfolioView(data.portfolio);
    } else {
      if (tbody) tbody.innerHTML = `<tr><td colspan="11" class="text-center text-danger">测算失败：${escapeHtml(data.error || '未知错误')}</td></tr>`;
    }
  } catch (err) {
    if (tbody) tbody.innerHTML = `<tr><td colspan="11" class="text-center text-danger">网络异常：${escapeHtml(err.message)}</td></tr>`;
  } finally {
    if (btn) btn.disabled = false;
  }
}

function renderPortfolioView(plan) {
  const sumTotalEl = document.getElementById("portSumTotal");
  const sumInvEl = document.getElementById("portSumInvested");
  const sumInvPctEl = document.getElementById("portSumInvestedPct");
  const sumCashEl = document.getElementById("portSumCash");
  const sumCashPctEl = document.getElementById("portSumCashPct");
  const sumConEl = document.getElementById("portSumConstraints");
  const sumConDescEl = document.getElementById("portSumConstraintsDesc");

  const totalCap = Number(plan.total_capital || 100000);
  const invested = Number(plan.total_invested ?? plan.total_allocated ?? 0);
  const cash = Number(plan.cash_reserve ?? (totalCap - invested));
  const invPct = plan.total_exposure_pct != null ? Number(plan.total_exposure_pct).toFixed(1) : ((invested / totalCap) * 100).toFixed(1);
  const cashPct = plan.cash_pct != null ? Number(plan.cash_pct).toFixed(1) : ((cash / totalCap) * 100).toFixed(1);

  if (sumTotalEl) sumTotalEl.textContent = `$${Math.round(totalCap).toLocaleString()}`;
  if (sumInvEl) sumInvEl.textContent = `$${Math.round(invested).toLocaleString()}`;
  if (sumInvPctEl) sumInvPctEl.textContent = `总仓位: ${invPct}%`;
  if (sumCashEl) sumCashEl.textContent = `$${Math.round(cash).toLocaleString()}`;
  if (sumCashPctEl) sumCashPctEl.textContent = `现金垫: ${cashPct}%`;

  const allocations = plan.allocations || [];
  const constrainedCount = allocations.filter(a => a.sector_cap_triggered || a.sector_constraint_triggered || a.macro_constraint_triggered).length;
  if (sumConEl) sumConEl.textContent = `${constrainedCount} 只标的`;
  if (sumConDescEl) sumConDescEl.textContent = constrainedCount > 0 ? "已触发单一行业30%上限调减" : "未触发行业硬顶拦截";

  const tbody = document.getElementById("portfolioTableBody");
  if (!tbody) return;

  if (!allocations.length) {
    tbody.innerHTML = '<tr><td colspan="11" class="text-center text-muted">无可分配标的</td></tr>';
    return;
  }

  const sectorMap = {};
  if (Array.isArray(plan.sectors)) {
    plan.sectors.forEach(s => {
      sectorMap[s.sector] = s.weight_pct;
    });
  }

  tbody.innerHTML = allocations.map(a => {
    const isSectorCap = Boolean(a.sector_cap_triggered || a.sector_constraint_triggered);
    const shares = a.shares ?? a.allocated_shares ?? 0;
    const note = a.allocation_note || "";
    let statusBadge = '<span class="stat-pill positive">正常配置</span>';
    if (shares === 0) {
      statusBadge = `
        <span class="stat-pill neutral" title="${escapeHtml(note)}">0 股 (未建仓)</span>
        <div class="text-xs text-muted" style="max-width: 260px; line-height: 1.3; margin-top: 4px;">${escapeHtml(note || "可用预算不足")}</div>
      `;
    } else if (isSectorCap) {
      statusBadge = `
        <span class="stat-pill negative" title="${escapeHtml(note || '行业敞口达到 30% 上限')}">行业调减 (${shares}股)</span>
        <div class="text-xs text-muted" style="max-width: 260px; line-height: 1.3; margin-top: 4px;">${escapeHtml(note)}</div>
      `;
    } else if (a.macro_constraint_triggered) {
      statusBadge = `
        <span class="stat-pill neutral" title="${escapeHtml(note || '宏观总仓位上限约束')}">宏观截断 (${shares}股)</span>
        <div class="text-xs text-muted" style="max-width: 260px; line-height: 1.3; margin-top: 4px;">${escapeHtml(note)}</div>
      `;
    } else if (note && note !== "正常配置") {
      statusBadge = `
        <span class="stat-pill positive" title="${escapeHtml(note)}">正常配置</span>
        <div class="text-xs text-muted" style="max-width: 260px; line-height: 1.3; margin-top: 4px;">${escapeHtml(note)}</div>
      `;
    }

    const lastPrice = a.last ?? a.last_price;
    const atr = a.atr_14 ?? a.atr14 ?? a.atr;
    const stopPrice = a.stop_loss_price ?? a.stop_price;
    const investedAmount = a.invested_amount ?? a.allocated_capital ?? 0;
    const weightPct = a.portfolio_weight_pct ?? a.weight_pct ?? 0;
    const secWeight = a.sector_exposure_pct ?? sectorMap[a.sector] ?? 0;

    return `
      <tr>
        <td><strong class="font-mono text-primary cursor-pointer" onclick="jumpToDossier('${escapeHtml(a.symbol)}')">${escapeHtml(a.symbol)}</strong></td>
        <td class="text-muted">${escapeHtml(a.sector || '--')}</td>
        <td class="font-mono">$${lastPrice != null ? Number(lastPrice).toFixed(2) : '--'}</td>
        <td class="font-mono">$${atr != null ? Number(atr).toFixed(2) : '--'}</td>
        <td class="font-mono text-rose">$${stopPrice != null ? Number(stopPrice).toFixed(2) : '--'}</td>
        <td class="font-mono text-danger">-${a.stop_loss_pct != null ? Number(a.stop_loss_pct).toFixed(1) : '--'}%</td>
        <td class="font-mono"><strong>${shares}</strong> 股</td>
        <td class="font-mono text-emerald">$${Math.round(investedAmount).toLocaleString()}</td>
        <td class="font-mono">${Number(weightPct).toFixed(1)}%</td>
        <td class="font-mono">${Number(secWeight).toFixed(1)}%</td>
        <td>${statusBadge}</td>
      </tr>
    `;
  }).join("");
}

// ==============================================================================
// Top Nav Search & Autocomplete (Rule 2: 搜索放在顶栏，回车仍进档案)
// ==============================================================================
let topNavSuggestions = [];
let topNavSelectedIndex = -1;

function initTopNavSearch() {
  const form = document.getElementById("topNavSearchForm");
  const input = document.getElementById("topNavSymbolInput");
  const dropdown = document.getElementById("topNavAutocompleteDropdown");
  const btn = document.getElementById("topNavSearchBtn");

  if (!input) return;

  input.addEventListener("input", () => {
    const raw = input.value;
    const filtered = raw.replace(/[^a-zA-Z.]/g, "").toUpperCase();
    if (raw !== filtered) input.value = filtered;

    if (filtered) {
      renderTopNavDropdown(filtered);
    } else {
      if (dropdown) dropdown.style.display = "none";
    }
  });

  input.addEventListener("focus", () => {
    const val = input.value.trim();
    if (val) renderTopNavDropdown(val);
  });

  input.addEventListener("keydown", (e) => {
    if (!dropdown || dropdown.style.display === "none") {
      if (e.key === "Enter") {
        e.preventDefault();
        const val = input.value.trim();
        if (val) {
          executeTopNavSearch(val);
        }
      }
      return;
    }

    const items = dropdown.querySelectorAll(".top-nav-suggestion-item");
    if (!items.length) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      topNavSelectedIndex = (topNavSelectedIndex + 1) % items.length;
      updateTopNavHighlight(items);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      topNavSelectedIndex = (topNavSelectedIndex - 1 + items.length) % items.length;
      updateTopNavHighlight(items);
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (topNavSelectedIndex >= 0 && topNavSelectedIndex < topNavSuggestions.length) {
        executeTopNavSearch(topNavSuggestions[topNavSelectedIndex].symbol);
      } else {
        const val = input.value.trim();
        if (val) executeTopNavSearch(val);
      }
    } else if (e.key === "Escape") {
      dropdown.style.display = "none";
    }
  });

  if (form) {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const val = input.value.trim();
      if (val) executeTopNavSearch(val);
    });
  }

  if (btn) {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      const val = input.value.trim();
      if (val) executeTopNavSearch(val);
    });
  }

  document.addEventListener("click", (e) => {
    if (!e.target.closest(".top-nav-search-container") && dropdown) {
      dropdown.style.display = "none";
    }
  });
}

function renderTopNavDropdown(query) {
  const dropdown = document.getElementById("topNavAutocompleteDropdown");
  if (!dropdown) return;

  const q = query.toUpperCase();
  topNavSuggestions = US_STOCK_UNIVERSE.filter(item => {
    const sym = item.symbol.toUpperCase();
    const t = item.ticker.toUpperCase();
    const zh = (item.name_cn || "").toUpperCase();
    return sym.includes(q) || t.includes(q) || zh.includes(q);
  }).slice(0, 6);

  if (!topNavSuggestions.length) {
    dropdown.innerHTML = `
      <div class="top-nav-suggestion-item" onclick="executeTopNavSearch('${escapeHtml(q)}')">
        <span class="symbol-col font-mono text-primary">${escapeHtml(q)}</span>
        <span class="name-col text-muted">直接调阅美股代码档案 ➔</span>
      </div>
    `;
    dropdown.style.display = "block";
    topNavSelectedIndex = 0;
    return;
  }

  dropdown.innerHTML = topNavSuggestions.map((item, idx) => `
    <div class="top-nav-suggestion-item" data-idx="${idx}" onclick="executeTopNavSearch('${escapeHtml(item.symbol)}')">
      <span class="symbol-col font-mono text-primary font-bold">${escapeHtml(item.symbol)}</span>
      <span class="name-col">${escapeHtml(item.name_cn || item.name_en)}</span>
      <span class="sector-col text-muted">${escapeHtml(item.sector || "")}</span>
    </div>
  `).join("");

  dropdown.style.display = "block";
  topNavSelectedIndex = 0;
  updateTopNavHighlight(dropdown.querySelectorAll(".top-nav-suggestion-item"));
}

function updateTopNavHighlight(items) {
  items.forEach((item, idx) => {
    item.classList.toggle("selected", idx === topNavSelectedIndex);
  });
}

function executeTopNavSearch(symbol) {
  const dropdown = document.getElementById("topNavAutocompleteDropdown");
  if (dropdown) dropdown.style.display = "none";

  const norm = normalizeSymbol(symbol);
  // Switch to dossier section
  switchWorkbenchTab("dossierSection");
  loadDossier(norm);
}

// ==============================================================================
// Watchlist Management (Rule P1 9: 补上自选股)
// ==============================================================================
const WATCHLIST_STORAGE_KEY = "ai_screener_watchlist";

function showScreenerNotice(text) {
  const box = document.getElementById("screenerExceptionsBox");
  const el = document.getElementById("screenerExceptionsText");
  if (!box || !el || !text) return;
  box.style.display = "block";
  el.textContent = text;
}

function symbolInCurrentScan(symbol) {
  const data = state.dailyPicksData;
  if (!data) return false;
  const norm = normalizeSymbol(symbol);
  const rows = []
    .concat(data.picks || [])
    .concat(data.near_misses || [])
    .concat(data.culled_details || []);
  return rows.some(row => normalizeSymbol(row && row.symbol) === norm);
}

async function postWatchlist(path, symbol) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbol }),
  });
  const data = await res.json();
  if (!data.ok) {
    throw new Error(data.error || "自选同步失败");
  }
  return normalizeSymbol(data.symbol || symbol);
}

function readLocalWatchlist() {
  try {
    const raw = localStorage.getItem(WATCHLIST_STORAGE_KEY);
    if (!raw) return [];
    const arr = JSON.parse(raw);
    if (!Array.isArray(arr)) return [];
    return arr.map(item => normalizeSymbol(item)).filter(Boolean);
  } catch (err) {
    return [];
  }
}

async function loadWatchlist() {
  const local = readLocalWatchlist();
  let server = [];
  let serverOk = false;
  try {
    const res = await fetch("/api/watchlist");
    const data = await res.json();
    if (data.ok && Array.isArray(data.watchlist)) {
      serverOk = true;
      server = data.watchlist.map(item => normalizeSymbol(item.symbol || item)).filter(Boolean);
    }
  } catch (err) {
    serverOk = false;
  }

  state.watchlistSymbols = new Set(server.concat(local));
  if (serverOk) {
    const serverSet = new Set(server);
    for (const sym of local) {
      if (serverSet.has(sym)) continue;
      try {
        const saved = await postWatchlist("/api/watchlist/add", sym);
        if (saved) {
          state.watchlistSymbols.delete(sym);
          state.watchlistSymbols.add(saved);
          serverSet.add(saved);
        }
      } catch (err) {
        state.watchlistSymbols.delete(sym);
        showScreenerNotice(err.message || `${sym} 没能加入服务端自选`);
      }
    }
  } else if (local.length) {
    showScreenerNotice("自选列表没有同步到服务端，本次扫描仍只有默认股票池。");
  }
  saveWatchlist();
}

function saveWatchlist() {
  try {
    const arr = Array.from(state.watchlistSymbols);
    localStorage.setItem(WATCHLIST_STORAGE_KEY, JSON.stringify(arr));
  } catch (e) {}
  updateWatchlistBadges();
}

function updateWatchlistBadges() {
  const watchCountEl = document.getElementById("screenerWatchlistCount");
  if (watchCountEl && state.watchlistSymbols) {
    watchCountEl.textContent = state.watchlistSymbols.size;
  }

  // Update dossier header watchlist button if active
  const btnDossier = document.getElementById("btnDossierWatchlist");
  const icon = document.getElementById("dossierWatchlistIcon");
  const text = document.getElementById("dossierWatchlistText");
  if (btnDossier && state.currentSymbol) {
    const currentNorm = normalizeSymbol(state.currentSymbol);
    const isWatched = state.watchlistSymbols && (state.watchlistSymbols.has(state.currentSymbol) || state.watchlistSymbols.has(currentNorm));
    btnDossier.classList.toggle("active", isWatched);
    if (icon) icon.textContent = isWatched ? "★" : "☆";
    if (text) text.textContent = isWatched ? "已在自选" : "加入自选";
  }
}

function paintWatchButton(btnEl, watched) {
  if (!btnEl) return;
  btnEl.classList.toggle("active", watched);
  if (btnEl.classList.contains("btn-card-watchlist")) {
    btnEl.textContent = watched ? "★ 已自选" : "☆ 加自选";
  } else if (btnEl.classList.contains("btn-table-watchlist")) {
    btnEl.textContent = watched ? "★" : "☆";
  }
}

async function syncWatchlistChange(sym, wasWatched) {
  const saved = await postWatchlist(wasWatched ? "/api/watchlist/remove" : "/api/watchlist/add", sym);
  const finalSym = saved || sym;
  if (!wasWatched && finalSym !== sym) {
    state.watchlistSymbols.delete(sym);
    state.watchlistSymbols.add(finalSym);
    saveWatchlist();
  }
  if (!symbolInCurrentScan(finalSym)) {
    loadScreenerTab(true);
  } else if (state.screenerFilter === "watchlist" && state.dailyPicksData) {
    renderDailyPicks(state.dailyPicksData);
  }
  return finalSym;
}

async function toggleWatchlist(rawSymbol, btnEl) {
  if (!rawSymbol) return;
  const sym = normalizeSymbol(rawSymbol);
  if (!sym) return;
  if (!state.watchlistSymbols) state.watchlistSymbols = new Set();

  const wasWatched = state.watchlistSymbols.has(sym);
  if (wasWatched) state.watchlistSymbols.delete(sym);
  else state.watchlistSymbols.add(sym);
  saveWatchlist();
  paintWatchButton(btnEl, !wasWatched);

  try {
    await syncWatchlistChange(sym, wasWatched);
  } catch (err) {
    if (wasWatched) state.watchlistSymbols.add(sym);
    else state.watchlistSymbols.delete(sym);
    saveWatchlist();
    paintWatchButton(btnEl, wasWatched);
    showScreenerNotice(err.message || "自选同步失败");
    if (state.dailyPicksData) renderDailyPicks(state.dailyPicksData);
  }
}

// Global exposure for inline onclick handlers
window.onToggleWatchlist = function(symbol, btnEl) {
  toggleWatchlist(symbol, btnEl);
};

function initWatchlistListeners() {
  const btnDossier = document.getElementById("btnDossierWatchlist");
  if (btnDossier) {
    btnDossier.addEventListener("click", () => {
      if (state.currentSymbol) {
        toggleWatchlist(state.currentSymbol, btnDossier);
      }
    });
  }

  // Screener filter tabs (All vs Watchlist)
  const btnAll = document.getElementById("btnFilterAllPool");
  const btnWatch = document.getElementById("btnFilterWatchlist");
  if (btnAll) {
    btnAll.addEventListener("click", () => {
      state.screenerFilter = "all";
      btnAll.classList.add("active");
      if (btnWatch) btnWatch.classList.remove("active");
      if (state.dailyPicksData) renderDailyPicks(state.dailyPicksData);
    });
  }
  if (btnWatch) {
    btnWatch.addEventListener("click", () => {
      state.screenerFilter = "watchlist";
      btnWatch.classList.add("active");
      if (btnAll) btnAll.classList.remove("active");
      if (state.dailyPicksData) renderDailyPicks(state.dailyPicksData);
    });
  }

  // Quick add to watchlist
  const quickInput = document.getElementById("quickAddWatchlistInput");
  const btnQuickAdd = document.getElementById("btnQuickAddWatchlist");
  if (btnQuickAdd && quickInput) {
    const doAdd = async () => {
      const raw = quickInput.value.trim();
      if (!raw) return;
      const sym = normalizeSymbol(raw);
      if (!sym) return;
      quickInput.value = "";
      if (!state.watchlistSymbols) state.watchlistSymbols = new Set();
      if (state.watchlistSymbols.has(sym)) return;
      state.watchlistSymbols.add(sym);
      saveWatchlist();
      if (state.dailyPicksData) renderDailyPicks(state.dailyPicksData);
      try {
        await syncWatchlistChange(sym, false);
      } catch (err) {
        state.watchlistSymbols.delete(sym);
        saveWatchlist();
        showScreenerNotice(err.message || "加入自选失败");
        if (state.dailyPicksData) renderDailyPicks(state.dailyPicksData);
      }
    };
    btnQuickAdd.addEventListener("click", doAdd);
    quickInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        doAdd();
      }
    });
  }
}

// ==============================================================================
// Multi-Stock Compare Floating Tray (Rule P1 11: 最多5只标的勾选快速横向对比)
// ==============================================================================
function onToggleCompareSymbol(symbol, isChecked) {
  const sym = normalizeSymbol(symbol);
  if (!state.selectedCompareSymbols) state.selectedCompareSymbols = [];

  if (isChecked) {
    if (state.selectedCompareSymbols.length >= 5) {
      alert("最多支持勾选 5 只标的进行横向对比！");
      // Uncheck the checkbox
      const boxes = document.querySelectorAll(`.compare-checkbox[data-symbol="${sym}"]`);
      boxes.forEach(b => b.checked = false);
      return;
    }
    if (!state.selectedCompareSymbols.includes(sym)) {
      state.selectedCompareSymbols.push(sym);
    }
  } else {
    state.selectedCompareSymbols = state.selectedCompareSymbols.filter(s => s !== sym);
  }

  // Synchronize any duplicate checkboxes for this symbol
  const boxes = document.querySelectorAll(`.compare-checkbox[data-symbol="${sym}"]`);
  boxes.forEach(b => b.checked = isChecked);

  renderCompareFloatingTray();
}
window.onToggleCompareSymbol = onToggleCompareSymbol;

function renderCompareFloatingTray() {
  const tray = document.getElementById("compareFloatingTray");
  const countEl = document.getElementById("traySelectedCount");
  const pillsEl = document.getElementById("traySelectedPills");
  const btnLaunch = document.getElementById("btnLaunchCompare");
  const btnClear = document.getElementById("btnClearCompare");

  if (!tray) return;

  const list = state.selectedCompareSymbols || [];
  if (list.length === 0) {
    tray.style.display = "none";
    return;
  }

  tray.style.display = "block";
  if (countEl) countEl.textContent = list.length;
  if (pillsEl) {
    pillsEl.innerHTML = list.map(sym => `
      <span class="tray-chip">
        ${escapeHtml(sym)}
        <button type="button" class="tray-chip-del" onclick="removeCompareSymbol('${escapeHtml(sym)}')">×</button>
      </span>
    `).join("");
  }

  if (btnClear) {
    btnClear.onclick = () => {
      state.selectedCompareSymbols = [];
      document.querySelectorAll(".compare-checkbox").forEach(b => b.checked = false);
      renderCompareFloatingTray();
    };
  }

  if (btnLaunch) {
    btnLaunch.onclick = () => {
      if (!state.selectedCompareSymbols || state.selectedCompareSymbols.length < 2) {
        alert("请至少勾选 2 只标的进行对比！");
        return;
      }
      const syms = state.selectedCompareSymbols.join(", ");
      const compareInput = document.getElementById("compareSymbolsInput");
      if (compareInput) compareInput.value = syms;
      switchWorkbenchTab("compareSection");
      runMultiCompare(syms);
    };
  }
}

window.removeCompareSymbol = function(symbol) {
  onToggleCompareSymbol(symbol, false);
};

// ==============================================================================
// Existing Holdings Health Check (Rule P2 15: 表 2 现有持仓风控自查)
// ==============================================================================
function initHoldingsListeners() {
  const btnAdd = document.getElementById("btnAddHoldingRow");
  const btnInspect = document.getElementById("btnInspectHoldings");

  if (btnAdd) {
    btnAdd.addEventListener("click", () => addHoldingRow("", 100));
  }
  if (btnInspect) {
    btnInspect.addEventListener("click", inspectExistingHoldings);
  }

  // Render initial holdings rows
  renderHoldingsRows();
}

function renderHoldingsRows() {
  const tbody = document.getElementById("holdingsTableBody");
  if (!tbody) return;

  const holdings = state.existingHoldings || [
    { symbol: "NVDA.US", shares: 100 },
    { symbol: "AAPL.US", shares: 120 },
    { symbol: "MSFT.US", shares: 80 }
  ];

  tbody.innerHTML = "";
  holdings.forEach((h, idx) => {
    appendHoldingRowDOM(h.symbol, h.shares, idx);
  });
}

function addHoldingRow(symbol = "", shares = 100) {
  const tbody = document.getElementById("holdingsTableBody");
  if (!tbody) return;
  const idx = tbody.children.length;
  appendHoldingRowDOM(symbol, shares, idx);
}

function appendHoldingRowDOM(symbol, shares, idx) {
  const tbody = document.getElementById("holdingsTableBody");
  if (!tbody) return;

  const tr = document.createElement("tr");
  tr.className = "holding-row";
  tr.dataset.idx = idx;
  tr.innerHTML = `
    <td>
      <input type="text" class="holding-input holding-sym" value="${escapeHtml(symbol)}" placeholder="代码如 NVDA.US" onchange="onHoldingInputChange(this)" />
    </td>
    <td>
      <input type="number" class="holding-input holding-shares" value="${shares}" min="1" step="10" onchange="onHoldingInputChange(this)" />
    </td>
    <td class="font-mono holding-price">--</td>
    <td class="font-mono holding-val">--</td>
    <td class="holding-sector text-muted">--</td>
    <td class="font-mono holding-sec-pct">--</td>
    <td class="font-mono holding-stop text-rose">--</td>
    <td class="font-mono holding-dist">--</td>
    <td class="holding-status"><span class="health-pill neutral">待体检</span></td>
    <td>
      <button type="button" class="btn-action-delete" title="删除持仓行" onclick="this.closest('tr').remove(); saveHoldingsFromDOM();">🗑️</button>
    </td>
  `;
  tbody.appendChild(tr);
}

window.onHoldingInputChange = function(input) {
  saveHoldingsFromDOM();
};

function saveHoldingsFromDOM() {
  const tbody = document.getElementById("holdingsTableBody");
  if (!tbody) return;

  const list = [];
  tbody.querySelectorAll(".holding-row").forEach(tr => {
    const symInput = tr.querySelector(".holding-sym");
    const sharesInput = tr.querySelector(".holding-shares");
    const sym = (symInput ? symInput.value : "").trim().toUpperCase();
    const shares = sharesInput ? parseFloat(sharesInput.value) || 0 : 0;
    if (sym && shares > 0) {
      list.push({ symbol: normalizeSymbol(sym), shares });
    }
  });
  state.existingHoldings = list;
}

async function inspectExistingHoldings() {
  saveHoldingsFromDOM();
  const holdings = state.existingHoldings;
  if (!holdings || holdings.length === 0) {
    alert("请至少填入一只持仓股票代码与持有股数！");
    return;
  }

  const btn = document.getElementById("btnInspectHoldings");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "体检诊断中...";
  }

  try {
    const res = await fetch("/api/portfolio/inspect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ holdings })
    });
    const data = await res.json();
    if (!data.ok || !Array.isArray(data.report)) {
      alert("持仓体检失败: " + (data.error || "未知异常"));
      return;
    }

    // Render report onto rows
    const tbody = document.getElementById("holdingsTableBody");
    const rows = tbody.querySelectorAll(".holding-row");
    const report = data.report;

    report.forEach((rep, idx) => {
      const tr = rows[idx];
      if (!tr) return;

      const pCell = tr.querySelector(".holding-price");
      const vCell = tr.querySelector(".holding-val");
      const sCell = tr.querySelector(".holding-sector");
      const secPctCell = tr.querySelector(".holding-sec-pct");
      const stopCell = tr.querySelector(".holding-stop");
      const distCell = tr.querySelector(".holding-dist");
      const stCell = tr.querySelector(".holding-status");

      if (pCell) pCell.textContent = rep.price != null ? `$${Number(rep.price).toFixed(2)}` : "--";
      if (vCell) vCell.textContent = rep.market_value != null ? `$${Math.round(rep.market_value).toLocaleString()}` : "--";
      if (sCell) sCell.textContent = rep.sector || "--";
      if (secPctCell) secPctCell.textContent = rep.sector_weight_pct != null ? `${Number(rep.sector_weight_pct).toFixed(1)}%` : "--";
      if (stopCell) stopCell.textContent = rep.stop_loss_2atr != null ? `$${Number(rep.stop_loss_2atr).toFixed(2)}` : "--";

      if (distCell) {
        if (rep.dist_to_stop_pct != null) {
          const d = Number(rep.dist_to_stop_pct);
          distCell.textContent = `${d >= 0 ? '+' : ''}${d.toFixed(1)}%`;
          distCell.className = `font-mono holding-dist ${d >= 0 ? 'text-success' : 'text-danger font-bold'}`;
        } else {
          distCell.textContent = "--";
          distCell.className = "font-mono holding-dist text-muted";
        }
      }

      if (stCell) {
        if (rep.is_broken_stop) {
          stCell.innerHTML = `<span class="health-pill danger" title="价格跌破 2xATR 止损价，建议纪律减仓">⚠️ 破 2xATR 止损</span>`;
        } else if (rep.is_sector_overweight) {
          stCell.innerHTML = `<span class="health-pill warning" title="所属行业敞口超过 30% 风控红线">⚠️ 行业超 30%</span>`;
        } else {
          stCell.innerHTML = `<span class="health-pill ok">✅ 止损上方健康</span>`;
        }
      }
    });

  } catch (err) {
    alert("体检请求异常: " + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "运行持仓体检";
    }
  }
}


