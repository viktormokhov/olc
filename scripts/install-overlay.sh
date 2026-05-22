#!/bin/bash
# Copy overlay files into another OlcPanel directory (advanced).
# Usage: ./scripts/install-overlay.sh /path/to/OlcPanel
set -euo pipefail

TARGET="${1:?Usage: install-overlay.sh /path/to/OlcPanel}"
OVERLAY="$(cd "$(dirname "$0")/.." && pwd)"

if [[ ! -d "$TARGET/.git" ]] && [[ ! -f "$TARGET/backend/src/app.py" ]]; then
  echo "Target does not look like OlcPanel: $TARGET" >&2
  exit 1
fi

cp -v "$OVERLAY/docker-compose.yml" "$TARGET/"
cp -v "$OVERLAY/.env.example" "$TARGET/"
cp -v "$OVERLAY/Caddyfile" "$TARGET/"
cp -v "$OVERLAY/.gitignore" "$TARGET/" 2>/dev/null || true
mkdir -p "$TARGET/host-nginx" "$TARGET/scripts" "$TARGET/patches" "$TARGET/olcrtc"
cp -v "$OVERLAY/host-nginx/"* "$TARGET/host-nginx/" 2>/dev/null || true
cp -v "$OVERLAY/scripts/"*.sh "$OVERLAY/scripts/"*.py "$TARGET/scripts/"
cp -rv "$OVERLAY/olcrtc/"* "$TARGET/olcrtc/"
cp -rv "$OVERLAY/patches/"* "$TARGET/patches/"

echo "Overlay installed into $TARGET"
echo "Next: cd $TARGET && cp .env.example .env && docker compose up -d --build"
