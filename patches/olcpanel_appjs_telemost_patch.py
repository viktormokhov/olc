"""Patch OlcPanel frontend App.js for telemost (run on server)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from olcpanel_paths import FRONT as APP  # noqa: E402  # patches App.js only


def main():
    s = APP.read_text(encoding="utf-8")

    old_fetch = """  const fetchTransports = async () => {
    try {
      const response = await axios.get('/api/transports');
      setTransports(response.data.transports);
    } catch (err) {
      console.error('Failed to fetch transports:', err);
    }
  };"""

    new_fetch = """  const fetchTransports = async (carrier = 'wbstream') => {
    try {
      const response = await axios.get(`/api/transports-for/${encodeURIComponent(carrier)}`);
      const list = response.data.transports;
      setTransports(list);
      return list;
    } catch (err) {
      console.error('Failed to fetch transports:', err);
      return null;
    }
  };"""

    if "encodeURIComponent(carrier)" not in s:
        if old_fetch not in s:
            raise SystemExit("old_fetch not found")
        s = s.replace(old_fetch, new_fetch, 1)

    old_auth_effect = """  useEffect(() => {
    if (isAuthenticated) {
      fetchConfig();
      fetchCarriers();
      fetchTransports();
      fetchStatus();
      fetchNodes();"""

    new_auth_effect = """  useEffect(() => {
    if (isAuthenticated) {
      fetchConfig();
      fetchCarriers();
      fetchStatus();
      fetchNodes();"""

    if "fetchCarriers();\n      fetchTransports();" in s:
        s = s.replace(old_auth_effect, new_auth_effect, 1)

    hook_anchor = """  }, [newUser.transport, isAuthenticated]);

  const fetchConfig = async () => {"""

    hook_insert = """  }, [newUser.transport, isAuthenticated]);

  useEffect(() => {
    if (isAuthenticated && newUser.carrier) {
      fetchTransports(newUser.carrier);
    }
  }, [newUser.carrier, isAuthenticated]);

  useEffect(() => {
    if (!isAuthenticated || !transports.length) return;
    if (!transports.includes(newUser.transport)) {
      const t = transports[0];
      setNewUser(prev => ({ ...prev, transport: t, transport_params: {} }));
      fetchTransportParams(t);
    }
  }, [transports, isAuthenticated, newUser.transport]);

  const fetchConfig = async () => {"""

    if "if (isAuthenticated && newUser.carrier)" not in s:
        if hook_anchor not in s:
            raise SystemExit("hook anchor not found")
        s = s.replace(hook_anchor, hook_insert, 1)

    old_edit = """  const editUser = async (user) => {
    try {
      const response = await axios.get(`/api/users/get/${user.id}`);
      const userData = response.data;
      setEditingUser({
        id: user.id,
        client_id: userData.client_id || '',
        key: userData.key || '',
        room_id: userData.room_id || '',
        carrier: userData.carrier || 'wbstream',
        transport: userData.transport || 'datachannel',
        mode: userData.mode || 'srv',
        socks_port: userData.socks_port || 1080,
        transport_params: userData.transport_params || {},
        debug: userData.debug || false,
        profile_name: userData.profile_name || '',
        dns: userData.dns || '1.1.1.1:53',
        node_id: userData.node_id || 'local',
        rx_limit: userData.rx_limit || 0,
        tx_limit: userData.tx_limit || 0,
      });
      setShowEditForm(true);
      fetchTransportParams(userData.transport || 'datachannel');
    } catch (err) {
      showNotification('Ошибка загрузки данных', 'error');
    }
  };"""

    new_edit = """  const editUser = async (user) => {
    try {
      const response = await axios.get(`/api/users/get/${user.id}`);
      const userData = response.data;
      const carrier = userData.carrier || 'wbstream';
      const allowed = await fetchTransports(carrier) || [];
      let transport = userData.transport || 'datachannel';
      if (!allowed.includes(transport)) {
        transport = allowed[0] || 'vp8channel';
      }
      setEditingUser({
        id: user.id,
        client_id: userData.client_id || '',
        key: userData.key || '',
        room_id: userData.room_id || '',
        carrier,
        transport,
        mode: userData.mode || 'srv',
        socks_port: userData.socks_port || 1080,
        transport_params: userData.transport_params || {},
        debug: userData.debug || false,
        profile_name: userData.profile_name || '',
        dns: userData.dns || '1.1.1.1:53',
        node_id: userData.node_id || 'local',
        rx_limit: userData.rx_limit || 0,
        tx_limit: userData.tx_limit || 0,
      });
      setShowEditForm(true);
      fetchTransportParams(transport);
    } catch (err) {
      showNotification('Ошибка загрузки данных', 'error');
    }
  };"""

    if "const allowed = await fetchTransports(carrier)" not in s:
        if old_edit not in s:
            raise SystemExit("old_edit not found")
        s = s.replace(old_edit, new_edit, 1)

    old_ec = """                      onChange={(e) => setEditingUser({ ...editingUser, carrier: e.target.value })}
                    >
                      {carriers.map(c => <option key={c} value={c}>{c}</option>)}
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="edit_transport">Transport</Label>
                    <Select
                      id="edit_transport"
                      value={editingUser.transport}
                      onChange={(e) => {
                        setEditingUser({ ...editingUser, transport: e.target.value, transport_params: {} });
                        fetchTransportParams(e.target.value);
                      }}
                    >"""

    new_ec = """                      onChange={async (e) => {
                        const c = e.target.value;
                        try {
                          const r = await axios.get(`/api/transports-for/${encodeURIComponent(c)}`);
                          const allowed = r.data.transports || [];
                          setTransports(allowed);
                          setEditingUser(prev => {
                            let t = prev.transport;
                            if (!allowed.includes(t)) t = allowed[0] || 'vp8channel';
                            fetchTransportParams(t);
                            return { ...prev, carrier: c, transport: t, transport_params: {} };
                          });
                        } catch (err) {
                          console.error(err);
                          setEditingUser({ ...editingUser, carrier: c });
                        }
                      }}
                    >
                      {carriers.map(c => <option key={c} value={c}>{c}</option>)}
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="edit_transport">Transport</Label>
                    <Select
                      id="edit_transport"
                      value={editingUser.transport}
                      onChange={(e) => {
                        setEditingUser({ ...editingUser, transport: e.target.value, transport_params: {} });
                        fetchTransportParams(e.target.value);
                      }}
                    >"""

    if old_ec in s:
        s = s.replace(old_ec, new_ec, 1)

    old_room = """                <Input
                  id="room_id"
                  placeholder="room-id"
                  value={newUser.room_id}
                  onChange={(e) => setNewUser({ ...newUser, room_id: e.target.value })}
                  className="flex-1"
                />"""

    new_room = """                <Input
                  id="room_id"
                  placeholder={newUser.carrier === 'telemost' ? 'https://telemost.yandex.ru/j/... или id' : 'room-id'}
                  value={newUser.room_id}
                  onChange={(e) => setNewUser({ ...newUser, room_id: e.target.value })}
                  onBlur={(e) => {
                    if (newUser.carrier !== 'telemost') return;
                    const v = e.target.value;
                    const m = v.match(/(?:https?:\\/\\/)?(?:www\\.)?telemost\\.yandex\\.ru\\/j\\/([^\\/?#]+)/i);
                    if (m) setNewUser(prev => ({ ...prev, room_id: m[1] }));
                  }}
                  className="flex-1"
                />"""

    if 'placeholder={newUser.carrier ===' not in s and old_room in s:
        s = s.replace(old_room, new_room, 1)

    old_eroom = """                    <Input
                      id="edit_room_id"
                      placeholder="room-id"
                      value={editingUser.room_id}
                      onChange={(e) => setEditingUser({ ...editingUser, room_id: e.target.value })}
                      className="flex-1"
                    />"""

    new_eroom = """                    <Input
                      id="edit_room_id"
                      placeholder={editingUser.carrier === 'telemost' ? 'https://telemost.yandex.ru/j/... или id' : 'room-id'}
                      value={editingUser.room_id}
                      onChange={(e) => setEditingUser({ ...editingUser, room_id: e.target.value })}
                      onBlur={(e) => {
                        if (editingUser.carrier !== 'telemost') return;
                        const v = e.target.value;
                        const m = v.match(/(?:https?:\\/\\/)?(?:www\\.)?telemost\\.yandex\\.ru\\/j\\/([^\\/?#]+)/i);
                        if (m) setEditingUser(prev => ({ ...prev, room_id: m[1] }));
                      }}
                      className="flex-1"
                    />"""

    if 'placeholder={editingUser.carrier ===' not in s and old_eroom in s:
        s = s.replace(old_eroom, new_eroom, 1)

    anchor_upd = """  const updateUser = async () => {
    if (!editingUser.client_id) {
      showNotification('Заполни Client ID!', 'error');
      return;
    }
    try {
      await axios.post(`/api/users/update/${editingUser.id}`, editingUser);
      setEditingUser(null);
      setShowEditForm(false);
      fetchStatus();
      showNotification('Инстанс обновлён');
    } catch (err) {
      showNotification('Ошибка обновления', 'error');
    }
  };"""

    repl_upd = """  const updateUser = async () => {
    if (!editingUser.client_id) {
      showNotification('Заполни Client ID!', 'error');
      return;
    }
    try {
      await axios.post(`/api/users/update/${editingUser.id}`, editingUser);
      setEditingUser(null);
      setShowEditForm(false);
      fetchStatus();
      showNotification('Инстанс обновлён');
    } catch (err) {
      const msg = err.response?.data?.error || err.message || 'Ошибка обновления';
      showNotification(msg, 'error');
    }
  };"""

    if "const msg = err.response?.data?.error" not in s and anchor_upd in s:
        s = s.replace(anchor_upd, repl_upd, 1)

    APP.write_text(s, encoding="utf-8")
    print("patched", APP)


if __name__ == "__main__":
    main()
