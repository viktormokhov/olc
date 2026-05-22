#!/usr/bin/env python3
"""Apply Telemost-oriented patches to olcrtc (master branch).

- Defer carrier reconnect until session / link is ready (avoids handshake EOF).
- Optional: extend handshake DefaultTimeout 15s -> 90s.

Usage: patch_defer_carrier.py [SRC_DIR]
"""
from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "/src")
CLIENT = SRC / "internal/client/client.go"
SERVER = SRC / "internal/server/server.go"
HANDSHAKE = SRC / "internal/handshake/handshake.go"

# --- legacy refactor/universal-carrier (if someone pins an old fork) ---
OLD_C_LEGACY = """\tln.SetShouldReconnect(func() bool { return ctx.Err() == nil })
\tln.SetReconnectCallback(func() {
\t\tif ctx.Err() != nil {
\t\t\treturn
\t\t}
\t\tif !c.handleReconnect(ctx, cfg, cancel, "carrier") {
\t\t\tcancel()
\t\t}
\t})

\tif err := ln.Connect(ctx); err != nil {"""

NEW_C_NOOP = """\tln.SetShouldReconnect(func() bool { return ctx.Err() == nil })
\tln.SetReconnectCallback(func() {})

\tif err := ln.Connect(ctx); err != nil {"""

INS_C = """\tlogger.Infof("session %s opened (device=%s)", sid, c.deviceID)

\tc.sessMu.Lock()"""

RECONNECT_C_LEGACY = """\tlogger.Infof("session %s opened (device=%s)", sid, c.deviceID)

\tln.SetReconnectCallback(func() {
\t\tif ctx.Err() != nil {
\t\t\treturn
\t\t}
\t\tif !c.handleReconnect(ctx, cfg, cancel, "carrier") {
\t\t\tcancel()
\t\t}
\t})

\tc.sessMu.Lock()"""

# --- upstream master (openlibrecommunity/olcrtc) ---
OLD_C_MASTER = """\tln.SetShouldReconnect(func() bool { return ctx.Err() == nil })
\tln.SetReconnectCallback(func() {
\t\tif ctx.Err() != nil {
\t\t\treturn
\t\t}
\t\t// Carrier callback fires after the link is back up. If handshake
\t\t// still fails it usually means the server hasn't completed its
\t\t// own reinstall yet — keep the listener up and wait for either
\t\t// another callback or a future liveness loss to re-trigger.
\t\tc.handleReconnect(ctx, cfg, cancel, "carrier")
\t})

\tif err := ln.Connect(ctx); err != nil {"""

RECONNECT_C_MASTER = """\tlogger.Infof("session %s opened (device=%s)", sid, c.deviceID)

\tln.SetReconnectCallback(func() {
\t\tif ctx.Err() != nil {
\t\t\treturn
\t\t}
\t\t// Carrier callback fires after the link is back up. If handshake
\t\t// still fails it usually means the server hasn't completed its
\t\t// own reinstall yet — keep the listener up and wait for either
\t\t// another callback or a future liveness loss to re-trigger.
\t\tc.handleReconnect(ctx, cfg, cancel, "carrier")
\t})

\tc.sessMu.Lock()"""

OLD_S_LEGACY = """\tln.SetShouldReconnect(func() bool { return ctx.Err() == nil })
\tln.SetReconnectCallback(func() {
\t\tif ctx.Err() != nil {
\t\t\treturn
\t\t}
\t\ts.handleReconnect()
\t})

\tlogger.Infof("Connecting transport=%s carrier=%s ...", cfg.Transport, cfg.Carrier)"""

OLD_S_MASTER = """\tln.SetShouldReconnect(func() bool { return ctx.Err() == nil })
\tln.SetReconnectCallback(func() {
\t\tif ctx.Err() != nil {
\t\t\treturn
\t\t}
\t\ts.handleReconnect()
\t})

\tlogger.Infof("Connecting transport=%s carrier=%s ...", cfg.Transport, cfg.Carrier)
\tif s.peerLn == nil {
\t\ts.installSession()
\t}

\tif err := ln.Connect(ctx); err != nil {"""

NEW_S_PREFIX = """\tln.SetShouldReconnect(func() bool { return ctx.Err() == nil })

\tlogger.Infof("Connecting transport=%s carrier=%s ...", cfg.Transport, cfg.Carrier)"""

INS_S_LEGACY = """\tlogger.Infof("Link connected")

\ts.wg.Add(1)"""

RECONNECT_S_LEGACY = """\tlogger.Infof("Link connected")

\tln.SetReconnectCallback(func() {
\t\tif ctx.Err() != nil {
\t\t\treturn
\t\t}
\t\ts.handleReconnect()
\t})

\ts.wg.Add(1)"""

INS_S_MASTER = """\tlogger.Infof("Link connected")

\ts.wg.Add(1)
\tgo func() {
\t\tdefer s.wg.Done()
\t\tln.WatchConnection(ctx)
\t}()
\treturn nil"""

RECONNECT_S_MASTER = """\tlogger.Infof("Link connected")

\tln.SetReconnectCallback(func() {
\t\tif ctx.Err() != nil {
\t\t\treturn
\t\t}
\t\ts.handleReconnect()
\t})

\ts.wg.Add(1)
\tgo func() {
\t\tdefer s.wg.Done()
\t\tln.WatchConnection(ctx)
\t}()
\treturn nil"""


def patch_handshake() -> bool:
    if not HANDSHAKE.is_file():
        return False
    text = HANDSHAKE.read_text(encoding="utf-8")
    old = "const DefaultTimeout = 15 * time.Second"
    new = "const DefaultTimeout = 90 * time.Second"
    if new in text:
        print("skip handshake timeout (already 90s)", HANDSHAKE)
        return True
    if old not in text:
        print("warn: handshake DefaultTimeout line not found", HANDSHAKE)
        return False
    HANDSHAKE.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("patched handshake DefaultTimeout 90s", HANDSHAKE)
    return True


def patch_client() -> bool:
    cs = CLIENT.read_text(encoding="utf-8")
    if "SetReconnectCallback(func() {})" in cs and OLD_C_MASTER not in cs and OLD_C_LEGACY not in cs:
        print("skip client (defer reconnect already applied)", CLIENT)
        return True

    for old_c, reconnect_c, label in (
        (OLD_C_MASTER, RECONNECT_C_MASTER, "master"),
        (OLD_C_LEGACY, RECONNECT_C_LEGACY, "legacy"),
    ):
        if old_c not in cs:
            continue
        cs = cs.replace(old_c, NEW_C_NOOP, 1)
        if INS_C not in cs:
            raise SystemExit(f"client ({label}): insert point not found in {CLIENT}")
        cs = cs.replace(INS_C, reconnect_c, 1)
        CLIENT.write_text(cs, encoding="utf-8")
        print(f"patched client defer reconnect ({label})", CLIENT)
        return True

    raise SystemExit(f"client: reconnect block not found in {CLIENT}")


def patch_server() -> bool:
    ss = SERVER.read_text(encoding="utf-8")
    if (
        "Link connected\"\n\n\tln.SetReconnectCallback" in ss
        or "Link connected\"\n\n\tln.SetReconnectCallback" in ss.replace("\r\n", "\n")
    ):
        print("skip server (defer reconnect already applied)", SERVER)
        return True

    for old_s, new_s_tail, ins_s, reconnect_s, label in (
        (
            OLD_S_MASTER,
            NEW_S_PREFIX
            + "\n\tif s.peerLn == nil {\n\t\ts.installSession()\n\t}\n\n\tif err := ln.Connect(ctx); err != nil {",
            INS_S_MASTER,
            RECONNECT_S_MASTER,
            "master",
        ),
        (
            OLD_S_LEGACY,
            NEW_S_PREFIX,
            INS_S_LEGACY,
            RECONNECT_S_LEGACY,
            "legacy",
        ),
    ):
        if old_s not in ss:
            continue
        ss = ss.replace(old_s, new_s_tail, 1)
        if ins_s not in ss:
            raise SystemExit(f"server ({label}): insert point not found in {SERVER}")
        ss = ss.replace(ins_s, reconnect_s, 1)
        SERVER.write_text(ss, encoding="utf-8")
        print(f"patched server defer reconnect ({label})", SERVER)
        return True

    raise SystemExit(f"server: reconnect block not found in {SERVER}")


def main() -> None:
    patch_handshake()
    patch_client()
    patch_server()


if __name__ == "__main__":
    main()
