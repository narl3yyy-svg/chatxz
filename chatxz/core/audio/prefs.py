"""Persisted voice I/O preferences (Stoat-style device pinning for chatxz P2P calls)."""

from __future__ import annotations

import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

AUDIO_DEVICE_AUTO = -1

DEFAULT_AUDIO_SETTINGS: Dict[str, Any] = {
    "audio_input_device": AUDIO_DEVICE_AUTO,
    "audio_output_device": AUDIO_DEVICE_AUTO,
    "audio_input_name": "",
    "audio_output_name": "",
    "audio_pulse_source": "",
    "audio_pulse_sink": "",
    "browser_audio_input_id": "",
    "browser_audio_output_id": "",
}


def merge_audio_defaults(settings: Dict[str, Any]) -> Dict[str, Any]:
    for key, val in DEFAULT_AUDIO_SETTINGS.items():
        settings.setdefault(key, val)
    return settings


def normalize_prefs(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    src = dict(DEFAULT_AUDIO_SETTINGS)
    if raw:
        src.update({k: raw.get(k, v) for k, v in DEFAULT_AUDIO_SETTINGS.items()})
    try:
        src["audio_input_device"] = int(src.get("audio_input_device", AUDIO_DEVICE_AUTO))
    except (TypeError, ValueError):
        src["audio_input_device"] = AUDIO_DEVICE_AUTO
    try:
        src["audio_output_device"] = int(src.get("audio_output_device", AUDIO_DEVICE_AUTO))
    except (TypeError, ValueError):
        src["audio_output_device"] = AUDIO_DEVICE_AUTO
    for key in (
        "audio_input_name",
        "audio_output_name",
        "audio_pulse_source",
        "audio_pulse_sink",
        "browser_audio_input_id",
        "browser_audio_output_id",
    ):
        src[key] = str(src.get(key) or "").strip()
    src["pin_input"] = is_input_pinned(src)
    src["pin_output"] = is_output_pinned(src)
    return src


def is_input_pinned(prefs: Dict[str, Any]) -> bool:
    return (
        int(prefs.get("audio_input_device", AUDIO_DEVICE_AUTO)) >= 0
        or bool((prefs.get("audio_input_name") or "").strip())
        or bool((prefs.get("audio_pulse_source") or "").strip())
    )


def is_output_pinned(prefs: Dict[str, Any]) -> bool:
    return (
        int(prefs.get("audio_output_device", AUDIO_DEVICE_AUTO)) >= 0
        or bool((prefs.get("audio_output_name") or "").strip())
        or bool((prefs.get("audio_pulse_sink") or "").strip())
    )


def apply_pulse_prefs(prefs: Dict[str, Any]) -> None:
    """Apply saved Pulse source/sink before PyAudio opens streams."""
    if sys.platform not in ("linux", "linux2"):
        return
    src = (prefs.get("audio_pulse_source") or "").strip()
    sink = (prefs.get("audio_pulse_sink") or "").strip()
    for cmd in (
        (["pactl", "set-default-source", src], src),
        (["pactl", "set-default-sink", sink], sink),
    ):
        if not cmd[1]:
            continue
        try:
            proc = subprocess.run(
                cmd[0],
                capture_output=True,
                timeout=2,
                check=False,
            )
            if proc.returncode == 0:
                label = "source" if "source" in cmd[0][1] else "sink"
                print(f"[call-audio] Pulse {label} → {cmd[1]}")
        except Exception:
            pass


def resolve_device_index(
    pa,
    *,
    input_device: bool,
    index: int,
    name: str,
    ranked: List[Tuple[int, str, int]],
) -> Tuple[Optional[int], Optional[str]]:
    """Resolve pinned index/name against current PyAudio device list."""
    ch_key = "maxInputChannels" if input_device else "maxOutputChannels"
    if index >= 0:
        try:
            info = pa.get_device_info_by_index(index)
            if int(info.get(ch_key, 0) or 0) >= 1:
                return index, str(info.get("name") or f"device {index}")
        except Exception:
            pass
    needle = (name or "").strip().lower()
    if needle:
        for idx, dev_name, _score in ranked:
            if needle in (dev_name or "").lower():
                return idx, dev_name
        try:
            for i in range(pa.get_device_count()):
                info = pa.get_device_info_by_index(i)
                if int(info.get(ch_key, 0) or 0) < 1:
                    continue
                dev_name = str(info.get("name") or "")
                if needle in dev_name.lower():
                    return i, dev_name
        except Exception:
            pass
    return None, None