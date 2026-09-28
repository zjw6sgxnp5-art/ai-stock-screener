#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

HOST_PORT="${AI_STOCK_HOST_PORT:-8765}"
CONTAINER_NAME="ai-stock-local"
APP_URL="http://127.0.0.1:${HOST_PORT}"

log() {
  printf "\n[%s] %s\n" "$(date '+%H:%M:%S')" "$*"
}

need_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "缺少命令: $1"
    exit 1
  fi
}

ensure_docker() {
  need_command docker
  if docker info >/dev/null 2>&1; then
    return
  fi

  log "Docker 还没启动，正在尝试打开 Docker Desktop..."
  open -a Docker >/dev/null 2>&1 || true
  for _ in $(seq 1 90); do
    if docker info >/dev/null 2>&1; then
      log "Docker 已就绪"
      return
    fi
    sleep 2
  done

  echo "Docker 没有就绪，请先打开 Docker Desktop 后再运行。"
  exit 1
}

ensure_longbridge_auth_dir() {
  if [[ ! -d "${HOME}/.longbridge" ]]; then
    echo "未找到 ${HOME}/.longbridge，请先在电脑终端运行: longbridge auth login"
    exit 1
  fi
}

container_publishes_host_port() {
  docker port "$CONTAINER_NAME" 2>/dev/null | grep -Eq "(:|\\]:)${HOST_PORT}$"
}

ensure_port_available() {
  if ! command -v lsof >/dev/null 2>&1; then
    return
  fi

  if lsof -nP -iTCP:"$HOST_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    if container_publishes_host_port; then
      return
    fi

    echo "${HOST_PORT} 端口已经被其他服务占用。"
    echo "请先停止占用该端口的服务，或临时换端口启动: AI_STOCK_HOST_PORT=8766 ./启动Docker.command"
    exit 1
  fi
}

log "准备启动 AI 选股 Docker 服务..."
ensure_docker
ensure_longbridge_auth_dir
ensure_port_available

docker compose up -d --build

log "服务状态"
docker compose ps

printf "\n启动完成。\n访问地址: %s\n\n" "$APP_URL"
open "$APP_URL" >/dev/null 2>&1 || true

if [[ -t 0 ]]; then
  read -r -p "按回车关闭这个窗口..." _
fi
