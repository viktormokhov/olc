#!/usr/bin/env python3
"""OlcPanel: default olcrtc:patched, recreate container on Start if wrong image."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from olcpanel_paths import APP, COMPOSE  # noqa: E402

OLD_DEFAULT = "OLCRTC_IMAGE = os.environ.get('OLCRTC_IMAGE', 'olcrtc:universal')"
NEW_DEFAULT = "OLCRTC_IMAGE = os.environ.get('OLCRTC_IMAGE', 'olcrtc:patched')"

OLD_RUNNING = """        cn = f'olcrtc-{uid}'
        try:
            ex = docker_client.containers.get(cn)
            if ex.status == 'running':
                containers[uid] = ex.id
                users[uid]['state'] = 'running'
                users[uid]['container_id'] = ex.id
                save_users()
                if uid not in logs or len(logs[uid]) == 0:
                    threading.Thread(target=read_container_logs, args=(uid, ex), daemon=True).start()
                if user.get('mode') == 'srv':
                    threading.Thread(target=read_traffic_stats, args=(uid,), daemon=True).start()
                return True
            ex.remove(force=True)"""

NEW_RUNNING = """        cn = f'olcrtc-{uid}'
        try:
            ex = docker_client.containers.get(cn)
            tags = ex.image.tags or []
            wrong_image = not any(OLCRTC_IMAGE in t for t in tags)
            if ex.status == 'running' and not wrong_image:
                containers[uid] = ex.id
                users[uid]['state'] = 'running'
                users[uid]['container_id'] = ex.id
                save_users()
                if uid not in logs or len(logs[uid]) == 0:
                    threading.Thread(target=read_container_logs, args=(uid, ex), daemon=True).start()
                if user.get('mode') == 'srv':
                    threading.Thread(target=read_traffic_stats, args=(uid,), daemon=True).start()
                return True
            if wrong_image:
                print(f'Removing {cn}: image {tags or ex.image.short_id}, want {OLCRTC_IMAGE}')
            ex.remove(force=True)"""

COMPOSE_OLD = "OLCRTC_IMAGE=olcrtc:universal"
COMPOSE_NEW = "OLCRTC_IMAGE=olcrtc:patched"


def patch():
    s = APP.read_text(encoding="utf-8")
    if OLD_DEFAULT not in s:
        if NEW_DEFAULT in s:
            print("default image already patched")
        else:
            raise SystemExit("OLCRTC_IMAGE default line not found")
    else:
        s = s.replace(OLD_DEFAULT, NEW_DEFAULT, 1)
        print("patched default OLCRTC_IMAGE")

    if OLD_RUNNING not in s:
        if "wrong_image" in s:
            print("start_olcrtc_container already patched")
        else:
            raise SystemExit("start_olcrtc_container block not found")
    else:
        s = s.replace(OLD_RUNNING, NEW_RUNNING, 1)
        print("patched start_olcrtc_container image check")

    APP.write_text(s, encoding="utf-8")

    if COMPOSE.exists():
        cs = COMPOSE.read_text(encoding="utf-8")
        if COMPOSE_OLD in cs:
            COMPOSE.write_text(cs.replace(COMPOSE_OLD, COMPOSE_NEW), encoding="utf-8")
            print("patched docker-compose.yml")
        elif COMPOSE_NEW in cs:
            print("compose already has patched image")


if __name__ == "__main__":
    patch()
