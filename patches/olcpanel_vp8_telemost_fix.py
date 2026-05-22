"""Patch OlcPanel for Telemost+olcbox (vp8 only, binding token in URI API). Run on server."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from olcpanel_paths import APP, FRONT  # noqa: E402

BINDING_FN = '''

def olcrtc_binding_token(client_id):
    """FNV-1a token embedded in VP8 frames (must match olcrtc vp8channel)."""
    h = 2166136261
    for ch in str(client_id):
        h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return h or 1
'''

OLD_URI_RETURN = """    uri = f"olcrtc://{user['carrier']}?{user['transport']}{params_str}@{user['room_id']}#{user['key']}%{user['client_id']}"

    if user.get('profile_name'):
        uri += f"${user['profile_name']}"

    return jsonify({'uri': uri})"""

NEW_URI_RETURN = """    uri = f"olcrtc://{user['carrier']}?{user['transport']}{params_str}@{user['room_id']}#{user['key']}%{user['client_id']}"

    if user.get('profile_name'):
        uri += f"${user['profile_name']}"

    tok = olcrtc_binding_token(user['client_id'])
    return jsonify({
        'uri': uri,
        'client_id': user['client_id'],
        'binding_token': f'0x{tok:08x}',
        'olcbox_hint': (
            'Import this URI in olcbox (Telemost + VP8). '
            'In srv logs want= must equal binding_token; got= is a foreign VP8 track.'
        ),
    })"""


def patch_app():
    s = APP.read_text(encoding="utf-8")
    s = s.replace(
        "TELEMOST_TRANSPORTS = frozenset({'vp8channel', 'videochannel'})",
        "TELEMOST_TRANSPORTS = frozenset({'vp8channel'})",
    )
    s = s.replace(
        "'telemost supports only vp8channel or videochannel; '",
        "'telemost supports only vp8channel (use olcbox VP8); '",
    )
    s = s.replace(
        "return jsonify({'transports': ['vp8channel', 'videochannel']})",
        "return jsonify({'transports': ['vp8channel']})",
    )
    if "def olcrtc_binding_token" not in s:
        s = s.replace(
            "@app.route('/api/generate-uri/<uid>', methods=['GET'])",
            BINDING_FN + "\n@app.route('/api/generate-uri/<uid>', methods=['GET'])",
        )
    if OLD_URI_RETURN in s:
        s = s.replace(OLD_URI_RETURN, NEW_URI_RETURN)
    elif "binding_token" not in s:
        raise SystemExit("generate_uri block not found")
    APP.write_text(s, encoding="utf-8")
    print("patched", APP)


def patch_front():
    s = FRONT.read_text(encoding="utf-8")
    old = """      const response = await axios.get(`/api/generate-uri/${uid}`);
      await copyToClipboard(response.data.uri, 'URI');"""
    new = """      const response = await axios.get(`/api/generate-uri/${uid}`);
      const { uri, binding_token: bt } = response.data;
      await copyToClipboard(uri, 'URI');
      if (bt) {
        showNotification(`URI copied. В логах srv: want=${bt}`, 'info');
      }"""
    if old in s:
        s = s.replace(old, new, 1)
        FRONT.write_text(s, encoding="utf-8")
        print("patched", FRONT)
    else:
        print("frontend skip (already patched or layout changed)")


if __name__ == "__main__":
    patch_app()
    patch_front()
