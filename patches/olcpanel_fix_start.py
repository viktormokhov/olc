"""Fix Start button: adopt or remove existing olcrtc-{uid} container by name."""
from pathlib import Path

APP = Path("/home/admin/OlcPanel/backend/src/app.py")

OLD = """        cmd = build_olcrtc_command(user)

        port_bindings = {}
        if user.get('mode') == 'cnc':"""

NEW = """        container_name = f'olcrtc-{uid}'
        try:
            existing = docker_client.containers.get(container_name)
            if existing.status == 'running':
                containers[uid] = existing.id
                users[uid]['state'] = 'running'
                users[uid]['container_id'] = existing.id
                save_users()
                if uid not in logs or len(logs[uid]) == 0:
                    thread = threading.Thread(
                        target=read_container_logs, args=(uid, existing), daemon=True
                    )
                    thread.start()
                if user.get('mode') == 'srv':
                    traffic_thread = threading.Thread(
                        target=read_traffic_stats, args=(uid,), daemon=True
                    )
                    traffic_thread.start()
                return True
            existing.remove(force=True)
        except docker.errors.NotFound:
            pass
        except Exception as e:
            print(f"Error cleaning existing container {container_name}: {e}")
            try:
                existing.remove(force=True)
            except Exception:
                pass

        cmd = build_olcrtc_command(user)

        port_bindings = {}
        if user.get('mode') == 'cnc':"""

OLD_START_USER = """    success = start_olcrtc_container(uid)
    return jsonify({'success': success})"""

NEW_START_USER = """    success = start_olcrtc_container(uid)
    if not success:
        return jsonify({
            'success': False,
            'error': 'Container failed to start (name conflict or docker error; check backend logs)',
        }), 500
    return jsonify({'success': True})"""


def main():
    s = APP.read_text(encoding="utf-8")
    if OLD not in s:
        if "container_name = f'olcrtc-{uid}'" in s:
            print("already patched start container")
        else:
            raise SystemExit("start_olcrtc marker not found")
    else:
        s = s.replace(OLD, NEW, 1)
        print("patched start_olcrtc_container")
    if OLD_START_USER in s:
        s = s.replace(OLD_START_USER, NEW_START_USER, 1)
        print("patched start_user response")
    APP.write_text(s, encoding="utf-8")


if __name__ == "__main__":
    main()
