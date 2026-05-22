"""Migrate OlcPanel to olcrtc refactor/universal-carrier (YAML config, no CLI flags).

Run via bootstrap: python3 /home/admin/OlcPanel/scripts/apply-patches.py
Then rebuild:
  cd /home/admin/OlcPanel/olcrtc && docker build -t olcrtc:universal .
  cd /home/admin/OlcPanel && docker compose build backend frontend && docker compose up -d
"""
from __future__ import annotations

import re
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from olcpanel_paths import APP, COMPOSE, FRONT, OLCRTC_DOCKERFILE, REQ, ROOT  # noqa: E402

DOCKERFILE = OLCRTC_DOCKERFILE


def patch_dockerfile():
    if not DOCKERFILE.is_file():
        print("skip dockerfile (missing)", DOCKERFILE)
        return
    s = DOCKERFILE.read_text(encoding="utf-8")
    if "patch_defer_carrier.py" in s or "refactor/universal-carrier" in s and "patch_defer" in s:
        print("skip dockerfile (deploy/olcpanel/olcrtc/Dockerfile already)")
        return
    old_clone = (
        "RUN git clone --depth 1 --recurse-submodules "
        "https://github.com/openlibrecommunity/olcrtc.git ."
    )
    new_clone = (
        "RUN git clone --depth 1 --branch refactor/universal-carrier "
        "--recurse-submodules https://github.com/openlibrecommunity/olcrtc.git ."
    )
    if old_clone in s:
        s = s.replace(old_clone, new_clone)
    elif "refactor/universal-carrier" not in s:
        raise SystemExit("Dockerfile clone line not found")

    if "COPY --from=builder /build/data /app/data" not in s:
        insert = (
            "\nCOPY --from=builder /build/data /app/data\n"
        )
        s = s.replace(
            "COPY --from=builder /build/olcrtc /app/olcrtc\n",
            "COPY --from=builder /build/olcrtc /app/olcrtc\n" + insert,
        )
    DOCKERFILE.write_text(s, encoding="utf-8")
    print("patched", DOCKERFILE)


def patch_compose():
    s = COMPOSE.read_text(encoding="utf-8")
    if "HOST_DATA_DIR" not in s:
        s = s.replace(
            "      - WBSTREAM_ACCESS_TOKEN=${WBSTREAM_ACCESS_TOKEN:-}\n",
            "      - WBSTREAM_ACCESS_TOKEN=${WBSTREAM_ACCESS_TOKEN:-}\n"
            "      - HOST_DATA_DIR=${HOST_DATA_DIR:-./backend/data}\n"
            "      - OLCRTC_IMAGE=olcrtc:patched\n",
        )
    COMPOSE.write_text(s, encoding="utf-8")
    print("patched", COMPOSE)


def patch_requirements():
    s = REQ.read_text(encoding="utf-8")
    if "pyyaml" not in s.lower():
        s = s.rstrip() + "\npyyaml==6.0.1\n"
        REQ.write_text(s, encoding="utf-8")
        print("patched", REQ)
    else:
        print("requirements ok")


def patch_app():
    s = APP.read_text(encoding="utf-8")

    if "import yaml" not in s:
        s = s.replace(
            "import os\n",
            "import os\nimport re\nimport yaml\n",
        )

    if "HOST_DATA_DIR" not in s:
        s = s.replace(
            "os.makedirs(DATA_DIR, exist_ok=True)\n",
            "os.makedirs(DATA_DIR, exist_ok=True)\n"
            "HOST_DATA_DIR = os.environ.get('HOST_DATA_DIR', DATA_DIR)\n"
            "CONFIGS_DIR = os.path.join(HOST_DATA_DIR, 'configs')\n"
            "OLCRTC_IMAGE = os.environ.get('OLCRTC_IMAGE', 'olcrtc:patched')\n"
            "os.makedirs(os.path.join(DATA_DIR, 'configs'), exist_ok=True)\n"
            "os.makedirs(CONFIGS_DIR, exist_ok=True)\n",
        )

    marker = "TRANSPORTS = ['datachannel', 'vp8channel', 'seichannel', 'videochannel']\n"
    telemost_block = """TELEMOST_TRANSPORTS = frozenset({'vp8channel'})


def normalize_room_id_for_carrier(carrier, room_id):
    if room_id is None:
        return room_id
    text = str(room_id).strip()
    if carrier == 'telemost':
        m = re.search(
            r'(?:https?://)?(?:www\\.)?telemost\\.yandex\\.ru/j/([^/?#]+)',
            text,
            re.I,
        )
        # universal vp8channel: bindingToken = FNV(room URL string) — must match olcbox URI @-part
        rid = m.group(1) if m else text
        return f'https://telemost.yandex.ru/j/{rid}'
    return text


def normalize_auth_provider(carrier):
    c = (carrier or 'telemost').lower()
    if c == 'jazz':
        return 'wbstream'
    return c


def validate_carrier_transport_pair(carrier, transport):
    if carrier == 'telemost' and transport not in TELEMOST_TRANSPORTS:
        return (
            'telemost supports only vp8channel (use olcbox VP8); '
            'create a meeting at https://telemost.yandex.ru/ and paste the link or room id'
        )
    return None


def transport_params_to_yaml(transport, tp):
    tp = tp or {}
    if transport == 'vp8channel':
        return {
            'vp8': {
                'fps': int(tp.get('vp8-fps', 60)),
                'batch_size': int(tp.get('vp8-batch', 64)),
            }
        }
    if transport == 'seichannel':
        return {
            'sei': {
                'fps': int(tp.get('fps', 60)),
                'batch_size': int(tp.get('batch', 64)),
                'fragment_size': int(tp.get('frag', 900)),
                'ack_timeout_ms': int(tp.get('ack_timeout', 2000)),
            }
        }
    if transport == 'videochannel':
        res = str(tp.get('resolution', '1920x1080')).split('x')
        w, h = (res[0], res[1]) if len(res) == 2 else ('1920', '1080')
        return {
            'video': {
                'codec': tp.get('codec', 'qrcode'),
                'width': int(w),
                'height': int(h),
                'fps': int(tp.get('fps', 30)),
                'bitrate': str(tp.get('bitrate', '2M')),
                'hw': 'nvenc' if tp.get('hw_accel') else 'none',
            }
        }
    return {}


def build_olcrtc_yaml(user):
    provider = normalize_auth_provider(user.get('carrier'))
    transport = user.get('transport', 'vp8channel')
    mode = user.get('mode', 'srv')
    cfg = {
        'mode': mode,
        'auth': {'provider': provider},
        'room': {'id': str(user['room_id'])},
        'crypto': {'key': user['key']},
        'net': {
            'transport': transport,
            'dns': user.get('dns') or load_config().get('dns', '1.1.1.1:53'),
        },
        'data': 'data',
    }
    cfg.update(transport_params_to_yaml(transport, user.get('transport_params')))
    # srv: leave socks proxy unset — direct dial (proxy_port 1081 needs a real upstream SOCKS)
    if mode == 'cnc':
        cfg['socks'] = {
            'host': '127.0.0.1',
            'port': int(user.get('socks_port', 1080)),
        }
    if load_config().get('debug') or user.get('debug'):
        cfg['debug'] = True
    if mode == 'srv':
        cfg['liveness'] = {'interval': '30s', 'timeout': '20s', 'failures': 10}
    return cfg


def write_olcrtc_config(uid, user):
    cfg = build_olcrtc_yaml(user)
    # Use olcrtc-{uid}.yaml — Docker creates a directory if a missing file is bind-mounted.
    rel = os.path.join('configs', f'olcrtc-{uid}.yaml')
    configs_dir = os.path.join(HOST_DATA_DIR, 'configs')
    os.makedirs(configs_dir, exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, 'configs'), exist_ok=True)
    host_path = os.path.join(HOST_DATA_DIR, rel)
    with open(host_path, 'w', encoding='utf-8') as f:
        yaml.dump(cfg, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return host_path


def build_olcrtc_uri(user):
    params_str = ''
    if user.get('transport_params'):
        params_list = [
            f"{k}={v}" for k, v in user['transport_params'].items() if v is not None and v != ''
        ]
        if params_list:
            params_str = '<' + '&'.join(params_list) + '>'
    uri = (
        f"olcrtc://{user['carrier']}?{user['transport']}{params_str}"
        f"@{user['room_id']}#{user['key']}"
    )
    mimo = user.get('profile_name') or user.get('client_id') or ''
    if mimo:
        uri += f"${mimo}"
    return uri

"""
    if "def normalize_room_id_for_carrier" not in s:
        if marker not in s:
            raise SystemExit("TRANSPORTS marker missing")
        s = s.replace(marker, marker + telemost_block)

    # transports-for route
    route = """

@app.route('/api/transports-for/<carrier>', methods=['GET'])
@require_auth
def get_transports_for_carrier(carrier):
    if carrier == 'telemost':
        return jsonify({'transports': ['vp8channel']})
    return jsonify({'transports': TRANSPORTS})
"""
    if "def get_transports_for_carrier" not in s:
        s = s.replace(
            "@app.route('/api/transports', methods=['GET'])\n@require_auth\ndef get_transports():",
            route.strip() + "\n\n@app.route('/api/transports', methods=['GET'])\n@require_auth\ndef get_transports():",
        )

    old_build = """def build_olcrtc_command(user):
    cmd = [
        '-mode', user.get('mode', 'cnc'),
        '-carrier', user['carrier'],
        '-transport', user['transport'],
        '-link', 'direct',
        '-data', '/data',
        '-id', user['room_id'],
        '-client-id', user['client_id'],
        '-key', user['key'],
        '-dns', user.get('dns', '1.1.1.1:53')
    ]

    if user.get('mode') == 'cnc':
        cmd.extend(['-socks-host', '0.0.0.0'])
        cmd.extend(['-socks-port', str(user.get('socks_port', 1080))])
    elif user.get('mode') == 'srv':
        # For srv mode, use local SOCKS5 proxy for traffic control
        cmd.extend(['-socks-proxy', '127.0.0.1'])
        cmd.extend(['-socks-proxy-port', '1081'])

    transport_params = user.get('transport_params', {})
    for key, value in transport_params.items():
        if value is not None and value != '':
            cmd.extend([f'-{key}', str(value)])

    config = load_config()
    if config.get('debug') or user.get('debug'):
        cmd.append('--debug')

    return cmd"""

    new_build = """def build_olcrtc_command(user):
    \"\"\"Legacy name: returns olcrtc argv for universal branch (single config path).\"\"\"
    return ['/config/config.yaml']"""

    if "return ['/config/config.yaml']" not in s:
        if old_build in s:
            s = s.replace(old_build, new_build)
        elif "def build_olcrtc_command" in s:
            a = s.find("def build_olcrtc_command")
            b = s.find("\ndef ", a + 5)
            s = s[:a] + new_build + "\n\n" + s[b + 1 :]
        else:
            raise SystemExit("build_olcrtc_command block not found")

    # start local container: use yaml mount + OLCRTC_IMAGE
    old_run = """        cmd = build_olcrtc_command(user)

        port_bindings = {}
        if user.get('mode') == 'cnc':
            socks_port = user.get('socks_port', 1080)
            port_bindings[1080] = socks_port

        # Environment variables for SOCKS5 proxy (srv mode only)
        environment = {}
        if user.get('mode') == 'srv':
            # Use port 88XX where XX is the instance ID
            socks_port = 8800 + int(uid)
            environment['SOCKS_PORT'] = '1081'
            environment['RX_LIMIT'] = str(user.get('rx_limit', 0))
            environment['TX_LIMIT'] = str(user.get('tx_limit', 0))
            # Expose SOCKS5 proxy port
            port_bindings[1081] = socks_port
            users[uid]['socks_port'] = socks_port

        try:
            container = docker_client.containers.run(
                'olcrtc:latest',
                command=cmd,
                detach=True,
                name=f'olcrtc-{uid}',
                ports=port_bindings,
                environment=environment,
                remove=False,
                network_mode='bridge'
            )"""

    new_run = """        config_host_path = write_olcrtc_config(uid, user)
        cmd = build_olcrtc_command(user)
        volumes = {
            config_host_path: {'bind': '/config/config.yaml', 'mode': 'ro'},
        }

        port_bindings = {}
        if user.get('mode') == 'cnc':
            socks_port = user.get('socks_port', 1080)
            port_bindings[1080] = socks_port

        environment = {}
        if user.get('mode') == 'srv':
            socks_port = 8800 + int(uid)
            environment['SOCKS_PORT'] = '1081'
            environment['RX_LIMIT'] = str(user.get('rx_limit', 0))
            environment['TX_LIMIT'] = str(user.get('tx_limit', 0))
            port_bindings[1081] = socks_port
            users[uid]['socks_port'] = socks_port

        try:
            container = docker_client.containers.run(
                OLCRTC_IMAGE,
                command=cmd,
                detach=True,
                name=f'olcrtc-{uid}',
                ports=port_bindings,
                environment=environment,
                volumes=volumes,
                working_dir='/app',
                remove=False,
                network_mode='bridge',
            )"""

    if "config_host_path = write_olcrtc_config" not in s:
        if old_run not in s:
            raise SystemExit("containers.run block not found")
        s = s.replace(old_run, new_run, 1)

    # remote start
    old_remote = """    cmd = build_olcrtc_command(user)

    port_bindings = {}
    environment = {}

    if user.get('mode') == 'cnc':
        socks_port = user.get('socks_port', 1080)
        port_bindings['1080/tcp'] = socks_port
    elif user.get('mode') == 'srv':
        socks_port = 8800 + int(uid)
        environment['SOCKS_PORT'] = '1081'
        environment['RX_LIMIT'] = str(user.get('rx_limit', 0))
        environment['TX_LIMIT'] = str(user.get('tx_limit', 0))
        port_bindings['1081/tcp'] = socks_port
        users[uid]['socks_port'] = socks_port

    try:
        result = call_node_api(node_id, 'POST', '/containers/start', {
            'image': 'olcrtc:latest',
            'command': cmd,"""

    new_remote = """    config_host_path = write_olcrtc_config(uid, user)
    cmd = build_olcrtc_command(user)

    port_bindings = {}
    environment = {}

    if user.get('mode') == 'cnc':
        socks_port = user.get('socks_port', 1080)
        port_bindings['1080/tcp'] = socks_port
    elif user.get('mode') == 'srv':
        socks_port = 8800 + int(uid)
        environment['SOCKS_PORT'] = '1081'
        environment['RX_LIMIT'] = str(user.get('rx_limit', 0))
        environment['TX_LIMIT'] = str(user.get('tx_limit', 0))
        port_bindings['1081/tcp'] = socks_port
        users[uid]['socks_port'] = socks_port

    try:
        result = call_node_api(node_id, 'POST', '/containers/start', {
            'image': OLCRTC_IMAGE,
            'command': cmd,
            'config_path': config_host_path,"""

    if "'config_path': config_host_path" not in s and old_remote in s:
        s = s.replace(old_remote, new_remote, 1)

    # add_user: client_id optional
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

    new_add = """    required = ['key', 'room_id', 'carrier', 'transport']
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
            'client_id': data.get('client_id', ''),
            'key': data['key'],
            'room_id': room_id,
            'carrier': data['carrier'],"""

    if "room_id = normalize_room_id_for_carrier" not in s.split("def add_user")[1].split("def delete_user")[0]:
        s = s.replace(old_add, new_add)

    # update_user validation
    old_upd_tail = """        if data.get('node_id'):
            user['node_id'] = data['node_id']

        save_users()

        # Restart container if it was running
        if user.get('state') == 'running':
            stop_olcrtc_container(uid)
            start_olcrtc_container(uid)

    return jsonify({'success': True})

@app.route('/api/users/start/<uid>', methods=['POST'])"""

    new_upd_tail = """        if data.get('node_id'):
            user['node_id'] = data['node_id']
        if 'client_id' in data:
            user['client_id'] = data.get('client_id') or ''

        err = validate_carrier_transport_pair(user.get('carrier', ''), user.get('transport', ''))
        if err:
            return jsonify({'error': err}), 400
        user['room_id'] = normalize_room_id_for_carrier(user.get('carrier', ''), user.get('room_id', ''))
        write_olcrtc_config(uid, user)

        save_users()

        if user.get('state') == 'running':
            stop_olcrtc_container(uid)
            start_olcrtc_container(uid)

    return jsonify({'success': True})

@app.route('/api/users/start/<uid>', methods=['POST'])"""

    if "validate_carrier_transport_pair(user.get('carrier'" not in s:
        s = s.replace(old_upd_tail, new_upd_tail)

    # remove duplicate client_id update
    s = s.replace(
        "        if data.get('client_id'):\n            user['client_id'] = data['client_id']\n",
        "",
        1,
    )

    # generate_room_ids telemost + yaml gen
    if "carrier == 'telemost'" not in s.split("def generate_room_ids")[1].split("def generate_uri")[0]:
        s = s.replace(
            "    if carrier not in ['wbstream', 'jazz']:\n"
            "        return jsonify({'error': 'Only wbstream and jazz support room generation'}), 400\n",
            "    if carrier == 'telemost':\n"
            "        return jsonify({\n"
            "            'error': (\n"
            "                'telemost does not support automated room generation; '\n"
            "                'create a meeting at https://telemost.yandex.ru/'\n"
            "            )\n"
            "        }), 400\n"
            "    if carrier not in ['wbstream', 'jazz']:\n"
            "        return jsonify({'error': 'Only wbstream and jazz support room generation'}), 400\n",
        )

    old_gen_run = """        container = docker_client.containers.run(
            'olcrtc:latest',
            command=[
                '-mode', 'gen',
                '-carrier', carrier,
                '-dns', dns,
                '-amount', str(amount)
            ],
            environment={},  # No SOCKS proxy for generation mode
            remove=True,
            detach=False,
            stdout=True,
            stderr=False  # Ignore stderr to avoid debug messages
        )"""

    new_gen_run = """        gen_cfg = {
            'mode': 'gen',
            'auth': {'provider': normalize_auth_provider(carrier)},
            'net': {'dns': dns},
            'gen': {'amount': int(amount)},
        }
        gen_path = os.path.join(HOST_DATA_DIR, 'configs', 'olcrtc-gen.yaml')
        os.makedirs(os.path.dirname(gen_path), exist_ok=True)
        with open(gen_path, 'w', encoding='utf-8') as f:
            yaml.dump(gen_cfg, f, default_flow_style=False, sort_keys=False)
        host_gen = gen_path
        container = docker_client.containers.run(
            OLCRTC_IMAGE,
            command=['/config/config.yaml'],
            volumes={host_gen: {'bind': '/config/config.yaml', 'mode': 'ro'}},
            working_dir='/app',
            environment={},
            remove=True,
            detach=False,
            stdout=True,
            stderr=False,
        )"""

    if "gen_cfg = {" not in s and old_gen_run in s:
        s = s.replace(old_gen_run, new_gen_run)

    # generate_uri universal (no %client_id)
    old_uri = """    uri = f"olcrtc://{user['carrier']}?{user['transport']}{params_str}@{user['room_id']}#{user['key']}%{user['client_id']}"

    if user.get('profile_name'):
        uri += f"${user['profile_name']}"

    return jsonify({'uri': uri})"""

    new_uri = """    uri = build_olcrtc_uri(user)
    return jsonify({
        'uri': uri,
        'config_yaml': build_olcrtc_yaml(user),
        'olcbox_hint': (
            'Universal olcrtc: import URI in olcbox (Telemost + vp8channel). '
            'Client ID in URI is not used; olcbox uses install-id from device.'
        ),
    })"""

    if "build_olcrtc_uri(user)" not in s:
        if old_uri in s:
            s = s.replace(old_uri, new_uri)
        else:
            print("warn: generate_uri block not found")

    # subscription: match by client_id OR profile_name; URI without %
    sub_old = """            if user.get('client_id') != client_id:
                continue

            # Build URI
            params_str = ''
            if user.get('transport_params'):
                params_list = [f"{k}={v}" for k, v in user['transport_params'].items() if v]
                if params_list:
                    params_str = '<' + '&'.join(params_list) + '>'

            uri = f"olcrtc://{user['carrier']}?{user['transport']}{params_str}@{user['room_id']}#{user['key']}%{client_id}"
            if user.get('profile_name'):
                uri += f"${user['profile_name']}"
"""

    sub_new = """            cid = user.get('client_id') or ''
            pname = user.get('profile_name') or ''
            if client_id not in (cid, pname, f'instance-{uid}'):
                continue

            uri = build_olcrtc_uri(user)
"""

    if "client_id not in (cid, pname" not in s and sub_old in s:
        s = s.replace(sub_old, sub_new)

    # subscription list: instances not only client_ids
    old_sub_list = """@app.route('/api/subscription/list', methods=['GET'])
@require_auth
def list_subscriptions():
    \"\"\"List all available client_ids with running instances\"\"\"
    with lock:
        client_ids = set()
        for user in users.values():
            if user.get('state') == 'running' and user.get('client_id'):
                client_ids.add(user['client_id'])

        return jsonify({'client_ids': sorted(list(client_ids))})"""

    new_sub_list = """@app.route('/api/subscription/list', methods=['GET'])
@require_auth
def list_subscriptions():
    \"\"\"List running instances for subscription links\"\"\"
    with lock:
        items = []
        for uid, user in users.items():
            if user.get('state') != 'running':
                continue
            key = user.get('profile_name') or user.get('client_id') or f'instance-{uid}'
            items.append({
                'uid': uid,
                'key': key,
                'profile_name': user.get('profile_name', ''),
                'client_id': user.get('client_id', ''),
            })
        return jsonify({'instances': items, 'client_ids': sorted({i['key'] for i in items})})"""

    if "'instances': items" not in s and old_sub_list in s:
        s = s.replace(old_sub_list, new_sub_list)

    # fix olcbox hwid path
    s = s.replace(
        "        with open('data/last_hwid.txt', 'a') as f:\n",
        "        with open(os.path.join(DATA_DIR, 'last_hwid.txt'), 'a') as f:\n",
    )

    # vp8 defaults for telemost in TRANSPORT_PARAMS
    s = s.replace(
        "        {'name': 'vp8-fps', 'type': 'text', 'default': '25', 'label': 'FPS'},\n"
        "        {'name': 'vp8-batch', 'type': 'text', 'default': '1', 'label': 'Batch Size'}",
        "        {'name': 'vp8-fps', 'type': 'text', 'default': '60', 'label': 'FPS'},\n"
        "        {'name': 'vp8-batch', 'type': 'text', 'default': '64', 'label': 'Batch Size'}",
    )

    APP.write_text(s, encoding="utf-8")
    print("patched", APP)


def patch_frontend():
    s = FRONT.read_text(encoding="utf-8")

    s = s.replace(
        "    if (!newUser.client_id || !newUser.key || !newUser.room_id) {\n"
        "      showNotification('Заполни Client ID, Key и Room ID!', 'error');\n",
        "    if (!newUser.key || !newUser.room_id) {\n"
        "      showNotification('Заполни Key и Room ID!', 'error');\n",
    )

    s = s.replace(
        "    if (!editingUser.client_id) {\n"
        "      showNotification('Заполни Client ID!', 'error');\n"
        "      return;\n"
        "    }\n\n",
        "",
    )

    old_label = '<Label htmlFor="client_id">Client ID</Label>'
    new_label = '<Label htmlFor="client_id">Client ID (необязательно, legacy)</Label>'
    if old_label in s:
        s = s.replace(old_label, new_label, 1)

    old_edit_label = '<Label htmlFor="edit_client_id">Client ID</Label>'
    new_edit_label = '<Label htmlFor="edit_client_id">Client ID (необязательно)</Label>'
    if old_edit_label in s:
        s = s.replace(old_edit_label, new_edit_label, 1)

    s = s.replace(
        '                  placeholder="my-client"\n',
        '                  placeholder="опционально — olcbox использует install-id устройства"\n',
        1,
    )

    # subscription page title
    s = s.replace(
        "              Ссылки на subscription файлы для каждого Client ID\n",
        "              Subscription по имени профиля / instance (Client ID не обязателен)\n",
    )

    # list subscriptions API
    old_fetch = """                    const clientIds = response.data.client_ids;
                    const subscriptionData = clientIds.map(clientId => ({
                      clientId,
                      url: `${window.location.origin.replace(':808', ':3001')}/api/subscription/${clientId}`
                    }));"""
    new_fetch = """                    const items = response.data.instances || [];
                    const subscriptionData = items.map(item => ({
                      clientId: item.key,
                      url: `${window.location.origin.replace(':808', ':3001')}/api/subscription/${encodeURIComponent(item.key)}`
                    }));"""
    if old_fetch in s:
        s = s.replace(old_fetch, new_fetch)

    # user list display
    s = s.replace(
        '<motion.div className="font-mono text-sm">#{user.id} - {user.client_id}</motion.div>',
        '<motion.div className="font-mono text-sm">#{user.id} - {user.profile_name || user.room_id}</motion.div>',
    )

    FRONT.write_text(s, encoding="utf-8")
    print("patched", FRONT)


def main():
    patch_dockerfile()
    patch_compose()
    patch_requirements()
    patch_app()
    patch_frontend()
    print("done — rebuild olcrtc:universal and docker compose")


if __name__ == "__main__":
    main()
