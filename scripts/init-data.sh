#!/bin/bash
# Seed backend/data from examples/ (no secrets in git).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATA="$ROOT/backend/data"
EX="$DATA/examples"

if [[ -f "$ROOT/.env" ]]; then
  # shellcheck disable=SC1091
  set -a && source "$ROOT/.env" && set +a
fi
SRV_PORT="${OLCRTC_SRV_PORT:-8801}"

mkdir -p "$DATA/configs"

copy_if_missing() {
  local src="$1" dst="$2"
  if [[ -f "$dst" ]]; then
    echo "  keep existing $(basename "$dst")"
    return
  fi
  cp "$src" "$dst"
  echo "  created $(basename "$dst") from example"
}

apply_srv_port() {
  local f="$1"
  [[ -f "$f" ]] || return
  if [[ "$(uname -s)" == Darwin* ]]; then
    sed -i '' -E "s/\"socks_port\": [0-9]+/\"socks_port\": ${SRV_PORT}/" "$f" 2>/dev/null || true
  else
    sed -i -E "s/\"socks_port\": [0-9]+/\"socks_port\": ${SRV_PORT}/" "$f" 2>/dev/null || true
  fi
}

echo ">>> Initializing backend/data from examples/"
copy_if_missing "$EX/config.json.example" "$DATA/config.json"
copy_if_missing "$EX/users.json.example" "$DATA/users.json"
copy_if_missing "$EX/nodes.json.example" "$DATA/nodes.json"
copy_if_missing "$EX/configs/olcrtc-1.yaml.example" "$DATA/configs/olcrtc-1.yaml"
apply_srv_port "$DATA/users.json"
echo ">>> Telemost: edit backend/data/users.json — paste meeting link in room_id"
echo ">>> olcrtc srv host port: ${SRV_PORT} (OLCRTC_SRV_PORT in .env)"
