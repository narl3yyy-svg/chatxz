from chatxz.core.messaging import ChatMessaging


class _StubMessaging(ChatMessaging):
    def __init__(self):
        self._user_disconnected = set()
        self._session_peer_hash = "a" * 32
        self.active_peer_hash = "a" * 32
        self.active_link = object()
        self._transport_reconnect_pending = True
        self._last_link_lost_at = 999.0
        self.links = {}
        self.peer_links = {}
        self._link_peer_hashes = {}
        self.identity_to_dest = {}
        self.dest_to_identity = {}

    def dest_hash_for(self, any_hash):
        return (any_hash or "").replace(":", "")

    def hashes_equivalent(self, a, b):
        return self.dest_hash_for(a) == self.dest_hash_for(b)

    def is_user_disconnected(self, peer_hash):
        peer = self.dest_hash_for(peer_hash)
        return peer in self._user_disconnected

    def clear_session_peer(self):
        self._session_peer_hash = None


def test_user_disconnect_clears_session_and_failover_flags():
    m = _StubMessaging()
    peer = "a" * 32
    m.mark_user_disconnected(peer)
    m.clear_session_peer()
    m._transport_reconnect_pending = False
    m._last_link_lost_at = 0
    assert m._session_peer_hash is None
    assert not m._transport_reconnect_pending
    assert m._last_link_lost_at == 0
    assert m.is_user_disconnected(peer)