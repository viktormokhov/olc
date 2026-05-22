# Deployment guide

Generic VPS setup for OlcPanel from this repository.

## Ports

Set in `.env` (or prompted by `./install.sh`):

| Variable | Default | Service |
|----------|---------|---------|
| `PANEL_PORT` | **808** | Panel HTTPS (`https://<PANEL_DOMAIN>:<PANEL_PORT>`) |
| `OLCRTC_SRV_PORT` | **8801** | olcrtc srv / Olcbox KCP (after **Start** in UI) |

Ensure these are open in your firewall / security group. **Olcbox APK** — from GitHub Releases, not from this server.

**Carrier:** only **Telemost** — paste a meeting link in **Room ID** (no wbstream/jazz, no room generator).

## Install

```bash
git clone <your-repo-url>
cd OlcPanel
./install.sh
./scripts/verify-install.sh
```

## DNS and TLS

1. Create DNS `A` record: `PANEL_DOMAIN` → your server IP.
2. Set `ACME_EMAIL` in `.env`.
3. Caddy obtains a certificate automatically (stored in Docker volume `caddy_data`).

**Caddyfile note:** use `{$PANEL_DOMAIN}` and `{$ACME_EMAIL}` — not `{env.PANEL_DOMAIN}`.

## Data backup

```bash
tar czf olcpanel-data-$(date +%F).tar.gz -C . backend/data
```

Do not commit `backend/data/` to git — it contains keys and room URLs.

## Host nginx (optional)

If port 443 on the host must proxy to the panel:

```bash
cp host-nginx/panel.example.com.conf /etc/nginx/sites-available/
# edit server_name and paths
sudo ln -s /etc/nginx/sites-available/panel.example.com.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Default install uses **Caddy** published on host `PANEL_PORT` (container listens on 808).

## Troubleshooting

| Issue | Check |
|-------|--------|
| Panel not opening | `docker ps`, `docker logs olcpanel-caddy`, `PANEL_PORT` in `.env` |
| Caddy restart loop | Caddyfile must use `{$VAR}` syntax |
| 502 from Caddy | `docker ps` — backend/frontend must be Up |
| Telemost / tunnel | [OLC_TELEMOST.md](OLC_TELEMOST.md) |
