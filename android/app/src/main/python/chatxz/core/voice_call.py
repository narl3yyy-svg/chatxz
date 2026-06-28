"""Duplex voice call signaling and audio frames over RNS links."""

import json
import time
import uuid

CALL_INVITE = "__call_invite"
CALL_ACCEPT = "__call_accept"
CALL_REJECT = "__call_reject"
CALL_END = "__call_end"
CALL_AUDIO = "__call_audio"

CALL_TYPES = frozenset({
    CALL_INVITE,
    CALL_ACCEPT,
    CALL_REJECT,
    CALL_END,
    CALL_AUDIO,
})

STATE_IDLE = "idle"
STATE_OUTGOING = "outgoing"
STATE_INCOMING = "incoming"
STATE_ACTIVE = "active"


def new_call_id():
    return str(uuid.uuid4())[:12]


def parse_call_payload(content):
    if not content:
        return {}
    try:
        data = json.loads(content)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


class VoiceCallSession:
    """Tracks one duplex call per messaging backend."""

    def __init__(self):
        self.state = STATE_IDLE
        self.call_id = ""
        self.peer_hash = ""
        self.transport = ""
        self.started_at = 0.0
        self._audio_seq_out = 0

    def reset(self):
        self.state = STATE_IDLE
        self.call_id = ""
        self.peer_hash = ""
        self.transport = ""
        self.started_at = 0.0
        self._audio_seq_out = 0

    def is_busy(self):
        return self.state in (STATE_OUTGOING, STATE_INCOMING, STATE_ACTIVE)

    def begin_outgoing(self, peer_hash, transport="lan"):
        self.reset()
        self.state = STATE_OUTGOING
        self.call_id = new_call_id()
        self.peer_hash = (peer_hash or "").replace(":", "")
        self.transport = (transport or "lan").strip().lower() or "lan"
        return self.call_id

    def begin_incoming(self, call_id, peer_hash, transport="lan"):
        self.reset()
        self.state = STATE_INCOMING
        self.call_id = (call_id or new_call_id()).strip()
        self.peer_hash = (peer_hash or "").replace(":", "")
        self.transport = (transport or "lan").strip().lower() or "lan"

    def activate(self, call_id=None):
        if call_id and self.call_id and call_id != self.call_id:
            return False
        self.state = STATE_ACTIVE
        self.started_at = time.time()
        return True

    def end(self):
        cid = self.call_id
        peer = self.peer_hash
        self.reset()
        return cid, peer

    def next_audio_seq(self):
        self._audio_seq_out += 1
        return self._audio_seq_out