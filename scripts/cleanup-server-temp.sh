#!/bin/bash
# Remove scratch files from manual debugging on the VPS (safe to re-run).
set -euo pipefail

rm -f /root/repack_olcbox_apk.py /root/olcpanel_*.py
rm -rf /tmp/apk-patch
echo "Kept: /home/admin/OlcPanel, docker image olcrtc:patched, backend/data"
echo "Optional: rm -rf /tmp/olcrtc-src /tmp/olcbox-src"
