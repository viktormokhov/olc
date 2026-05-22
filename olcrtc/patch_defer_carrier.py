#!/usr/bin/env python3
"""Apply defer-carrier-reconnect patch to olcrtc source tree. Usage: patch_defer_carrier.py [SRC_DIR]"""
import sys
from pathlib import Path

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "/src")
CLIENT = SRC / "internal/client/client.go"
SERVER = SRC / "internal/server/server.go"

old_c = """\tln.SetShouldReconnect(func() bool { return ctx.Err() == nil })
\tln.SetReconnectCallback(func() {
\t\tif ctx.Err() != nil {
\t\t\treturn
\t\t}
\t\tif !c.handleReconnect(ctx, cfg, cancel, "carrier") {
\t\t\tcancel()
\t\t}
\t})

\tif err := ln.Connect(ctx); err != nil {"""

new_c = """\tln.SetShouldReconnect(func() bool { return ctx.Err() == nil })
\tln.SetReconnectCallback(func() {})

\tif err := ln.Connect(ctx); err != nil {"""

ins_c = """\tlogger.Infof("session %s opened (device=%s)", sid, c.deviceID)

\tc.sessMu.Lock()"""

reconnect_c = """\tlogger.Infof("session %s opened (device=%s)", sid, c.deviceID)

\tln.SetReconnectCallback(func() {
\t\tif ctx.Err() != nil {
\t\t\treturn
\t\t}
\t\tif !c.handleReconnect(ctx, cfg, cancel, "carrier") {
\t\t\tcancel()
\t\t}
\t})

\tc.sessMu.Lock()"""

old_s = """\tln.SetShouldReconnect(func() bool { return ctx.Err() == nil })
\tln.SetReconnectCallback(func() {
\t\tif ctx.Err() != nil {
\t\t\treturn
\t\t}
\t\ts.handleReconnect()
\t})

\tlogger.Infof("Connecting transport=%s carrier=%s ...", cfg.Transport, cfg.Carrier)"""

new_s = """\tln.SetShouldReconnect(func() bool { return ctx.Err() == nil })

\tlogger.Infof("Connecting transport=%s carrier=%s ...", cfg.Transport, cfg.Carrier)"""

ins_s = """\tlogger.Infof("Link connected")

\ts.wg.Add(1)"""

reconnect_s = """\tlogger.Infof("Link connected")

\tln.SetReconnectCallback(func() {
\t\tif ctx.Err() != nil {
\t\t\treturn
\t\t}
\t\ts.handleReconnect()
\t})

\ts.wg.Add(1)"""


def main() -> None:
    cs = CLIENT.read_text()
    if old_c not in cs:
        raise SystemExit(f"client: block not found in {CLIENT}")
    cs = cs.replace(old_c, new_c, 1)
    if ins_c not in cs:
        raise SystemExit(f"client: insert point not found in {CLIENT}")
    CLIENT.write_text(cs.replace(ins_c, reconnect_c, 1))
    print("patched", CLIENT)

    ss = SERVER.read_text()
    if old_s not in ss:
        raise SystemExit(f"server: block not found in {SERVER}")
    ss = ss.replace(old_s, new_s, 1)
    if ins_s not in ss:
        raise SystemExit(f"server: insert point not found in {SERVER}")
    SERVER.write_text(ss.replace(ins_s, reconnect_s, 1))
    print("patched", SERVER)


if __name__ == "__main__":
    main()
