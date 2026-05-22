from pathlib import Path
p = Path("/home/admin/OlcPanel/backend/src/app.py")
s = p.read_text()
m = "        cmd = build_olcrtc_command(user)\n\n        port_bindings = {}"
i = (
    "        cn = f'olcrtc-{uid}'\n"
    "        try:\n"
    "            ex = docker_client.containers.get(cn)\n"
    "            if ex.status == 'running':\n"
    "                containers[uid] = ex.id\n"
    "                users[uid]['state'] = 'running'\n"
    "                users[uid]['container_id'] = ex.id\n"
    "                save_users()\n"
    "                if uid not in logs or len(logs[uid]) == 0:\n"
    "                    threading.Thread(target=read_container_logs, args=(uid, ex), daemon=True).start()\n"
    "                if user.get('mode') == 'srv':\n"
    "                    threading.Thread(target=read_traffic_stats, args=(uid,), daemon=True).start()\n"
    "                return True\n"
    "            ex.remove(force=True)\n"
    "        except docker.errors.NotFound:\n"
    "            pass\n"
    "        except Exception as e:\n"
    "            print(f'clean {cn}: {e}')\n"
    "            try:\n"
    "                ex.remove(force=True)\n"
    "            except Exception:\n"
    "                pass\n\n"
)
if "cn = f'olcrtc-{uid}'" not in s:
    s = s.replace(m, i + m, 1)
o = "    success = start_olcrtc_container(uid)\n    return jsonify({'success': success})"
n = (
    "    success = start_olcrtc_container(uid)\n"
    "    if not success:\n"
    "        return jsonify({'success': False, 'error': 'Container failed to start'}), 500\n"
    "    return jsonify({'success': True})"
)
if o in s:
    s = s.replace(o, n, 1)
p.write_text(s)
print("ok")
