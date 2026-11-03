FROM python:3.12-slim

WORKDIR /app

# Longbridge CLI: pinned version + SHA-256 verified (no `curl | sh`).
# Checksums come from the official GitHub release assets (*.tar.gz.sha256) of
# https://github.com/longbridge/longbridge-terminal/releases/tag/v0.31.0 and match the
# assets.lbkrs.com CDN copy. To upgrade: bump LONGBRIDGE_VERSION and both SHA256 args together.
ARG LONGBRIDGE_VERSION=v0.31.0
ARG LONGBRIDGE_SHA256_AMD64=3d2b3dd19c4c00015eb0a80733f7ecb06187e1956230e700a3072152e0399f73
ARG LONGBRIDGE_SHA256_ARM64=3f30be43f2a1e7352ce5d54ac46f0eafe4028ca6fa9ef16ce9dcbe2ff41c146c

RUN set -eu \
    && apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && case "$(uname -m)" in \
         x86_64) arch=amd64; sha="$LONGBRIDGE_SHA256_AMD64" ;; \
         aarch64|arm64) arch=arm64; sha="$LONGBRIDGE_SHA256_ARM64" ;; \
         *) echo "unsupported arch $(uname -m)" >&2; exit 1 ;; \
       esac \
    && pkg="longbridge-terminal-linux-musl-${arch}.tar.gz" \
    && curl -fsSLo "/tmp/${pkg}" "https://github.com/longbridge/longbridge-terminal/releases/download/${LONGBRIDGE_VERSION}/${pkg}" \
    && echo "${sha}  /tmp/${pkg}" | sha256sum -c - \
    && tar xzf "/tmp/${pkg}" -C /usr/local/bin longbridge \
    && chmod 0755 /usr/local/bin/longbridge \
    && rm -f "/tmp/${pkg}"

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
