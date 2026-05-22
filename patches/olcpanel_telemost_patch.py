"""One-off patch script for remote OlcPanel - run on server: python3 olcpanel_telemost_patch.py"""
from pathlib import Path

APP = Path("/home/admin/OlcPanel/backend/src/app.py")

def main():
    s = APP.read_text(encoding="utf-8")
    marker = "TRANSPORTS = ['datachannel', 'vp8channel', 'seichannel', 'videochannel']\n"
    ins = """TELEMOST_TRANSPORTS = frozenset({'vp8channel', 'videochannel'})


def normalize_room_id_for_carrier(carrier, room_id):
    if room_id is None:
        return room_id
    text = str(room_id).strip()
    if carrier == 'telemost':
        m = re.search(r'(?:https?://)?(?:www\\.)?telemost\\.yandex\\.ru/j/([^/?#]+)', text, re.I)
        rid = m.group(1) if m else text
        return f'https://telemost.yandex.ru/j/{rid}'
    return text


def validate_carrier_transport_pair(carrier, transport):
    if carrier == 'telemost' and transport not in TELEMOST_TRANSPORTS:
        return (
            'telemost supports only vp8channel or videochannel; '
            'create a meeting at https://telemost.yandex.ru/ and paste the link or room id'
        )
    return None

"""
    if "def normalize_room_id_for_carrier" not in s:
        if marker not in s:
            raise SystemExit("marker not found")
        s = s.replace(marker, marker + ins)

    # GET /api/transports-for/<carrier>
    route = """

@app.route('/api/transports-for/<carrier>', methods=['GET'])
@require_auth
def get_transports_for_carrier(carrier):
    if carrier == 'telemost':
        return jsonify({'transports': ['vp8channel', 'videochannel']})
    return jsonify({'transports': TRANSPORTS})
"""
    if "def get_transports_for_carrier" not in s:
        s = s.replace(
            "@app.route('/api/transports', methods=['GET'])\n@require_auth\ndef get_transports():",
            route.strip() + "\n\n@app.route('/api/transports', methods=['GET'])\n@require_auth\ndef get_transports():",
        )

    # generate_room_ids: explicit telemost message
    old_gen = "    if carrier not in ['wbstream', 'jazz']:\n        return jsonify({'error': 'Only wbstream and jazz support room generation'}), 400\n"
    new_gen = (
        "    if carrier == 'telemost':\n"
        "        return jsonify({\n"
        "            'error': (\n"
        "                'telemost does not support automated room generation; '\n"
        "                'create a meeting at https://telemost.yandex.ru/ and paste the full /j/... link or room id'\n"
        "            )\n"
        "        }), 400\n"
        "    if carrier not in ['wbstream', 'jazz']:\n"
        "        return jsonify({'error': 'Only wbstream and jazz support room generation'}), 400\n"
    )
    if "if carrier == 'telemost':" not in s.split("def generate_room_ids")[1].split("def generate_uri")[0]:
        s = s.replace(old_gen, new_gen)

    # add_user validation + normalized room_id
    old_add = """    required = ['client_id', 'key', 'room_id', 'carrier', 'transport']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400

    with lock:
        uid = str(len(users) + 1)
        users[uid] = {
            'client_id': data['client_id'],
            'key': data['key'],
            'room_id': data['room_id'],
            'carrier': data['carrier'],"""

    new_add = """    required = ['client_id', 'key', 'room_id', 'carrier', 'transport']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400

    carrier = data['carrier']
    transport = data['transport']
    err = validate_carrier_transport_pair(carrier, transport)
    if err:
        return jsonify({'error': err}), 400
    room_id = normalize_room_id_for_carrier(carrier, data['room_id'])

    with lock:
        uid = str(len(users) + 1)
        users[uid] = {
            'client_id': data['client_id'],
            'key': data['key'],
            'room_id': room_id,
            'carrier': data['carrier'],"""

    if "room_id = normalize_room_id_for_carrier" not in s:
        s = s.replace(old_add, new_add)

    # update_user: normalize + validate before save
    old_tail = """        if data.get('node_id'):
            user['node_id'] = data['node_id']

        save_users()

        # Restart container if it was running
        if user.get('state') == 'running':
            stop_olcrtc_container(uid)
            start_olcrtc_container(uid)

    return jsonify({'success': True})

@app.route('/api/users/start/<uid>', methods=['POST'])"""

    new_tail = """        if data.get('node_id'):
            user['node_id'] = data['node_id']

        err = validate_carrier_transport_pair(user.get('carrier', ''), user.get('transport', ''))
        if err:
            return jsonify({'error': err}), 400
        user['room_id'] = normalize_room_id_for_carrier(user.get('carrier', ''), user.get('room_id', ''))

        save_users()

        # Restart container if it was running
        if user.get('state') == 'running':
            stop_olcrtc_container(uid)
            start_olcrtc_container(uid)

    return jsonify({'success': True})

@app.route('/api/users/start/<uid>', methods=['POST'])"""

    if "validate_carrier_transport_pair(user.get('carrier'" not in s:
        s = s.replace(old_tail, new_tail)

    APP.write_text(s, encoding="utf-8")
    print("patched", APP)


if __name__ == "__main__":
    main()
