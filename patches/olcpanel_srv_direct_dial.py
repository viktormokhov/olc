#!/usr/bin/env python3
"""OlcPanel: srv must not set socks.proxy_* to 127.0.0.1:1081 (no listener). Direct dial."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from olcpanel_paths import APP  # noqa: E402

OLD = """    if mode == 'srv':
        cfg['socks'] = {'proxy_addr': '127.0.0.1', 'proxy_port': 1081}
    elif mode == 'cnc':"""

NEW = """    if mode == 'cnc':"""


def patch():
    s = APP.read_text(encoding="utf-8")
    if OLD not in s:
        if "proxy_port': 1081" not in s:
            print("already patched")
            return
        raise SystemExit("block not found")
    APP.write_text(s.replace(OLD, NEW, 1), encoding="utf-8")
    print("patched", APP)


if __name__ == "__main__":
    patch()
