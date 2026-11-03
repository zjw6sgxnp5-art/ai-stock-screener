# AI 选股本地投研工作台

> **数据与能力声明**：行情与单期财报来自长桥，产品笔记为人工整理，分数是规则分，未经历史胜率验证。

本项目是一个本地美股量化与基本面投研工作台原型：

- **数据事实层**：本地调用长桥 CLI 获取实时行情、日 K 线、最新单期财报、同业相对倍数、做空持仓与内部人交易；长桥离线时降级为 Yahoo 真实日K与价格，不编造虚假财务。
- **量化规则层**：计算均线、20日动量、年化波动、真实 14 日 ATR 及 2×ATR 动态跟踪止损防线；消息催化作为展示项不入综合分。
- **个股深度档案**：默认展示估值与财务实数、日 K 均线与止损走势图、白话技术罗盘、资产负债杜邦拆解；商业模式与核心产品笔记作为专题附录（明确标注人工整理或简介原文，非官方审计财报）。
- **智能选股**：每日候选池（22 只核心标的 ∪ 自选股），经过趋势闸门与规则综合分截断输出 Top 6、接近入选与淘汰明细表。
- **组合风控体检**：提供 Top 6 理论试算模拟，以及现有持仓的 2×ATR 止损线与 30% 行业集中度硬上限健康检查。
- **量化动量实验**：滑动窗口回测动量与 2×ATR 止损规则（明确标注为动量实验，不验证每日多因子）。
- **备忘录可选**：支持调用本地 Gemini CLI 或 Grok CLI 生成买方投资审议备忘录；未配置时如实显示“待人工复核”，绝不使用模板造假兜底。
- **权威投研文库（双库·518标的）**：集成外部机构全景投研库（标普500+纳指100，共 518 只标的，带 30 分制六维质地量化评分与 518 篇 Markdown 深度研报全文）与自研标普500买方避雷库（506 期专研，含四级避雷评级、错杀识别与独家证伪防线）。支持数据源 Tab 自由切换与多维筛选。
- **个股档案双重视角对照（方案 A）**：个股档案顶部实时切换“外部机构全景研判”与“我的买方避雷研判”。针对 15 只纳指 100 非标普成分股，自动置灰禁用买方避雷切换（点不动），并提供悬停/点击浮动气泡提示。
- **零构建工具**：基于 Python 标准库与原生 HTML/JS/CSS，打开即用。

详细设计与实现细节请查阅技术文档：[权威投研文库与双库交叉研判系统设计文档](docs/RESEARCH_LIBRARY_DESIGN.md)。

## 数据源模式与诚实机制说明

系统遵循**「买方诚信、绝不编造假数据」**原则，区分两种运行状态：

- **完整模式（长桥在线，推荐）**：终端执行 `longbridge auth login` 后，系统获取长桥官方实时行情、日 K 线、最新单期财报（营收同比/净利润率/现金流）、同业估值倍数、做空比例与内部人交易，自动运行完整多因子评分并生成每日选股 Top 6 优选名单。
- **降级模式（仅 Yahoo 在线）**：长桥离线或凭证过期时，系统自动调用 Yahoo Finance 接口获取真实日 K 与现价，确保 K 线走势图、均线与 2×ATR 止损线正常渲染。**因缺失官方审计财报与做空数据，系统不合成虚构评分**，标的状态如实显示为「数据不足，不能评级」，此时每日选股 Top 6 榜单为空。如需执行多因子选股，请先在终端登录长桥。

## 安全与防护机制

- **同源与 CSRF 拦截**：系统仅允许来自 `localhost` 和 `127.0.0.1` 的合法本地请求；对任意公网跨域请求（如恶意网页发起的跨域调用）实施严格拦截，杜绝恶意网站篡改自选股或删除档案。
- **本地回路绑定**：服务默认监听 `127.0.0.1`（Docker 镜像同理绑定 `127.0.0.1:8765`），不暴露局域网端口。
- **输入过滤**：全量 API 接入标的代码正则表达式校验（严格限定字母、数字及 `. - ^`），阻断注入与非法路径。
- **研报资料保密确认**：`【1】参考资料/` 目录收录 518 份机构研报与 506 份标普专研，若用于公开仓库，请确保已取得资料方分享或公开授权。

## 前置条件

1. 安装并登录长桥 CLI (提供实时真实行情与单期财报)：

```bash
longbridge auth login
```

2. 可选：配置 Gemini 或 Grok CLI 凭证：

```bash
# Gemini CLI 登录或配置 GEMINI_API_KEY
gemini auth login
# 或 Grok CLI 配置 GROK_API_KEY
export GROK_API_KEY="你的 Grok API Key"
```

如果不配置大模型，系统仍跑长桥事实层与量化指标，备忘录区域提示“未配置大模型，待人工复核”。非预置标的只复述公司简介和单期营收同比，缺现金流时不写成经营结论。预置库 18 只仍是人工笔记。

## 启动

```bash
python3 app.py
```

然后打开：

```text
http://localhost:8765
```

## Docker 启动

也可以直接双击 `启动Docker.command`，或在当前目录运行：

```bash
docker compose up -d --build
```

Docker 版默认访问 `http://localhost:8765`，并会把本机 `data/`、`reports/` 目录挂载到容器中持久化数据。长桥认证读取电脑上的 `~/.longbridge`，首次使用前请先在电脑终端完成：

```bash
longbridge auth login
```

如果 8765 端口被占用，可以临时换端口：

```bash
AI_STOCK_HOST_PORT=8766 ./启动Docker.command
```

## 示例股票代码

```text
AAPL.US
MSFT.US
NVDA.US
TSLA.US
QQQ.US
```

## 常用接口

```text
GET  /api/universe/stocks
GET  /api/research/list?source=benchmark&page=1&page_size=12
GET  /api/research/detail?symbol=AAPL.US
GET  /api/research/report?symbol=AAPL.US
GET  /api/analyze?symbol=NVDA.US&extra=1
GET  /api/screener/run?symbols=NVDA.US,MSFT.US,AAPL.US&limit=3
GET  /api/screener/run?universe=watchlist&limit=5
GET  /api/compare?symbols=NVDA.US,MSFT.US,AAPL.US
GET  /api/watchlist
POST /api/watchlist/add
GET  /api/history?limit=10
GET  /api/report/export?symbol=NVDA.US
```

导出的 Markdown 报告保存在 `reports/` 目录。

`/api/analyze` 会返回 `score.score_formula` 和 `score.factor_breakdown`，前端会展示基础分、多因子分、风险惩罚、每个因子的权重/贡献和证据。

## 说明

本工具仅用于研究参考，不构成投资建议。
