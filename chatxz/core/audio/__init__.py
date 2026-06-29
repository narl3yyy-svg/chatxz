"""Voice call stack over RNS — Opus 48 kHz / 20 ms frames.

Audio pipeline:
  capture → Opus encode → CALL_AUDIO (messaging/RNS)
  CALL_AUDIO receive → Opus decode → jitter buffer → playback

Signaling (invite/accept/end) is in session.py; desktop I/O in engine.py;
Android bridge in android.py.
"""

from chatxz.core.audio.android import (
    clear_handlers,
    is_active as android_audio_active,
    on_encoded_opus,
    play_incoming_opus,
    register_handlers,
)
from chatxz.core.audio.engine import CallAudioEngine, VoiceCallAudio, call_audio_available
from chatxz.core.audio.manager import CallAudioManager
from chatxz.core.audio.jitter import SILENCE_PCM, VoiceJitterBuffer
from chatxz.core.audio.opus import (
    OPUS_CODEC,
    OPUS_FRAME_SAMPLES,
    OPUS_SAMPLE_RATE,
    OpusDecoder,
    OpusEncoder,
    opus_available,
    opus_unavailable_reason,
)
from chatxz.core.audio.session import (
    CALL_ACCEPT,
    CALL_AUDIO,
    CALL_AUDIO_MAX_OPUS_BYTES,
    CALL_END,
    CALL_INVITE,
    CALL_REJECT,
    CALL_TYPES,
    STATE_ACTIVE,
    STATE_IDLE,
    STATE_INCOMING,
    STATE_OUTGOING,
    VoiceCallSession,
    estimate_call_audio_packet_size,
    max_audio_bytes_for_mtu,
    new_call_id,
    parse_call_payload,
    split_call_audio_b64,
)

__all__ = [
    "CALL_ACCEPT",
    "CALL_AUDIO",
    "CALL_AUDIO_MAX_OPUS_BYTES",
    "CALL_END",
    "CALL_INVITE",
    "CALL_REJECT",
    "CALL_TYPES",
    "CallAudioEngine",
    "CallAudioManager",
    "OPUS_CODEC",
    "OPUS_FRAME_SAMPLES",
    "OPUS_SAMPLE_RATE",
    "OpusDecoder",
    "OpusEncoder",
    "SILENCE_PCM",
    "STATE_ACTIVE",
    "STATE_IDLE",
    "STATE_INCOMING",
    "STATE_OUTGOING",
    "VoiceCallAudio",
    "VoiceCallSession",
    "VoiceJitterBuffer",
    "android_audio_active",
    "call_audio_available",
    "clear_handlers",
    "estimate_call_audio_packet_size",
    "max_audio_bytes_for_mtu",
    "new_call_id",
    "on_encoded_opus",
    "opus_available",
    "opus_unavailable_reason",
    "parse_call_payload",
    "play_incoming_opus",
    "register_handlers",
    "split_call_audio_b64",
]