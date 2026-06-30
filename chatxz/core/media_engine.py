"""Media engine — Rust-backed when available, Python fallback otherwise."""

from __future__ import annotations

import struct
import time
from typing import Optional

MAGIC = b"CXMZ"
HEADER_SIZE = 17
RNS_LINK_MTU = 1064
RNS_PACKET_OVERHEAD = 120
MAX_CXMZ_BYTES = RNS_LINK_MTU - RNS_PACKET_OVERHEAD
MAX_PAYLOAD = min(480, MAX_CXMZ_BYTES - HEADER_SIZE)
AUDIO_CHUNK_BYTES = 480  # 240 samples @ 16-bit mono — fits MTU with headroom
FRAME_BYTES = 960 * 2

KIND_AUDIO = 1
KIND_VIDEO = 2
KIND_SCREEN = 3
KIND_CONTROL = 4

FLAG_KEYFRAME = 0x01
FLAG_FRAG = 0x02
FLAG_FRAG_LAST = 0x04

_rust_available = False
_rust_module = None

try:
    import chatxz_media as _rust_module  # type: ignore
    _rust_available = True
except ImportError:
    pass


def rust_available() -> bool:
    return _rust_available


def is_media_packet(data: bytes) -> bool:
    if _rust_available:
        return _rust_module.is_media_packet(data)
    return len(data) >= HEADER_SIZE and data[:4] == MAGIC


def parse_packet(data: bytes) -> Optional[tuple]:
    if _rust_available:
        return _rust_module.parse_packet(data)
    if len(data) < HEADER_SIZE or data[:4] != MAGIC:
        return None
    kind = data[5]
    flags = data[6]
    seq = struct.unpack(">I", data[7:11])[0]
    ts = struct.unpack(">I", data[11:15])[0]
    plen = struct.unpack(">H", data[15:17])[0]
    if len(data) < HEADER_SIZE + plen:
        return None
    return kind, flags, seq, ts, data[HEADER_SIZE : HEADER_SIZE + plen]


def packet_fits_mtu(data: bytes, mtu: int = RNS_LINK_MTU) -> bool:
    return len(data) <= max(200, int(mtu or RNS_LINK_MTU) - RNS_PACKET_OVERHEAD)


def _encode_packet(kind: int, flags: int, seq: int, ts: int, payload: bytes) -> bytes:
    plen = min(len(payload), MAX_PAYLOAD)
    hdr = MAGIC + bytes([1, kind, flags])
    hdr += struct.pack(">IIH", seq, ts, plen)
    return hdr + payload[:plen]


class _PythonJitter:
    def __init__(self):
        self._packets: dict[int, tuple] = {}
        self._next = 0
        self._target_ms = 40

    def reset(self):
        self._packets.clear()
        self._next = 0
        self._target_ms = 40

    def push(self, kind, flags, seq, ts, payload):
        self._packets[seq] = (kind, flags, ts, payload)
        while len(self._packets) > 64:
            k = min(self._packets)
            del self._packets[k]
            self._next = k + 1

    def pop(self, now_ms: int):
        if not self._packets:
            return None
        oldest_ts = min(v[2] for v in self._packets.values())
        if now_ms - oldest_ts < self._target_ms and len(self._packets) < 2:
            return None
        seq = self._next if self._next in self._packets else min(self._packets)
        kind, flags, ts, payload = self._packets.pop(seq)
        self._next = seq + 1
        return kind, flags, seq, ts, payload


class _FragmentAssembler:
    """Reassemble fragmented video/screen JPEG payloads."""

    def __init__(self):
        self._bufs: dict[tuple, bytearray] = {}

    def reset(self):
        self._bufs.clear()

    def ingest(self, kind: int, flags: int, ts: int, payload: bytes) -> Optional[bytes]:
        key = (kind, ts)
        if flags & FLAG_FRAG:
            buf = self._bufs.setdefault(key, bytearray())
            buf.extend(payload)
            if flags & FLAG_FRAG_LAST:
                out = bytes(buf)
                self._bufs.pop(key, None)
                return out
            return None
        return payload


class MediaSession:
    """Unified media session — delegates to Rust when built."""

    def __init__(self):
        self._rust = _rust_module.MediaSession() if _rust_available else None
        self._tx_seq = 0
        self._jitter = _PythonJitter()
        self._frags = _FragmentAssembler()

    def reset(self):
        self._tx_seq = 0
        if self._rust:
            self._rust.reset()
        else:
            self._jitter.reset()
        self._frags.reset()

    def encode_audio_frame(self, pcm: bytes) -> bytes:
        if self._rust:
            return bytes(self._rust.encode_audio_frame(pcm))
        return pcm[: min(len(pcm), AUDIO_CHUNK_BYTES)]

    def decode_audio_frame(self, opus: bytes) -> bytes:
        if self._rust:
            return bytes(self._rust.decode_audio_frame(opus))
        return opus

    def _next_seq(self) -> int:
        seq = self._tx_seq
        self._tx_seq = (self._tx_seq + 1) & 0xFFFFFFFF
        return seq

    def packetize_audio(self, payload: bytes, timestamp_ms: int) -> bytes:
        packets = self.packetize_audio_chunks(payload, timestamp_ms)
        return packets[0] if packets else b""

    def packetize_audio_chunks(self, pcm: bytes, timestamp_ms: int) -> list[bytes]:
        if self._rust:
            enc = bytes(self._rust.encode_audio_frame(pcm))
            pkt = bytes(self._rust.packetize_audio(enc, timestamp_ms))
            return [pkt] if pkt else []
        out = []
        for i in range(0, max(1, len(pcm)), AUDIO_CHUNK_BYTES):
            chunk = pcm[i : i + AUDIO_CHUNK_BYTES]
            out.append(_encode_packet(KIND_AUDIO, 0, self._next_seq(), timestamp_ms, chunk))
        return out

    def packetize_video(self, payload: bytes, timestamp_ms: int, keyframe: bool = False) -> bytes:
        packets = self.packetize_video_chunks(payload, timestamp_ms, keyframe=keyframe)
        return packets[0] if packets else b""

    def packetize_screen(self, payload: bytes, timestamp_ms: int, keyframe: bool = False) -> bytes:
        packets = self.packetize_screen_chunks(payload, timestamp_ms, keyframe=keyframe)
        return packets[0] if packets else b""

    def _packetize_fragments(self, kind: int, payload: bytes, timestamp_ms: int, keyframe: bool) -> list[bytes]:
        if not payload:
            return []
        if len(payload) <= MAX_PAYLOAD:
            flags = FLAG_KEYFRAME if keyframe else 0
            return [_encode_packet(kind, flags, self._next_seq(), timestamp_ms, payload)]
        out = []
        offset = 0
        while offset < len(payload):
            chunk = payload[offset : offset + MAX_PAYLOAD]
            offset += len(chunk)
            flags = FLAG_FRAG
            if keyframe and offset >= len(payload):
                flags |= FLAG_KEYFRAME
            if offset >= len(payload):
                flags |= FLAG_FRAG_LAST
            out.append(_encode_packet(kind, flags, self._next_seq(), timestamp_ms, chunk))
        return out

    def packetize_video_chunks(self, payload: bytes, timestamp_ms: int, keyframe: bool = False) -> list[bytes]:
        if self._rust:
            pkt = bytes(self._rust.packetize_video(payload, timestamp_ms, keyframe))
            return [pkt] if pkt else []
        return self._packetize_fragments(KIND_VIDEO, payload, timestamp_ms, keyframe)

    def packetize_screen_chunks(self, payload: bytes, timestamp_ms: int, keyframe: bool = False) -> list[bytes]:
        if self._rust:
            pkt = bytes(self._rust.packetize_screen(payload, timestamp_ms, keyframe))
            return [pkt] if pkt else []
        return self._packetize_fragments(KIND_SCREEN, payload, timestamp_ms, keyframe)

    def ingest_packet(self, data: bytes) -> Optional[tuple]:
        if self._rust:
            return self._rust.ingest_packet(data)
        parsed = parse_packet(data)
        if not parsed:
            return None
        kind, flags, seq, ts, payload = parsed
        if kind in (KIND_VIDEO, KIND_SCREEN) and (flags & (FLAG_FRAG | FLAG_FRAG_LAST)):
            assembled = self._frags.ingest(kind, flags, ts, payload)
            if not assembled:
                return parsed
            payload = assembled
            flags = flags & FLAG_KEYFRAME
        self._jitter.push(kind, flags, seq, ts, payload)
        return kind, flags, seq, ts, payload

    def pop_audio(self, now_ms: Optional[int] = None) -> Optional[tuple]:
        now = now_ms if now_ms is not None else int(time.time() * 1000) & 0xFFFFFFFF
        if self._rust:
            return self._rust.pop_audio(now)
        item = self._jitter.pop(now)
        if not item or item[0] != KIND_AUDIO:
            return None
        _, _, _, _, payload = item
        decoded = self.decode_audio_frame(payload)
        return decoded, payload

    def pop_audio_immediate(self) -> Optional[tuple]:
        if self._rust:
            try:
                return self._rust.pop_audio(int(time.time() * 1000) + 10000)
            except Exception:
                return None
        if not self._jitter._packets:
            return None
        seq = (
            self._jitter._next
            if self._jitter._next in self._jitter._packets
            else min(self._jitter._packets)
        )
        kind, flags, ts, payload = self._jitter._packets.pop(seq)
        self._jitter._next = seq + 1
        if kind != KIND_AUDIO:
            return None
        decoded = self.decode_audio_frame(payload)
        return decoded, payload

    def jitter_depth(self) -> int:
        if self._rust:
            return self._rust.jitter_depth()
        return len(self._jitter._packets)

    def jitter_delay_ms(self) -> int:
        if self._rust:
            return self._rust.jitter_delay_ms()
        return self._jitter._target_ms