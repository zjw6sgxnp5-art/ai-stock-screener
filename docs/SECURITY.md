# 安全说明（SECURITY）

本项目是**本地单用户**投研工作台，默认只监听 `127.0.0.1`。以下为当前的安全机制与配置方法。

## 1. 跨域与 CSRF / DNS rebinding

| 机制 | 说明 |
| --- | --- |
| CORS | 不再返回 `*`。仅当 `Origin` 与请求 `Host` 同源，或在白名单 `AI_STOCK_ALLOWED_ORIGINS` 中时，才回写 `Access-Control-Allow-Origin`。 |
| 写操作校验 | 所有 POST 若带 `Origin` / `Referer`，必须同源或在白名单内，否则 403。`Origin: null`、`file://`、本机其他端口（如 `http://localhost:3000`）都**不再**视为可信。 |
| Host 校验 | 所有请求的 `Host` 必须是 `localhost` / `127.0.0.1` / `::1` 或 `AI_STOCK_ALLOWED_HOSTS` 中的名字，否则 403，防 DNS rebinding。 |
| 可选 API token | 设置 `AI_STOCK_API_TOKEN` 后，**不带 Origin/Referer 的写请求**（curl、脚本）必须带 `X-API-Token: <token>` 或 `Authorization: Bearer <token>`，否则 401。浏览器内同源前端不受影响。 |

### 环境变量

```bash
# 局域网其他设备访问（例：本机 IP 192.168.1.5，端口 8765）
export AI_STOCK_HOST=0.0.0.0
export AI_STOCK_ALLOWED_HOSTS=192.168.1.5
export AI_STOCK_ALLOWED_ORIGINS=http://192.168.1.5:8765   # 多个用逗号分隔

# 脚本写操作需要 token
export AI_STOCK_API_TOKEN=$(python3 -c 'import secrets;print(secrets.token_urlsafe(24))')
curl -X POST -H "X-API-Token: $AI_STOCK_API_TOKEN" -H 'Content-Type: application/json' \
     -d '{"symbol":"AAPL"}' http://127.0.0.1:8765/api/watchlist/add
```

> 注意：开放到局域网后，同网段任何人都能**读**接口数据、也能用浏览器以同源方式写；如需对局域网开放，建议再加反向代理认证。

## 2. 股票代码校验

单个 `symbol`（查询参数或 JSON）及批量 `symbols` 只允许 `A-Z 0-9 . - ^`、最长 20 位（大小写不敏感，自动补 `.US`）。非法值返回 **400**，不再静默替换成默认标的。

## 3. Docker

- 端口只绑定宿主机 `127.0.0.1`。
- 长桥 CLI 固定版本 `v0.31.0`，从官方 GitHub Release 下载并用官方 `.sha256` 校验（不再 `curl | sh`）。升级时同时修改 Dockerfile 中的 `LONGBRIDGE_VERSION` 和两个 `LONGBRIDGE_SHA256_*` ARG，校验和取自 `https://github.com/longbridge/longbridge-terminal/releases`。
- `~/.longbridge` **以可写方式**挂载：长桥 CLI 会自动刷新 OAuth token 并写入 `~/.longbridge/openapi/tokens/<client_id>`，只读挂载会导致 token 过期后无法续期。代价是容器可修改宿主机上的长桥凭证，请仅在受信任镜像中使用；不需要实时行情可注释该挂载行。

## 4. TLS 证书校验

- `backend/services/market_data.py` 的 Yahoo 请求已改为 `ssl.create_default_context()`（校验证书）。
- **已知遗留**：`backend/services/backtester.py` 仍使用 `ssl._create_unverified_context()`（关闭证书校验，存在中间人篡改行情风险）。该文件正由回测分支重写，届时应一并改为 `ssl.create_default_context()`。

## 5. 其他提示

- 研报资料（`【1】参考资料/`）位于公开仓库，请确认版权许可。
- 写接口没有用户体系，安全边界依赖“只监听本机 + 同源校验 + 可选 token”。
