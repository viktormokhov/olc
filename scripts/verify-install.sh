#!/usr/bin/env bash
# Post-install checks (run on the server after install.sh).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

fail=0
ok() { printf '\033[0;32mOK\033[0m %s\n' "$*"; }
bad() { printf '\033[0;31mFAIL\033[0m %s\n' "$*"; fail=1; }

# shellcheck disable=SC1091
[[ -f .env ]] && set -a && source .env && set +a
DOMAIN="${PANEL_DOMAIN:-panel.example.com}"
PANEL_PORT="${PANEL_PORT:-808}"

echo "=== OlcPanel verify ==="

docker compose config -q && ok "compose config" || bad "compose config"

for c in olcpanel-caddy olcpanel-backend olcpanel-frontend; do
  if docker ps --format '{{.Names}}' | grep -qx "$c"; then
    st=$(docker inspect -f '{{.State.Status}}' "$c" 2>/dev/null || echo missing)
    ok "container $c ($st)"
  else
    bad "container $c not running"
  fi
done

port_pat=":${PANEL_PORT} "
if ss -tlnp 2>/dev/null | grep -q "$port_pat"; then
  ok "port ${PANEL_PORT} listening"
elif netstat -tln 2>/dev/null | grep -q "$port_pat"; then
  ok "port ${PANEL_PORT} listening"
else
  bad "port ${PANEL_PORT} not listening"
fi

code=$(curl -sS -o /dev/null -w '%{http_code}' -k --connect-timeout 5 \
  --resolve "${DOMAIN}:${PANEL_PORT}:127.0.0.1" "https://${DOMAIN}:${PANEL_PORT}/" 2>/dev/null || echo 000)
if [[ "$code" == "200" || "$code" == "302" ]]; then
  ok "HTTPS panel HTTP $code"
else
  bad "HTTPS panel returned $code (check PANEL_DOMAIN, Caddy logs: docker logs olcpanel-caddy)"
fi

if docker images --format '{{.Repository}}:{{.Tag}}' | grep -qx 'olcrtc:patched'; then
  ok "image olcrtc:patched present"
else
  bad "image olcrtc:patched missing — run docker compose build olcrtc"
fi

[[ -f backend/data/config.json ]] && ok "backend/data/config.json" || bad "missing config.json"
[[ -f backend/data/users.json ]] && ok "backend/data/users.json" || bad "missing users.json"

if docker logs olcpanel-caddy 2>&1 | tail -20 | grep -q "env.PANEL_DOMAIN"; then
  bad "Caddyfile uses {env.VAR} — must be {\$PANEL_DOMAIN}"
else
  ok "Caddyfile syntax (no {env.*} in recent logs)"
fi

echo ""
echo "Firewall: PANEL_PORT=${PANEL_PORT}, OLCRTC_SRV_PORT=${OLCRTC_SRV_PORT:-8801}"
if [[ "$fail" -eq 0 ]]; then
  ok "All checks passed"
  exit 0
fi
bad "Some checks failed"
exit 1
