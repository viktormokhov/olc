#!/usr/bin/env python3
"""Telemost-only: remove wbstream/jazz carriers and room generators."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from olcpanel_paths import APP, FRONT  # noqa: E402


def patch_backend() -> None:
    s = APP.read_text(encoding="utf-8")
    s = re.sub(
        r"CARRIERS = \[.*?\]",
        "CARRIERS = ['telemost']",
        s,
        count=1,
    )
    s = s.replace(
        "    if c == 'jazz':\n        return 'wbstream'\n    return c\n",
        "    return c\n",
    )
    s = s.replace("data.get('carrier', 'wbstream')", "data.get('carrier', 'telemost')")
    s = s.replace("user.get('carrier', 'wbstream')", "user.get('carrier', 'telemost')")
    old_gen = """    if carrier == 'telemost':
        return jsonify({
            'error': (
                'telemost does not support automated room generation; '
                'create a meeting at https://telemost.yandex.ru/'
            )
        }), 400
    if carrier not in ['wbstream', 'jazz']:
        return jsonify({'error': 'Only wbstream and jazz support room generation'}), 400"""
    new_gen = """    return jsonify({
        'error': (
            'telemost does not support automated room generation; '
            'paste a meeting link from https://telemost.yandex.ru/ manually'
        )
    }), 400"""
    if old_gen in s:
        s = s.replace(old_gen, new_gen, 1)
    APP.write_text(s, encoding="utf-8")
    print("patched backend telemost-only", APP)


def patch_frontend() -> None:
    s = FRONT.read_text(encoding="utf-8")
    for old, new in [
        ("carrier: 'wbstream'", "carrier: 'telemost'"),
        ("carrier: 'wbstream',", "carrier: 'telemost',"),
        ("userData.carrier || 'wbstream'", "userData.carrier || 'telemost'"),
        ("async (carrier = 'wbstream')", "async (carrier = 'telemost')"),
        ("transport: 'datachannel'", "transport: 'vp8channel'"),
        ("transport: 'datachannel',", "transport: 'vp8channel',"),
    ]:
        s = s.replace(old, new)
    s = s.replace(
        """              <Button onClick={() => setShowGenForm(true)} variant="outline" className="flex-1">
                <Dice5 className="h-4 w-4 mr-2" />
                Генератор
              </Button>""",
        "",
    )
    s = s.replace(
        """                <Select
                  id="carrier"
                  value={newUser.carrier}
                  onChange={(e) => setNewUser({ ...newUser, carrier: e.target.value })}
                >
                  {carriers.map(c => <option key={c} value={c}>{c}</option>)}
                </Select>""",
        """                <Input id="carrier" value="telemost" readOnly className="bg-muted" />
                <p className="text-xs text-muted-foreground">Только Telemost — вставьте ссылку на встречу в Room ID</p>""",
    )
    s = s.replace(
        """                    <Select
                      id="edit_carrier"
                      value={editingUser.carrier}
                      onChange={(e) => {
                        const c = e.target.value;
                        fetchTransports(c).then((list) => {
                          const allowed = list || [];
                          let t = editingUser.transport;
                          if (!allowed.includes(t)) t = allowed[0] || 'vp8channel';
                          setEditingUser((prev) => {
                            return { ...prev, carrier: c, transport: t, transport_params: {} };
                          });
                        }).catch(() => {
                          setEditingUser({ ...editingUser, carrier: c });
                        });
                      }}
                    >
                      {carriers.map(c => <option key={c} value={c}>{c}</option>)}
                    </Select>""",
        """                    <Input id="edit_carrier" value="telemost" readOnly className="bg-muted" />""",
    )
    FRONT.write_text(s, encoding="utf-8")
    print("patched frontend telemost-only", FRONT)


def main() -> None:
    patch_backend()
    patch_frontend()


if __name__ == "__main__":
    main()
