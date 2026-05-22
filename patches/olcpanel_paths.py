"""Shared OlcPanel root paths for patch scripts."""
import os
from pathlib import Path

ROOT = Path(os.environ.get("OLCPANEL_ROOT", ".")).resolve()
APP = ROOT / "backend" / "src" / "app.py"
FRONT = ROOT / "frontend" / "src" / "App.js"
COMPOSE = ROOT / "docker-compose.yml"
OLCRTC_DOCKERFILE = ROOT / "olcrtc" / "Dockerfile"
REQ = ROOT / "backend" / "requirements.txt"
USERS = ROOT / "backend" / "data" / "users.json"
