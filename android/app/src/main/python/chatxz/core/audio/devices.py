"""Microphone and speaker device selection for desktop voice calls.

Linux (Arch/Ubuntu): uses pactl when a real capture source exists; otherwise opens
direct ALSA hw devices (bypassing Pulse default/monitor routing).
"""

from __future__ import annotations

import struct
import subprocess
import sys
import threading
import time
from typing import List, Optional, Tuple

# Set by prepare_linux_audio(): bypass Pulse default for PyAudio device ranking.
_PULSE_CAPTURE_BYPASS = False
# Set when Pulse default sink is HDMI — route playback through Pulse "default".
_PULSE_PLAYBACK_HDMI = False


def resample_pcm_s16(pcm_s16: bytes, from_rate: int, to_rate: int) -> bytes:
    """Linear resample mono s16le PCM between sample rates."""
    if not pcm_s16 or from_rate <= 0 or to_rate <= 0 or from_rate == to_rate:
        return pcm_s16
    count = len(pcm_s16) // 2
    if count < 1:
        return pcm_s16
    samples = struct.unpack(f"<{count}h", pcm_s16[: count * 2])
    out_len = max(1, int(round(count * to_rate / from_rate)))
    out = []
    for i in range(out_len):
        src = i * from_rate / to_rate
        idx = int(src)
        frac = src - idx
        s0 = samples[min(idx, count - 1)]
        s1 = samples[min(idx + 1, count - 1)]
        val = int(round(s0 + (s1 - s0) * frac))
        out.append(max(-32768, min(32767, val)))
    return struct.pack(f"<{len(out)}h", *out)


def stream_sample_rate(stream, fallback: int = 48000) -> int:
    try:
        rate = int(getattr(stream, "_rate", 0) or 0)
        if rate > 0:
            return rate
    except Exception:
        pass
    return fallback


def pcm_peak(pcm_s16: bytes) -> int:
    if len(pcm_s16) < 2:
        return 0
    count = len(pcm_s16) // 2
    samples = struct.unpack(f"<{count}h", pcm_s16[: count * 2])
    return max(abs(s) for s in samples) if samples else 0


def pulse_available() -> bool:
    if sys.platform not in ("linux", "linux2"):
        return False
    try:
        proc = subprocess.run(
            ["pactl", "info"],
            capture_output=True,
            timeout=2,
            check=False,
        )
        return proc.returncode == 0
    except Exception:
        return False


def pulse_list_sources() -> List[str]:
    if sys.platform not in ("linux", "linux2"):
        return []
    try:
        proc = subprocess.run(
            ["pactl", "list", "short", "sources"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if proc.returncode != 0:
            return []
        names: List[str] = []
        for line in (proc.stdout or "").splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                name = parts[1].strip()
                if name:
                    names.append(name)
        return names
    except Exception:
        return []


def pulse_list_sinks() -> List[str]:
    if sys.platform not in ("linux", "linux2"):
        return []
    try:
        proc = subprocess.run(
            ["pactl", "list", "short", "sinks"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if proc.returncode != 0:
            return []
        names: List[str] = []
        for line in (proc.stdout or "").splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                name = parts[1].strip()
                if name:
                    names.append(name)
        return names
    except Exception:
        return []


def pulse_best_capture_source() -> Optional[str]:
    sources = pulse_list_sources()
    ranked: List[Tuple[int, str]] = []
    for name in sources:
        low = name.lower()
        if ".monitor" in low or "monitor of" in low:
            continue
        score = 0
        if low.startswith("alsa_input"):
            score += 80
        for kw in ("microphone", "mic", "headset", "webcam", "usb", "analog"):
            if kw in low:
                score += 20
        for kw in ("hdmi", "spdif", "output", "sink"):
            if kw in low:
                score -= 40
        if score > -20:
            ranked.append((score, name))
    if not ranked:
        return None
    ranked.sort(key=lambda t: t[0], reverse=True)
    return ranked[0][1]


def pulse_best_playback_sink() -> Optional[str]:
    sinks = pulse_list_sinks()
    ranked: List[Tuple[int, str]] = []
    for name in sinks:
        low = name.lower()
        if ".monitor" in low:
            continue
        score = 0
        if low.startswith("alsa_output"):
            score += 60
        for kw in ("analog", "speaker", "headphone", "headset", "usb", "built-in"):
            if kw in low:
                score += 25
        for kw in ("hdmi", "spdif", "iec958"):
            if kw in low:
                score -= 50
        ranked.append((score, name))
    if not ranked:
        return None
    ranked.sort(key=lambda t: t[0], reverse=True)
    best_score, best = ranked[0]
    if best_score < 0:
        return None
    return best


def pulse_default_source() -> Optional[str]:
    if sys.platform not in ("linux", "linux2"):
        return None
    try:
        proc = subprocess.run(
            ["pactl", "get-default-source"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if proc.returncode == 0:
            name = (proc.stdout or "").strip()
            if name and ".monitor" not in name.lower():
                return name
    except Exception:
        pass
    return pulse_best_capture_source()


def pulse_default_sink() -> Optional[str]:
    if sys.platform not in ("linux", "linux2"):
        return None
    try:
        proc = subprocess.run(
            ["pactl", "get-default-sink"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if proc.returncode == 0:
            return (proc.stdout or "").strip() or None
    except Exception:
        pass
    return None


def ensure_pulse_capture_source() -> Optional[str]:
    """If Pulse default is a monitor, switch to a real microphone source."""
    if sys.platform not in ("linux", "linux2"):
        return None
    try:
        proc = subprocess.run(
            ["pactl", "get-default-source"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        current = (proc.stdout or "").strip() if proc.returncode == 0 else ""
        if current and ".monitor" not in current.lower():
            return current
        best = pulse_best_capture_source()
        if best:
            subprocess.run(
                ["pactl", "set-default-source", best],
                capture_output=True,
                timeout=2,
                check=False,
            )
            print(f"[call-audio] Pulse default source → {best}")
            return best
        if current:
            print(
                f"[call-audio] Pulse has no mic source (default={current}) "
                "— using direct ALSA capture"
            )
    except Exception:
        pass
    return pulse_default_source()


def ensure_pulse_playback_sink() -> Optional[str]:
    """Prefer analog speaker output when Pulse default is HDMI."""
    if sys.platform not in ("linux", "linux2"):
        return None
    try:
        current = pulse_default_sink() or ""
        low = current.lower()
        if current and "hdmi" not in low and "spdif" not in low and "iec958" not in low:
            return current
        best = pulse_best_playback_sink()
        if best and best != current:
            subprocess.run(
                ["pactl", "set-default-sink", best],
                capture_output=True,
                timeout=2,
                check=False,
            )
            print(f"[call-audio] Pulse default sink → {best}")
            return best
    except Exception:
        pass
    return pulse_default_sink()


def pulse_default_sink_is_hdmi() -> bool:
    sink = (pulse_default_sink() or "").lower()
    return any(kw in sink for kw in ("hdmi", "spdif", "iec958"))


def pulse_playback_hdmi() -> bool:
    return _PULSE_PLAYBACK_HDMI


def pulse_load_alsa_capture() -> Optional[str]:
    """Load module-alsa-source when Pulse has no real microphone source."""
    if sys.platform not in ("linux", "linux2") or not pulse_available():
        return None
    existing = pulse_best_capture_source()
    if existing:
        return existing
    for dev in ("hw:0,2", "hw:0,0"):
        try:
            proc = subprocess.run(
                [
                    "pactl",
                    "load-module",
                    "module-alsa-source",
                    f"device={dev}",
                    "source_properties=device.description=chatxz_capture",
                ],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            if proc.returncode != 0:
                continue
            time.sleep(0.15)
            best = pulse_best_capture_source()
            if not best:
                continue
            subprocess.run(
                ["pactl", "set-default-source", best],
                capture_output=True,
                timeout=2,
                check=False,
            )
            subprocess.run(
                ["pactl", "set-source-mute", best, "0"],
                capture_output=True,
                timeout=2,
                check=False,
            )
            subprocess.run(
                ["pactl", "set-source-volume", best, "100%"],
                capture_output=True,
                timeout=2,
                check=False,
            )
            print(f"[call-audio] Pulse ALSA source loaded ({dev}) → {best}")
            return best
        except Exception:
            pass
    return None


def alsa_set_capture_controls(card: int = 0) -> None:
    """Unmute ALSA capture and set a usable Input Source (ALC897-style codecs)."""
    if sys.platform not in ("linux", "linux2"):
        return

    def _run(cmd: List[str]) -> None:
        try:
            subprocess.run(cmd, capture_output=True, timeout=2, check=False)
        except Exception:
            pass

    for cmd in (
        ["amixer", "-c", str(card), "sset", "Capture", "cap"],
        ["amixer", "-c", str(card), "sset", "Capture", "90%"],
        ["amixer", "-c", str(card), "sset", "Master", "90%"],
        ["amixer", "-c", str(card), "sset", "Headphone", "90%"],
        ["amixer", "-c", str(card), "sset", "Speaker", "90%"],
        ["amixer", "-c", str(card), "sset", "Mic Boost", "3"],
        ["amixer", "-c", str(card), "sset", "Front Mic Boost", "3"],
        ["amixer", "-c", str(card), "sset", "Rear Mic Boost", "3"],
    ):
        _run(cmd)

    for source in ("Front Mic", "Rear Mic", "Line", "Internal Mic", "Mic"):
        try:
            proc = subprocess.run(
                ["amixer", "-c", str(card), "sset", "Input Source", source],
                capture_output=True,
                timeout=2,
                check=False,
            )
            if proc.returncode == 0:
                print(f"[call-audio] ALSA Input Source → {source}")
                break
        except Exception:
            pass

    src = pulse_best_capture_source()
    if src:
        _run(["pactl", "set-source-mute", src, "0"])
        _run(["pactl", "set-source-volume", src, "100%"])


def alsa_prepare_capture() -> None:
    """Backward-compatible alias for alsa_set_capture_controls."""
    alsa_set_capture_controls()


def hotswap_skip_device(name: str) -> bool:
    """Devices that break ALSA when hot-swapping under Pulse bypass."""
    low = (name or "").lower()
    if any(
        x in low
        for x in (
            "dsnoop",
            "dmix",
            "surround",
            "iec958",
            "spdif",
            "hdmi",
            "jack",
            "null",
            "pulse",
        )
    ):
        return True
    if low in ("default", "sysdefault", "front", "dmix"):
        return True
    return False


def pulse_capture_bypass() -> bool:
    return _PULSE_CAPTURE_BYPASS


def prepare_linux_audio() -> str:
    """Best-effort mic/speaker prep before opening PyAudio streams.

    Returns mode: pulse_ok | pulse_no_mic | alsa_only | other
    """
    global _PULSE_CAPTURE_BYPASS, _PULSE_PLAYBACK_HDMI
    _PULSE_CAPTURE_BYPASS = False
    _PULSE_PLAYBACK_HDMI = False
    if sys.platform not in ("linux", "linux2"):
        return "other"
    if pulse_available():
        _PULSE_PLAYBACK_HDMI = pulse_default_sink_is_hdmi()
        if _PULSE_PLAYBACK_HDMI:
            sink = pulse_default_sink() or ""
            print(
                f"[call-audio] Pulse default sink is HDMI ({sink}) "
                "— playback via Pulse default device"
            )
        ensure_pulse_playback_sink()
        source = ensure_pulse_capture_source()
        if source and ".monitor" not in source.lower():
            alsa_set_capture_controls()
            print(f"[call-audio] PulseAudio capture: {source}")
            return "pulse_ok"
        loaded = pulse_load_alsa_capture()
        if loaded:
            alsa_set_capture_controls()
            print(f"[call-audio] PulseAudio capture: {loaded}")
            return "pulse_ok"
        _PULSE_CAPTURE_BYPASS = True
        alsa_set_capture_controls()
        print("[call-audio] PulseAudio running but no mic — direct ALSA capture")
        return "pulse_no_mic"
    alsa_set_capture_controls()
    _PULSE_CAPTURE_BYPASS = True
    print("[call-audio] ALSA-only audio — unmuted capture, using hw devices")
    return "alsa_only"


def score_device(
    name: str,
    *,
    input_device: bool,
    pulse_name: Optional[str],
    pulse_bypass: bool = False,
    pulse_hdmi: bool = False,
) -> int:
    low = (name or "").lower()
    if not low:
        return -1000
    if any(x in low for x in ("monitor", "loopback", "null", "dummy")):
        return -1000
    if not input_device and any(
        x in low for x in ("virtual", "relay", "vb-audio", "cable", "voicemeeter")
    ):
        return -1000
    if not input_device and any(
        x in low for x in ("dsnoop", "dmix", "surround40", "surround51", "surround71")
    ):
        return -1000
    bypass = pulse_bypass or pulse_capture_bypass()
    hdmi_out = pulse_hdmi or pulse_playback_hdmi()
    if not input_device and hdmi_out:
        if low in ("default", "sysdefault"):
            return 98
        if any(x in low for x in ("dsnoop", "dmix", "surround", "iec958", "spdif")):
            return -1000
        if "hdmi" in low and "hw:" in low:
            return 35
        if "analog" in low and "hw:" in low:
            return 22
    if input_device and bypass:
        if "alt analog" in low:
            return 98
        if "analog" in low and "hw:" in low:
            return 96
        if low in ("default", "sysdefault"):
            return 40
    if input_device and "alt analog" in low:
        return 94 if pulse_name else 90
    if low in ("default", "sysdefault"):
        if input_device and bypass:
            return 40
        return 96 if input_device and not pulse_name else 88 if input_device else 25
    score = 20
    if input_device:
        if "pipewire" in low:
            score += 75
    if pulse_name and ".monitor" not in pulse_name.lower():
        pulse_low = pulse_name.lower()
        if pulse_low in low or low in pulse_low:
            score += 120
        pulse_base = pulse_low.split(".monitor")[0]
        if pulse_base and pulse_base in low:
            score += 80
    if input_device:
        for kw in (
            "microphone", "mic", "headset", "headphone", "webcam", "usb",
            "built-in", "internal", "audio-in", "capture", "analog",
        ):
            if kw in low:
                score += 25
        for kw in ("hdmi", "spdif", "speaker", "output", "sink"):
            if kw in low:
                score -= 40
    else:
        if bypass and "hdmi" in low:
            score -= 60
        for kw in ("speaker", "headphone", "headset", "analog", "usb", "built-in",
                   "internal", "audio-out"):
            if kw in low:
                score += 20
        for kw in ("hdmi", "spdif", "monitor"):
            if kw in low:
                score -= 30
    return score


def rank_devices(pa, *, input_device: bool) -> List[Tuple[int, str, int]]:
    bypass = pulse_capture_bypass()
    pulse_hdmi = pulse_playback_hdmi() if not input_device else False
    pulse = None
    if input_device and not bypass:
        ensure_pulse_capture_source()
        pulse = pulse_default_source()
    ranked: List[Tuple[int, str, int]] = []
    try:
        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            ch_key = "maxInputChannels" if input_device else "maxOutputChannels"
            if int(info.get(ch_key, 0) or 0) < 1:
                continue
            name = str(info.get("name") or f"device {i}")
            score = score_device(
                name,
                input_device=input_device,
                pulse_name=pulse,
                pulse_bypass=bypass,
                pulse_hdmi=pulse_hdmi,
            )
            if score > -1000:
                ranked.append((score, i, name))
    except Exception:
        pass
    ranked.sort(key=lambda t: t[0], reverse=True)
    return [(idx, name, score) for score, idx, name in ranked]


def _probe_read(stream, frame_count: int, timeout: float = 1.5) -> Tuple[Optional[bytes], int, Optional[str]]:
    """Read one probe buffer with a timeout so ALSA/Pulse cannot hang startup."""
    result: List[object] = [None, 0, None]

    def _read():
        try:
            data = stream.read(frame_count, exception_on_overflow=False)
            result[0] = data
            result[1] = pcm_peak(data)
        except Exception as exc:
            result[2] = str(exc)

    thread = threading.Thread(target=_read, name="call-audio-probe", daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        return None, -1, "timeout"
    if result[2]:
        return None, -1, str(result[2])
    return result[0], int(result[1] or 0), None


def pick_input_device(pa) -> Tuple[Optional[int], Optional[str], List[Tuple[int, str, int]]]:
    """Rank-only mic pick (no stream open). Safe when ALSA/Pulse is flaky."""
    ranked = rank_devices(pa, input_device=True)
    if not ranked:
        return None, None, []
    idx, name, score = ranked[0]
    print(f"[call-audio] Selected input [{idx}] score={score}: {name}")
    return idx, name, ranked


def create_pyaudio(timeout: float = 5.0):
    """Construct PyAudio in a helper thread — constructor can block on ALSA scan."""
    result: List[object] = [None, None]

    def _init():
        try:
            import pyaudio
            result[0] = pyaudio.PyAudio()
        except Exception as exc:
            result[1] = exc

    thread = threading.Thread(target=_init, name="call-audio-pa-init", daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        raise TimeoutError(f"PyAudio init timed out after {timeout}s")
    if result[1]:
        raise result[1]
    if not result[0]:
        raise RuntimeError("PyAudio init returned None")
    return result[0]


def _open_stream_with_timeout(pa, timeout: float = 3.0, **kwargs):
    """Open a PyAudio stream in a helper thread so ALSA cannot block forever."""
    result: List[object] = [None, None]

    def _open():
        try:
            result[0] = pa.open(**kwargs)
        except Exception as exc:
            result[1] = exc

    thread = threading.Thread(target=_open, name="call-audio-open", daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        raise TimeoutError(f"PyAudio open timed out after {timeout}s")
    if result[1]:
        raise result[1]
    return result[0]


def probe_input_device(
    pa,
    fmt,
    rate: int,
    frame_count: int,
    *,
    skip_probe: bool = False,
) -> Tuple[Optional[int], Optional[str], List[Tuple[int, str, int]]]:
    """Return (index, name, full_ranked_list). Picks best device even without probe signal."""
    ranked = rank_devices(pa, input_device=True)
    if not ranked:
        return None, None, []
    if skip_probe or pulse_capture_bypass():
        return pick_input_device(pa)
    bypass = pulse_capture_bypass()
    default_pick = None
    if not bypass:
        default_pick = next(
            (t for t in ranked if t[1].lower() in ("default", "sysdefault")),
            None,
        )
    best_silent = default_pick or ranked[0]
    for idx, name, score in ranked[:3]:
        stream = None
        try:
            stream = _open_stream_with_timeout(
                pa,
                timeout=2.0,
                format=fmt,
                channels=1,
                rate=rate,
                input=True,
                frames_per_buffer=frame_count,
                input_device_index=idx,
            )
            stream.start_stream()
            peak = 0
            timed_out = False
            for _ in range(4):
                data, sample_peak, err = _probe_read(stream, frame_count)
                if err == "timeout":
                    timed_out = True
                    print(f"[call-audio] Probe [{idx}] timed out: {name[:72]}")
                    break
                if err:
                    print(f"[call-audio] Probe [{idx}] failed: {err}")
                    break
                peak = max(peak, sample_peak)
            if timed_out:
                break
            print(f"[call-audio] Probe [{idx}] peak={peak}: {name[:72]}")
            if peak > 60:
                print(f"[call-audio] Selected input [{idx}] score={score}: {name}")
                return idx, name, ranked
        except Exception as exc:
            print(f"[call-audio] Probe [{idx}] failed: {exc}")
        finally:
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
    idx, name, score = best_silent
    print(
        f"[call-audio] Selected input [{idx}] score={score}: {name} "
        "(no probe signal — hot-swap if silent)"
    )
    return idx, name, ranked


def pick_output_device(pa) -> Tuple[Optional[int], Optional[str]]:
    ranked = rank_devices(pa, input_device=False)
    if ranked:
        idx, name, score = ranked[0]
        print(f"[call-audio] Selected output [{idx}] score={score}: {name}")
        return idx, name
    return None, None


def log_audio_devices(pa) -> None:
    try:
        pulse = pulse_default_source()
        sink = pulse_default_sink()
        if pulse:
            print(f"[call-audio] PulseAudio default source: {pulse}")
        if sink:
            print(f"[call-audio] PulseAudio default sink: {sink}")
        if pulse_capture_bypass():
            print("[call-audio] Pulse capture bypass active — ranking direct ALSA devices")
        if pulse_playback_hdmi():
            print("[call-audio] Pulse HDMI playback — ranking Pulse default for speaker output")
        for i in range(min(pa.get_device_count(), 16)):
            info = pa.get_device_info_by_index(i)
            name = str(info.get("name") or "")
            ins = int(info.get("maxInputChannels", 0) or 0)
            outs = int(info.get("maxOutputChannels", 0) or 0)
            if ins or outs:
                print(f"[call-audio] Device {i}: in={ins} out={outs} — {name[:72]}")
    except Exception:
        pass