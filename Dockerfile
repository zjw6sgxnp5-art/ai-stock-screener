FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && curl -sSL https://open.longbridge.cn/longbridge/longbridge-terminal/install | sh

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ./
COPY backend ./backend
COPY web ./web

RUN mkdir -p /app/data /app/reports

ENV PYTHONUNBUFFERED=1 \
    AI_STOCK_HOST=0.0.0.0 \
    AI_STOCK_PORT=8765 \
    LONG_BRIDGE_BIN=longbridge

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=5s --retries=5 --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/health', timeout=4).read()" || exit 1

CMD ["python", "app.py"]
