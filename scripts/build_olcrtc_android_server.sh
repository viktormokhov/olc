#!/bin/bash
# Build patched olcrtc for Android arm64. Run on the OlcPanel host (needs Docker).
set -euo pipefail
SRC=/tmp/olcrtc-src
OUT=/home/admin/OlcPanel/backend/data
IMAGE=olcrtc-winbuild

if [[ ! -d "$SRC/cmd/olcrtc" ]]; then
  echo "Missing $SRC — clone olcrtc refactor/universal-carrier first"
  exit 1
fi

# Apply defer + 90s handshake if not yet applied
python3 <<'PY' || true
from pathlib import Path
import sys
sys.path.insert(0, "/root")
# run defer patch inline if tools copied
PY

docker run --rm \
  -v "$SRC:/src" \
  -v "$OUT:/out" \
  -w /src "$IMAGE" \
  sh -c 'GOOS=android GOARCH=arm64 CGO_ENABLED=0 go build -ldflags="-s -w" -o /out/olcrtc-android-arm64 ./cmd/olcrtc'

chmod 644 "$OUT/olcrtc-android-arm64"
ls -la "$OUT/olcrtc-android-arm64"
echo "Output: $OUT/olcrtc-android-arm64 (for APK repack / GitHub; not served by OlcPanel)"
