#!/bin/bash
# Build Olcbox Android debug APK with patched olcrtc (/tmp/olcrtc-src).
# Run on Linux build host. Output: backend/data/ — publish APK to GitHub Releases.
set -euo pipefail

OLCRTC_SRC=/tmp/olcrtc-src
OLCBOX_SRC=/tmp/olcbox-src
OUT_DIR=/home/admin/OlcPanel/backend/data
APK_NAME=Olcbox-1.0.78-patched-android.apk
ANDROID_HOME="${ANDROID_HOME:-/opt/android-sdk}"
NDK_VER=28.2.13676358
LOG=/tmp/build-olcbox-android.log

exec > >(tee -a "$LOG") 2>&1
echo "=== build started $(date -Is) ==="

# --- patched olcrtc (defer reconnect + 90s handshake) ---
python3 <<'PY' || true
from pathlib import Path
CLIENT = Path("/tmp/olcrtc-src/internal/client/client.go")
SERVER = Path("/tmp/olcrtc-src/internal/server/server.go")
HS = Path("/tmp/olcrtc-src/internal/handshake/handshake.go")

# handshake 90s
if HS.exists():
    t = HS.read_text()
    if "DefaultTimeout = 15 * time.Second" in t:
        t = t.replace("DefaultTimeout = 15 * time.Second", "DefaultTimeout = 90 * time.Second")
        HS.write_text(t)
        print("patched handshake timeout")

# defer reconnect (inline from olcrtc_defer_carrier_reconnect.py)
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
if CLIENT.exists():
    cs = CLIENT.read_text()
    if old_c in cs:
        cs = cs.replace(old_c, new_c, 1)
        if ins_c in cs:
            cs = cs.replace(ins_c, reconnect_c, 1)
        CLIENT.write_text(cs)
        print("patched client defer")
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
if SERVER.exists():
    ss = SERVER.read_text()
    if old_s in ss:
        ss = ss.replace(old_s, new_s, 1)
        if ins_s in ss:
            ss = ss.replace(ins_s, reconnect_s, 1)
        SERVER.write_text(ss)
        print("patched server defer")
PY

# --- Android SDK (one-time) ---
if [[ ! -x "$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" ]]; then
  apt-get update -qq
  apt-get install -y -qq openjdk-21-jdk-headless unzip wget curl git
  mkdir -p /opt/android-sdk/cmdline-tools
  cd /tmp
  wget -q https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip -O cmdtools.zip
  unzip -q -o cmdtools.zip -d /opt/android-sdk/cmdline-tools
  mv /opt/android-sdk/cmdline-tools/cmdline-tools /opt/android-sdk/cmdline-tools/latest
  yes | "$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" --licenses >/dev/null || true
  "$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" \
    "platform-tools" "platforms;android-36" "build-tools;36.0.0" "ndk;${NDK_VER}"
fi

export ANDROID_HOME
export ANDROID_NDK_HOME="$ANDROID_HOME/ndk/$NDK_VER"
export ANDROID_NDK_ROOT="$ANDROID_NDK_HOME"
export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/cmdline-tools/latest/bin:$PATH"

# --- Go + gomobile ---
if ! command -v go >/dev/null 2>&1; then
  apt-get install -y -qq golang-go || true
fi
export GOPATH="${GOPATH:-/root/go}"
export PATH="$GOPATH/bin:$PATH"
go install golang.org/x/mobile/cmd/gomobile@latest
go install golang.org/x/mobile/cmd/gobind@latest
cd "$OLCRTC_SRC"
gomobile init

# --- olcbox source ---
if [[ ! -d "$OLCBOX_SRC/.git" ]]; then
  rm -rf "$OLCBOX_SRC"
  git clone --depth 1 -b universal-carrier https://github.com/alananisimov/olcbox.git "$OLCBOX_SRC"
fi

cd "$OLCBOX_SRC"
chmod +x gradlew
export OLCRTC_REPO="$OLCRTC_SRC"
export JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java-21-openjdk-amd64}"

./gradlew :androidApp:assembleDebug \
  -Polcbox.version=1.0.78-patched \
  --no-daemon \
  --stacktrace

APK_SRC="$OLCBOX_SRC/androidApp/build/outputs/apk/debug/androidApp-debug.apk"
cp -f "$APK_SRC" "$OUT_DIR/$APK_NAME"
chmod 644 "$OUT_DIR/$APK_NAME"
sha256sum "$OUT_DIR/$APK_NAME" | tee "$OUT_DIR/${APK_NAME}.sha256"
ls -la "$OUT_DIR/$APK_NAME"
echo "=== DONE $(date -Is) ==="
echo "APK: $OUT_DIR/$APK_NAME — upload to GitHub Releases (not served by OlcPanel)"
