#!/bin/bash
# Remove one-off temp files from manual debugging on the VPS (safe to re-run).
set -euo pipefail

echo "Removing /root scratch scripts..."
rm -f /root/repack_olcbox_apk.py /root/olcpanel_force_patched_image.py /root/repack_olcbox_apk.py

echo "Removing APK repack workspace (large)..."
rm -rf /tmp/apk-patch

echo "Optional: remove olcrtc build tree if disk is tight:"
echo "  rm -rf /tmp/olcrtc-src"
echo ""
echo "Keep: /home/admin/OlcPanel, docker images olcrtc:patched, backend/data"
