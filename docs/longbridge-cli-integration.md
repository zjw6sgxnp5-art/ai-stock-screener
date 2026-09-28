# 长桥 CLI 数据接入方案

**状态**: Draft v0.1  
**日期**: 2026-05-17  
**目标**: 第一版优先封装本机 `longbridge` CLI，快速构建本地股票分析软件的数据层。

## 1. 基本原则

- 所有 CLI 调用优先使用 `--format json`。
- 后端统一封装 CLI，不让前端直接调用命令。
- 每次请求记录 `source=longbridge_cli`、`command`、`fetched_at`、`symbol`、`status`。
- CLI 报错需要转换成用户可读中文提示。
- 所有结果先缓存到 SQLite，避免频繁请求和重复分析。
- 未登录时给出明确提示：运行 `longbridge auth login`。

## 2. 环境检测

启动后端时检查：

```bash
command -v longbridge
longbridge check --format json
```

如果未安装：

- 页面提示未检测到长桥 CLI。
- 提供安装/配置说明。

如果未登录：

- 页面提示“长桥 CLI 未登录”。
- 给出命令：`longbridge auth login`。

## 3. 单股全景数据映射

| 分析模块 | CLI 命令 | 用途 |
|---|---|---|
| 实时行情 | `longbridge quote <SYMBOL> --format json` | 最新价、涨跌幅、成交量、盘前盘后 |
| 历史 K 线 | `longbridge kline <SYMBOL> --period day --count 260 --format json` | 均线、涨跌幅、波动率、RSI/MACD |
| 分时行情 | `longbridge intraday <SYMBOL> --format json` | 当日走势和成交变化 |
| 公司概览 | `longbridge company <SYMBOL> --format json` | 公司名称、行业、IPO、员工等 |
| 新闻列表 | `longbridge news <SYMBOL> --count 20 --format json` | 最新消息、热度、评论数 |
| 新闻详情 | `longbridge news detail <ID>` | 文章全文，用于 AI 摘要 |
| 公告/监管文件 | `longbridge filing <SYMBOL> --count 20 --format json` | SEC/HKEX 等文件列表 |
| 公告详情 | `longbridge filing detail <SYMBOL> <ID>` | 文件全文，用于 AI 摘要 |
| 财务报表 | `longbridge financial-report <SYMBOL> --kind ALL --format json` | 利润表、资产负债表、现金流 |
| 估值 | `longbridge valuation <SYMBOL> --format json` | PE/PB/PS/股息率、同业对比 |
| 估值历史 | `longbridge valuation <SYMBOL> --history --indicator pe --range 5 --format json` | 估值分位与历史位置 |
| 机构评级 | `longbridge institution-rating <SYMBOL> --format json` | 评级分布、平均目标价 |
| 评级历史 | `longbridge institution-rating <SYMBOL> --history --format json` | 评级和目标价变化 |
| 资金分布 | `longbridge capital <SYMBOL> --format json` | 资金分布快照 |
| 资金流 | `longbridge capital <SYMBOL> --flow --format json` | 盘中资金流曲线 |
| 分红 | `longbridge dividend <SYMBOL> --format json` | 分红历史 |
| 公司行动 | `longbridge corp-action <SYMBOL> --format json` | 拆股、配股、分红等 |
| 做空数据 | `longbridge short-positions <SYMBOL> --format json` | 美股做空兴趣和风险观察 |
| 内部人交易 | `longbridge insider-trades <SYMBOL> --format json` | SEC Form 4 内部人交易 |
| 基金持仓 | `longbridge fund-holder <SYMBOL> --format json` | 持有该股的基金/ETF |

## 4. 智能选股数据映射

| 选股因子 | CLI 命令 | 说明 |
|---|---|---|
| 价格动量 | `quote`、`kline` | 5/20/60 日涨跌幅、相对强弱 |
| 成交活跃度 | `quote`、`kline` | 成交量、成交额、量价配合 |
| 异动 | `anomaly --market US/HK --count 100` | 市场异动候选池 |
| 资金面 | `capital` | 资金流入流出和大单分布 |
| 消息热度 | `news` | 新闻数量、发布时间、评论/点赞 |
| 财报催化 | `finance-calendar report` | 即将发布或刚发布财报 |
| 分红/拆股 | `finance-calendar dividend/split` | 公司行动催化 |
| 宏观事件 | `finance-calendar macrodata --star 3` | 高重要性宏观事件 |
| 估值 | `valuation` | 当前估值、同业对比、历史分位 |
| 评级变化 | `institution-rating --history` | 目标价和评级变化 |
| 做空风险 | `short-positions` | 空头拥挤或挤空风险 |
| 内部人信号 | `insider-trades` | 管理层买卖行为 |

## 5. 建议的缓存策略

| 数据类型 | TTL | 理由 |
|---|---:|---|
| 实时行情 | 15-60 秒 | 页面刷新频繁，但不做高频交易 |
| 分时行情 | 1-5 分钟 | 日内走势需要较新 |
| K 线 | 1 小时，收盘后刷新 | 日线不需要秒级 |
| 新闻列表 | 5-15 分钟 | 消息面需要较快更新 |
| 新闻详情 | 7 天或永久 | 文章内容通常不变 |
| 公告列表 | 30-60 分钟 | 公告频率较低 |
| 公告详情 | 永久 | 文件内容不变 |
| 财务报表 | 1 天 | 财报低频变化 |
| 估值 | 1-6 小时 | 随价格变化但不必秒级 |
| 评级 | 1 天 | 评级低频变化 |
| 日历 | 1-6 小时 | 事件日历中频变化 |

## 6. 后端接口草案

```text
GET /api/health
GET /api/datasources/longbridge/status
GET /api/stocks/{symbol}/quote
GET /api/stocks/{symbol}/klines?period=day&count=260
GET /api/stocks/{symbol}/news?count=20
GET /api/stocks/{symbol}/filings?count=20
GET /api/stocks/{symbol}/financials
GET /api/stocks/{symbol}/valuation
GET /api/stocks/{symbol}/ratings
GET /api/stocks/{symbol}/analysis
POST /api/screener/run
GET /api/screener/results/{run_id}
```

## 7. 错误处理

| CLI 情况 | 用户提示 |
|---|---|
| `command not found` | 未检测到长桥 CLI，请先安装并配置。 |
| `Not authenticated` | 长桥 CLI 未登录，请在终端运行 `longbridge auth login`。 |
| 权限不足 | 当前账号没有该市场或该数据的权限，请检查长桥行情/数据权限。 |
| symbol 格式错误 | 股票代码格式应为 `<代码>.<市场>`，例如 `AAPL.US`、`700.HK`。 |
| 网络超时 | 长桥服务请求超时，请稍后重试。 |
| JSON 解析失败 | 数据源返回格式异常，系统已记录原始响应用于排查。 |

## 8. 第一版实现顺序

1. 实现 CLI 执行器：超时、JSON 解析、stderr 错误映射。
2. 实现数据源状态检查。
3. 实现 `quote` 和 `kline`。
4. 实现技术指标计算。
5. 实现 `news`、`filing`、`financial-report`、`valuation`。
6. 实现单股全景分析接口。
7. 实现自选股批量评分。
8. 实现异动候选池和智能选股 Top N。

