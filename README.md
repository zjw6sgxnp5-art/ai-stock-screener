# AI 选股本地原型

本项目是一个本地股票分析软件原型，第一版以美股为主：

- 本地调用长桥 CLI 获取行情、K 线、新闻等数据。
- 本地计算技术指标、动量、波动、消息热度、财务质量、估值画像和风险评分。
- 单股全景支持公司概览、估值评级、财务快照、公告、关联股票、管理层治理、内部人交易、做空、历史争议和事件时间线。
- 智能选股支持用户输入股票池，输出 Top N、标签、入选理由和风险。
- 多股对比支持 2-5 只股票快速横向比较评分、动量、PE、评级、成交额和风险。
- 支持自选股、分析历史归档、Markdown 报告导出。
- 前端是高密度投研工作台：左侧导航、顶部命令条、紧凑 KPI、评分公式、因子贡献、表格化选股和可展开分析依据。
- 可选调用 OpenAI API 生成中文全景研判。
- 浏览器访问本地页面，不需要前端构建工具。

## 前置条件

1. 安装并登录长桥 CLI。

```bash
longbridge auth login
```

2. 可选：配置 OpenAI API Key。

```bash
export OPENAI_API_KEY="你的 API Key"
```

如果不配置，系统仍可展示行情、K 线、新闻和本地规则评分，只是不生成 GPT 综合研判。

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
