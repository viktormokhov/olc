#!/bin/bash
# OlcPanel — first-time install (Docker Compose).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

red() { printf '\033[0;31m%s\033[0m\n' "$*"; }
green() { printf '\033[0;32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[0;33m%s\033[0m\n' "$*"; }

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

is_placeholder() {
  local key="$1" val="$2"
  case "$key" in
    PANEL_DOMAIN) [[ -z "$val" || "$val" == "panel.example.com" ]] ;;
    ACME_EMAIL) [[ -z "$val" || "$val" == "admin@example.com" ]] ;;
    SECRET_KEY) [[ -z "$val" || "$val" == change-me* ]] ;;
    *) [[ -z "$val" ]] ;;
  esac
}

# Prompt when TTY and value empty/placeholder; optional force reprompt on fresh .env
prompt_var() {
  local key="$1" default="$2" hint="$3"
  local secret="${4:-0}" force="${5:-0}"
  local current val

  current=$(env_get "$key")
  if [[ "$force" != "1" ]] && [[ -n "$current" ]] && ! is_placeholder "$key" "$current"; then
    echo "  ${key}=${current} (keep)"
    return
  fi

  if [[ ! -t 0 ]]; then
    val="${current:-$default}"
    if is_placeholder "$key" "$val"; then
      yellow "  ${key}: using default ${val} (non-interactive — edit .env before production)"
    else
      echo "  ${key}=${val} (non-interactive)"
    fi
    env_set "$key" "$val"
    return
  fi

  if [[ "$secret" == "1" ]]; then
    if [[ -n "$current" ]] && ! is_placeholder "$key" "$current"; then
      read -rsp "${key} — ${hint} [Enter=keep current]: " val || true
      echo
      if [[ -z "$val" ]]; then
        echo "  ${key}=(unchanged)"
        return
      fi
    else
      read -rsp "${key} — ${hint} [Enter=auto-generate]: " val || true
      echo
      if [[ -z "$val" ]]; then
        if command -v openssl >/dev/null 2>&1; then
          val=$(openssl rand -hex 32)
          green "  ${key}=(generated)"
        else
          val="$default"
          yellow "  openssl not found — set SECRET_KEY in .env manually"
        fi
      else
        echo "  ${key}=(set)"
      fi
    fi
  else
    local shown="${current:-$default}"
    if is_placeholder "$key" "$shown"; then
      shown="$default"
    fi
    read -rp "${key} — ${hint} [${shown}]: " val || true
    val=${val:-$shown}
    echo "  ${key}=${val}"
  fi
  env_set "$key" "$val"
}

configure_env() {
  local fresh="${1:-0}"
  echo ""
  echo ">>> Panel settings (saved to .env)"
  if [[ ! -t 0 ]]; then
    yellow "No TTY — using .env defaults; edit .env for production."
  fi
  prompt_var PANEL_DOMAIN "panel.example.com" "public DNS name (A-record → this server)" 0 "$fresh"
  prompt_var ACME_EMAIL "admin@example.com" "Let's Encrypt contact email" 0 "$fresh"
  prompt_var SECRET_KEY "change-me" "JWT secret for API" 1 "$fresh"
}

# Ports: always ask in interactive install (separate step from domain/email).
prompt_port() {
  local key="$1" default="$2" hint="$3"
  local current val shown

  current=$(env_get "$key")
  shown="${current:-$default}"

  if [[ ! -t 0 ]]; then
    env_set "$key" "$shown"
    echo "  ${key}=${shown} (non-interactive)"
    return
  fi

  echo ""
  read -rp "  ${key} — ${hint}"$'\n'"       Current: ${shown}"$'\n'"       New value [Enter=${shown}]: " val || true
  val=${val:-$shown}
  env_set "$key" "$val"
  echo "  → ${key}=${val}"
}

configure_ports() {
  echo ""
  echo ">>> Ports (each value entered separately; open them in firewall)"
  if [[ ! -t 0 ]]; then
    yellow "No TTY — keeping PANEL_PORT / OLCRTC_SRV_PORT from .env"
    return
  fi
  prompt_port PANEL_PORT "808" "HTTPS panel — host port (Caddy HTTPS inside container :808)"
  prompt_port OLCRTC_SRV_PORT "8801" "olcrtc srv — KCP port for Olcbox / tunnel after Start in panel"
  echo ""
  yellow "  Port 80 is fixed (HTTP) — required for Let's Encrypt. Stop host nginx/apache on :80 if ACME fails."
}

echo "=== OlcPanel install ==="

need_cmd docker
docker compose version >/dev/null 2>&1 || { red "Need Docker Compose v2 (docker compose)"; exit 1; }

FRESH_ENV=0
if [[ ! -f .env ]]; then
  cp .env.example .env
  FRESH_ENV=1
  green "Created .env from .env.example"
else
  echo "  Found existing .env"
  if is_placeholder PANEL_DOMAIN "$(env_get PANEL_DOMAIN)" \
    || is_placeholder ACME_EMAIL "$(env_get ACME_EMAIL)" \
    || is_placeholder SECRET_KEY "$(env_get SECRET_KEY)"; then
    yellow "  .env still has example placeholders — will prompt"
    FRESH_ENV=1
  fi
fi

configure_env "$FRESH_ENV"
configure_ports

# Docker bind-mounts need absolute HOST_DATA_DIR on the VPS
ABS_DATA="$(cd "$ROOT/backend/data" && pwd)"
env_set HOST_DATA_DIR "$ABS_DATA"
echo "  HOST_DATA_DIR=${ABS_DATA} (absolute, for olcrtc bind mounts)"

# shellcheck disable=SC1091
set -a && source .env && set +a

bash "$ROOT/scripts/init-data.sh"

echo ""
echo ">>> Validating compose..."
docker compose config -q
green "docker compose config OK"

echo ">>> Building and starting (may take several minutes on first run)..."
docker compose up -d --build

echo ""
green "=== Install finished ==="
echo "  Panel URL: https://${PANEL_DOMAIN}:${PANEL_PORT}"
echo "  olcrtc srv port (firewall): ${OLCRTC_SRV_PORT}"
echo "  Admin login: backend/data/config.json (default admin / change-me — change after login)"
echo "  Telemost: paste meeting link in Room ID"
echo "  Verify: ./scripts/verify-install.sh"
echo "  Docs: docs/OLC_TELEMOST.md"

if is_placeholder PANEL_DOMAIN "${PANEL_DOMAIN:-}"; then
  yellow "Warning: PANEL_DOMAIN is still a placeholder — set a real DNS name in .env"
fi
