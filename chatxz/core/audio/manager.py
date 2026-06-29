"""Single-owner native call audio lifecycle — one engine, hard stop on hang-up."""

from __future__ import annotations

import threading
import time
from typing import Callable, List, Optional, Tuple

from chatxz.core.audio.engine import CallAudioEngine, call_audio_available
from chatxz.core.audio.opus import OPUS_CODEC
from chatxz.core.audio.session import STATE_ACTIVE

PendingFrame = Tuple[int, str, str]


class CallAudioManager:
    """Owns at most one CallAudioEngine; invalidates in-flight starts on stop."""

    def __init__(self):
        self._lock = threading.Lock()
        self._engine: Optional[CallAudioEngine] = None
        self._generation = 0
        self._session_id: Optional[str] = None
        self._pending: List[PendingFrame] = []
        self._send_hook: Optional[Callable[[str, str], bool]] = None
        self._voice_state = lambda: STATE_ACTIVE

    def configure(
        self,
        *,
        send_hook: Callable[[str, str], bool],
        voice_state,
    ) -> None:
        self._send_hook = send_hook
        self._voice_state = voice_state

    @property
    def engine(self) -> Optional[CallAudioEngine]:
        with self._lock:
            return self._engine

    def session_id(self) -> Optional[str]:
        with self._lock:
            return self._session_id

    def is_active(self) -> bool:
        with self._lock:
            return self._session_id is not None

    def _send_audio(self, b64: str, codec: str) -> bool:
        if not self.is_active():
            return False
        if self._voice_state() != STATE_ACTIVE:
            return False
        hook = self._send_hook
        if not hook:
            return False
        return bool(hook(b64, codec))

    def begin_session(self, call_id: str) -> None:
        cid = (call_id or "").strip() or None
        with self._lock:
            self._generation += 1
            self._session_id = cid
            self._pending.clear()

    def end_session(self, *, wait: bool = True) -> None:
        """Immediate stop — must silence capture/playback in console."""
        with self._lock:
            self._generation += 1
            self._session_id = None
            engine = self._engine
            self._engine = None
            self._pending.clear()
        if engine:
            try:
                engine.stop_fast()
                if wait:
                    engine.wait_stopped(timeout=0.5)
            except Exception:
                pass
            print("[call-audio] Engine stopped")

    def abandon(self) -> None:
        """Non-blocking teardown for signal shutdown."""
        with self._lock:
            self._generation += 1
            self._session_id = None
            engine = self._engine
            self._engine = None
            self._pending.clear()
        if engine:
            try:
                engine.stop_abandon(timeout=0.3)
            except Exception:
                pass

    def stop(self) -> None:
        self.end_session()

    def deliver_frame(self, seq: int, data: str, codec: str = OPUS_CODEC) -> None:
        if not data:
            return
        with self._lock:
            engine = self._engine
            if not engine or not engine.is_running():
                self._pending.append((int(seq or 0), data, codec or OPUS_CODEC))
                if len(self._pending) > 64:
                    del self._pending[0]
                return
        engine.receive_frame(seq, data, codec)

    def drain_pending(self) -> List[PendingFrame]:
        with self._lock:
            pending = list(self._pending)
            self._pending.clear()
        return pending

    def flush_pending(self) -> None:
        with self._lock:
            pending = list(self._pending)
            self._pending.clear()
            engine = self._engine
        if not engine:
            return
        for seq, data, codec in pending:
            try:
                engine.receive_frame(seq, data, codec)
            except Exception:
                pass

    def start(self) -> bool:
        if not call_audio_available():
            print("[call-audio] Native unavailable — install libopus + pyaudio")
            return False
        with self._lock:
            if self._engine and self._engine.is_running():
                return True
            self._generation += 1
            my_gen = self._generation
            old = self._engine
            self._engine = None

        if old:
            try:
                old.stop_fast()
                old.wait_stopped(timeout=1.0)
            except Exception:
                pass

        engine = CallAudioEngine(self._send_audio)
        ok = False
        try:
            ok = engine.start()
        except Exception as exc:
            print(f"[call-audio] Engine start exception: {exc}")
            engine.stop_fast()

        with self._lock:
            if my_gen != self._generation:
                engine.stop_fast()
                return False
            if ok:
                self._engine = engine
            else:
                print("[call-audio] Native engine failed — browser Opus fallback")
                return False

        self.flush_pending()
        return True

    def stats(self) -> dict:
        with self._lock:
            engine = self._engine
        if not engine:
            return {}
        return engine.stats()