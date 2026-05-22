#!/usr/bin/env python3
"""Apply all OlcPanel patches. Run from OlcPanel repo root after copying overlay."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

OLCPANEL_ROOT = Path(os.environ.get("OLCPANEL_ROOT", ".")).resolve()
PATCHES_DIR = OLCPANEL_ROOT / "patches"
if not PATCHES_DIR.is_dir():
    PATCHES_DIR = Path(__file__).resolve().parent.parent / "patches"

PATCHES = [
    "olcpanel_universal_carrier.py",
    "olcpanel_srv_direct_dial.py",
    "olcpanel_force_patched_image.py",
    "olcpanel_vp8_telemost_fix.py",
    "olcpanel_appjs_telemost_patch.py",
    "olcpanel_telemost_only.py",
]


def main() -> None:
    if not (OLCPANEL_ROOT / "backend" / "src" / "app.py").is_file():
        print(f"OlcPanel not found at {OLCPANEL_ROOT}", file=sys.stderr)
        sys.exit(1)
    env = {**os.environ, "OLCPANEL_ROOT": str(OLCPANEL_ROOT)}
    for name in PATCHES:
        script = PATCHES_DIR / name
        if not script.is_file():
            print(f"skip missing {script}")
            continue
        print(f"=== {name} ===")
        subprocess.run([sys.executable, str(script)], check=True, env=env, cwd=OLCPANEL_ROOT)
    print("All patches applied.")


if __name__ == "__main__":
    main()
