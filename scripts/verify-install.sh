#!/bin/bash
# Post-install checks (run on the server after install.sh).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

fail=0
warn=0
ok() { printf '\033[0;32mOK\033[0m %s\n' "$*"; }
bad() { printf '\033[0;31mFAIL\033[0m %s\n' "$*"; fail=1; }
warn_msg() { printf '\033[0;33mWARN\033[0m %s\n' "$*"; warn=1; }

# shellcheck disable=SC1091
[[ -f .env ]] && set -a && source .env && set +a
DOMAIN="${PANEL_DOMAIN:-panel.example.com}"
PANEL_PORT="${PANEL_PORT:-808}"

echo "=== OlcPanel verify ==="
echo "  PANEL_DOMAIN=${DOMAIN}"
echo "  PANEL_PORT=${PANEL_PORT}"

docker compose config -q && ok "compose config" || bad "compose config"

for c in olcpanel-caddy olcpanel-backend olcpanel-frontend; do
  if docker ps --format '{{.Names}}' | grep -qx "$c"; then
    st=$(docker inspect -f '{{.State.Status}}' "$c" 2>/dev/null || echo missing)
    hc=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' "$c" 2>/dev/null || echo "?")
    ok "container $c ($st, health=$hc)"
  else
    bad "container $c not running"
  fi
done

port_listening=0
port_pat=":${PANEL_PORT} "
if ss -tlnp 2>/dev/null | grep -q "$port_pat"; then
  ok "port ${PANEL_PORT} listening (ss)"
  port_listening=1
elif netstat -tln 2>/dev/null | grep -q "$port_pat"; then
  ok "port ${PANEL_PORT} listening (netstat)"
  port_listening=1
else
  bad "port ${PANEL_PORT} not listening on host"
fi

if [[ "$DOMAIN" == "panel.example.com" ]]; then
  warn_msg "PANEL_DOMAIN is still panel.example.com — set your real DNS name in .env"
fi

check_https() {
  local url="$1" extra=("${@:2}")
  local out code err
  out=$(curl -sS -o /dev/null -w '%{http_code}' -k --connect-timeout 10 "${extra[@]}" "$url" 2>&1) || err=1
  code=$(printf '%s' "$out" | tr -cd '0-9' | head -c 3)
  [[ -z "$code" ]] && code="000"
  if [[ -n "${err:-}" && "$code" == "000" ]]; then
    printf '%s' "$out" | head -3
  fi
  printf '%s' "$code"
}

code=$(check_https "https://${DOMAIN}:${PANEL_PORT}/" \
  --resolve "${DOMAIN}:${PANEL_PORT}:127.0.0.1")
method="curl --resolve ${DOMAIN}:${PANEL_PORT}:127.0.0.1"

if [[ "$code" != "200" && "$code" != "302" ]]; then
  code2=$(check_https "https://127.0.0.1:${PANEL_PORT}/" \
    -H "Host: ${DOMAIN}")
  if [[ "$code2" == "200" || "$code2" == "302" ]]; then
    code="$code2"
    method="curl https://127.0.0.1:${PANEL_PORT}/ -H Host:${DOMAIN}"
  fi
fi

if [[ "$code" == "200" || "$code" == "302" ]]; then
  ok "HTTPS panel HTTP ${code} (${method})"
elif [[ "$port_listening" -eq 1 ]] && docker ps --format '{{.Names}}' | grep -qx olcpanel-caddy; then
  warn_msg "HTTPS check got HTTP ${code} — port is open but TLS/UI failed (often ACME/DNS)"
  echo "       Fix:"
  echo "         1. DNS A-record: ${DOMAIN} → this server public IP"
  echo "         2. Ports 80 and ${PANEL_PORT} open; Caddy must own :80 (no host nginx)"
  echo "         3. docker logs --tail 40 olcpanel-caddy"
  echo "         4. Caddyfile: {\$PANEL_DOMAIN}, HTTP on :80 + HTTPS on :808"
  if ! ss -tlnp 2>/dev/null | grep -q ':80 '; then
    echo "         5. Port 80 not listening — republish Caddy (compose: 80:80)"
  fi
  echo "       Manual test:"
  echo "         curl -vk --resolve ${DOMAIN}:${PANEL_PORT}:127.0.0.1 https://${DOMAIN}:${PANEL_PORT}/"
  if docker logs olcpanel-caddy 2>&1 | tail -25 | grep -qiE 'certificate|acme|error|failed'; then
    echo "       Recent Caddy log:"
    docker logs olcpanel-caddy 2>&1 | tail -12 | sed 's/^/         /'
  fi
  # Port up + caddy running = deploy mostly OK; TLS may need DNS propagation
else
  bad "HTTPS panel unreachable (HTTP ${code}) — ${method}"
  echo "       docker logs --tail 30 olcpanel-caddy"
  docker logs olcpanel-caddy 2>&1 | tail -15 | sed 's/^/         /' || true
fi

if docker images --format '{{.Repository}}:{{.Tag}}' | grep -qx 'olcrtc:patched'; then
  ok "image olcrtc:patched present"
else
  bad "image olcrtc:patched missing — run: docker compose build olcrtc"
fi

[[ -f backend/data/config.json ]] && ok "backend/data/config.json" || bad "missing config.json"
[[ -f backend/data/users.json ]] && ok "backend/data/users.json" || bad "missing users.json"

if docker logs olcpanel-caddy 2>&1 | tail -30 | grep -q "env.PANEL_DOMAIN"; then
  bad "Caddyfile uses {env.VAR} — must be {\$PANEL_DOMAIN}"
else
  ok "Caddyfile syntax (no {env.*} in recent logs)"
fi

echo ""
echo "Firewall: PANEL_PORT=${PANEL_PORT}, OLCRTC_SRV_PORT=${OLCRTC_SRV_PORT:-8801}"
if [[ "$fail" -eq 0 ]]; then
  if [[ "$warn" -eq 1 ]]; then
    warn_msg "Checks passed with warnings (fix TLS/DNS if panel URL does not open in browser)"
    exit 0
  fi
  ok "All checks passed"
  exit 0
fi
bad "Some checks failed"
exit 1
