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
- **零构建工具**：基于 Python 标准库与原生 HTML/JS/CSS，打开即用。

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
