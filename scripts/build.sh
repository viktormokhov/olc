#!/usr/bin/env bash
# Deprecated wrapper — use docker compose only.
set -euo pipefail
cd "$(dirname "$0")/.."
exec docker compose up -d --build "$@"
