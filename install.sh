#!/usr/bin/env bash
# OlcPanel — first-time install (Docker Compose).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

red() { printf '\033[0;31m%s\033[0m\n' "$*"; }
green() { printf '\033[0;32m%s\033[0m\n' "$*"; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || { red "Missing: $1"; exit 1; }
}

env_get() {
  local key="$1"
  grep -E "^${key}=" "$ROOT/.env" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r' || true
}

env_set() {
  local key="$1" val="$2"
  local f="$ROOT/.env"
  if grep -qE "^${key}=" "$f" 2>/dev/null; then
    if [[ "$(uname -s)" == Darwin* ]]; then
      sed -i '' "s|^${key}=.*|${key}=${val}|" "$f"
    else
      sed -i "s|^${key}=.*|${key}=${val}|" "$f"
    fi
  else
    echo "${key}=${val}" >>"$f"
  fi
}

configure_ports() {
  local env_file="$ROOT/.env"
  echo ">>> Access ports (written to .env, open them in firewall)"
  declare -A defaults=(
    [PANEL_PORT]=808
    [OLCRTC_SRV_PORT]=8801
  )
  declare -A hints=(
    [PANEL_PORT]="HTTPS panel (Caddy)"
    [OLCRTC_SRV_PORT]="olcrtc srv / Olcbox KCP"
  )
  for key in PANEL_PORT OLCRTC_SRV_PORT; do
    local current def hint val
    current=$(env_get "$key")
    def=${defaults[$key]}
    hint=${hints[$key]}
    if [[ -n "$current" ]]; then
      echo "  ${key}=${current} (keep)"
      continue
    fi
    val="$def"
    if [[ -t 0 ]]; then
      read -rp "${key} — ${hint} [${def}]: " val || true
      val=${val:-$def}
    fi
    env_set "$key" "$val"
    echo "  ${key}=${val}"
  done
}

echo "=== OlcPanel install ==="

need_cmd docker
docker compose version >/dev/null 2>&1 || { red "Need Docker Compose v2 (docker compose)"; exit 1; }

if [[ ! -f .env ]]; then
  cp .env.example .env
  green "Created .env from .env.example"
  echo "  Edit .env: PANEL_DOMAIN, ACME_EMAIL, SECRET_KEY"
  if command -v openssl >/dev/null 2>&1; then
    echo "  Suggested SECRET_KEY: $(openssl rand -hex 32)"
  fi
else
  echo "  Using existing .env"
fi

configure_ports

# shellcheck disable=SC1091
set -a && source .env && set +a

bash "$ROOT/scripts/init-data.sh"

echo ">>> Validating compose..."
docker compose config -q
green "docker compose config OK"

echo ">>> Building and starting (may take several minutes on first run)..."
docker compose up -d --build

echo ""
green "=== Install finished ==="
echo "  Panel URL: https://${PANEL_DOMAIN:-panel.example.com}:${PANEL_PORT:-808}"
echo "  olcrtc srv port (firewall): ${OLCRTC_SRV_PORT:-8801}"
echo "  Admin login: see backend/data/config.json (default admin / change-me)"
echo "  Carrier: Telemost only — paste meeting link in Room ID"
echo "  Run: ./scripts/verify-install.sh"
echo "  Docs: docs/OLC_TELEMOST.md (Telemost + Olcbox)"
