"""Fix videochannel CLI mapping + restore vp8 telemost instance on server."""
import json
import subprocess
from pathlib import Path

APP = Path("/home/admin/OlcPanel/backend/src/app.py")
USERS = Path("/home/admin/OlcPanel/backend/data/users.json")

OLD = """    transport_params = user.get('transport_params', {})
    for key, value in transport_params.items():
        if value is not None and value != '':
            cmd.extend([f'-{key}', str(value)])"""

NEW = """    transport_params = user.get('transport_params', {}) or {}
    transport = user.get('transport', '')
    if transport == 'videochannel':
        p = dict(transport_params)
        cmd.extend(['-video-codec', str(p.get('codec', 'qrcode'))])
        res = str(p.get('resolution', '1080x1080')).lower()
        if 'x' in res:
            w, h = res.split('x', 1)
            cmd.extend(['-video-w', w.strip(), '-video-h', h.strip()])
        else:
            cmd.extend(['-video-w', '1080', '-video-h', '1080'])
        br = str(p.get('bitrate', '5000k'))
        if br.isdigit():
            n = int(br)
            br = f'{n // 1000}k' if n >= 1000 else f'{n}k'
        cmd.extend(['-video-bitrate', br, '-video-fps', '60'])
        hw = p.get('hw_accel') in (True, 'true', '1', 1, 'on')
        cmd.extend(['-video-hw', 'nvenc' if hw else 'none'])
    elif transport == 'seichannel':
        for key, value in transport_params.items():
            if value is None or value == '':
                continue
            flag = '-ack-ms' if key == 'ack_timeout' else f'-{key}'
            cmd.extend([flag, str(value)])
    else:
        for key, value in transport_params.items():
            if value is not None and value != '':
                cmd.extend([f'-{key}', str(value)])"""


def main():
    s = APP.read_text(encoding="utf-8")
    if OLD not in s:
        if "transport == 'videochannel'" not in s:
            raise SystemExit("patch marker not found")
        print("app.py already patched")
    else:
        APP.write_text(s.replace(OLD, NEW, 1), encoding="utf-8")
        print("patched", APP)

    d = json.loads(USERS.read_text(encoding="utf-8"))
    u = d["1"]
    u["transport"] = "vp8channel"
    u["transport_params"] = {"vp8-fps": "60", "vp8-batch": "64"}
    u["state"] = "stopped"
    USERS.write_text(json.dumps(d, indent=2), encoding="utf-8")
    print("users.json updated to vp8channel 60/64")

    subprocess.run(["docker", "rm", "-f", "olcrtc-1"], check=False)
    uid = "1"
    socks_port = 8800 + int(uid)
    cmd = [
        "docker",
        "run",
        "-d",
        "--name",
        f"olcrtc-{uid}",
        "-p",
        f"{socks_port}:1081",
        "-e",
        "SOCKS_PORT=1081",
        "olcrtc:latest",
        "-mode",
        "srv",
        "-carrier",
        u["carrier"],
        "-transport",
        u["transport"],
        "-link",
        "direct",
        "-data",
        "/data",
        "-id",
        u["room_id"],
        "-client-id",
        u["client_id"],
        "-key",
        u["key"],
        "-dns",
        u.get("dns", "1.1.1.1:53"),
        "-socks-proxy",
        "127.0.0.1",
        "-socks-proxy-port",
        "1081",
        "-vp8-fps",
        "60",
        "-vp8-batch",
        "64",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr)
        raise SystemExit(r.returncode)
    cid = r.stdout.strip()
    u["state"] = "running"
    u["container_id"] = cid
    u["socks_port"] = socks_port
    USERS.write_text(json.dumps(d, indent=2), encoding="utf-8")
    print("started olcrtc-1", cid)


if __name__ == "__main__":
    main()
