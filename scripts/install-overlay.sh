#!/bin/bash
# Copy deploy overlay into an existing OlcPanel tree (advanced).
# Usage: ./scripts/install-overlay.sh /path/to/OlcPanel
set -euo pipefail

TARGET="${1:?Usage: install-overlay.sh /path/to/OlcPanel}"
OVERLAY="$(cd "$(dirname "$0")/.." && pwd)"

if [[ ! -f "$TARGET/backend/src/app.py" ]]; then
  echo "Target does not look like OlcPanel: $TARGET" >&2
  exit 1
fi

cp -v "$OVERLAY/docker-compose.yml" "$OVERLAY/.env.example" "$OVERLAY/Caddyfile" "$TARGET/"
cp -v "$OVERLAY/.gitignore" "$TARGET/" 2>/dev/null || true
mkdir -p "$TARGET/host-nginx" "$TARGET/scripts" "$TARGET/olcrtc"
cp -v "$OVERLAY/host-nginx/"* "$TARGET/host-nginx/" 2>/dev/null || true
cp -v "$OVERLAY/scripts/"*.sh "$OVERLAY/scripts/"*.py "$TARGET/scripts/" 2>/dev/null || true
cp -rv "$OVERLAY/olcrtc/"* "$TARGET/olcrtc/"
# Patched panel sources (Telemost build)
cp -v "$OVERLAY/backend/src/app.py" "$TARGET/backend/src/app.py"
cp -v "$OVERLAY/frontend/src/App.js" "$TARGET/frontend/src/App.js"

echo "Overlay installed into $TARGET"
echo "Next: cd $TARGET && cp .env.example .env && ./install.sh"
