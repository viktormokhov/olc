# OlcPanel + olcrtc:patched

Docker deployment for **OlcPanel + Telemost / VP8** and **`olcrtc:patched`** (defer carrier reconnect, YAML config, direct dial without local SOCKS).

## Requirements

- Linux VPS (or local Linux) with **Docker** and **Compose v2**
- DNS `A` record: `PANEL_DOMAIN` → server public IP
- Open ports from `.env` (defaults: **808** panel HTTPS, **8801** olcrtc srv / Olcbox KCP)
- **`./install.sh`** prompts for `PANEL_PORT`, `OLCRTC_SRV_PORT`

## Quick install

```bash
git clone https://github.com/YOUR_ORG/OlcPanel.git
cd OlcPanel
chmod +x install.sh scripts/*.sh
./install.sh
```

1. **`./install.sh`** — ports, then edit **`.env`**: `PANEL_DOMAIN`, `ACME_EMAIL`, `SECRET_KEY`
2. Open **`https://<PANEL_DOMAIN>:<PANEL_PORT>`** (default port **808**)
3. Default admin password is in `backend/data/config.json` (from example: `admin` / `change-me`) — change after login or via `./reset-password.sh`
4. **Telemost only** — paste meeting link into **Room ID**, then **Stop → Start** instance

Verify:

```bash
./scripts/verify-install.sh
```

## What this repo contains

| Path | Purpose |
|------|---------|
| `docker-compose.yml` | bootstrap check → build `olcrtc:patched` → backend, frontend, caddy |
| `olcrtc/` | Dockerfile + `patch_defer_carrier.py` for `olcrtc:patched` |
| `backend/`, `frontend/` | Telemost panel sources (required; not generated at install) |
| `backend/data/examples/` | Sample config — copied to `backend/data/` by `init-data.sh` |
| `Caddyfile` | HTTPS inside container on **808**, published as `PANEL_PORT` (`{$PANEL_DOMAIN}`, not `{env.*}`) |
| `install.sh` | One-command install |
| `docs/OLC_TELEMOST.md` | How client, srv, and Telemost connect |
| `docs/olcbox_android_telemost.md` | Android Olcbox setup |

**Not in git:** `.env`, `backend/data/*` (runtime secrets)

## Environment (`.env`)

| Variable | Description |
|----------|-------------|
| `PANEL_DOMAIN` | Public hostname, e.g. `panel.example.com` |
| `ACME_EMAIL` | Email for Let's Encrypt |
| `SECRET_KEY` | JWT secret (`openssl rand -hex 32`) |
| `PANEL_PORT` | Host HTTPS port for panel (default `808`) |
| `OLCRTC_SRV_PORT` | Host port for olcrtc srv / Olcbox KCP (default `8801`) |
| `HOST_DATA_DIR` | Default `./backend/data` |
| `OLCRTC_IMAGE` | Default `olcrtc:patched` |

See [`.env.example`](.env.example).

## Update / rebuild

```bash
docker compose up -d --build
```

In the panel: **Stop → Start** instance after image or room/YAML changes.

## Android client (Olcbox)

Patched APK is **not** served from the panel host. Build with `scripts/build_olcbox_android_patched_server.sh` and publish to **GitHub Releases** (see [docs/olcbox_android_telemost.md](docs/olcbox_android_telemost.md)).

## Documentation

- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — VPS ports, firewall, host nginx
- [docs/OLC_TELEMOST.md](docs/OLC_TELEMOST.md) — architecture
- [docs/olcbox_android_telemost.md](docs/olcbox_android_telemost.md) — Android client

## License

Upstream OlcPanel and olcrtc have their own licenses. Patches in this repository are provided as-is for deployment convenience.
