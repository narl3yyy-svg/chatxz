# Voice calls in chatxz

chatxz provides **duplex Opus voice calls** over encrypted Reticulum (RNS) links — the same transport used for chat messages.

## Quick start

1. Connect to a peer (LAN or USB serial).
2. Tap **📞** in the chat header.
3. The other side accepts the incoming call.
4. Speak — audio flows in both directions until someone hangs up.

Voice **notes** (🎤) are separate one-shot recordings and do not use this pipeline.

## Codec and timing

| Parameter | Value |
|-----------|-------|
| Codec | Opus (VOIP mode) |
| Sample rate | 48 kHz mono |
| Frame size | 20 ms (960 samples) |
| Bitrate | ~32 kbps |
| MIME type | `audio/opus;rate=48000;frame=20` |

μ-law and PCM are **not** used on the call path.

## Architecture

All voice call code lives under **`chatxz/core/audio/`**:

```
capture thread → Opus encode → CALL_AUDIO (messaging.py) → RNS link
RNS receive → Opus decode → jitter buffer → playback thread → speaker
```

Signaling: `INVITE → ACCEPT → ACTIVE → CALL_AUDIO frames → END`

```
┌─────────────────────────────────────────────────────────────┐
│  session.py — call state machine + MTU-safe frame splitting   │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
  engine.py (desktop)   Browser WebCodecs      android.py + Java
  PyAudio + libopus     (fallback)             CallAudioEngine
  devices.py +          AudioEncoder/Decoder   AudioRecord +
  jitter.py                                       MediaCodec Opus
        │                     │                     │
        └─────────────────────┴─────────────────────┘
                              │
                    RNS encrypted link
                    (__call_audio + seq + b64)
```

### Modules (`chatxz/core/audio/`)

| Module | Role |
|--------|------|
| `session.py` | Call state machine, signaling packet types, MTU-safe frame splitting |
| `opus.py` | ctypes bindings to system libopus (encode/decode) |
| `jitter.py` | Adaptive playout buffer with PLC |
| `devices.py` | Linux PulseAudio/ALSA mic and speaker selection |
| `engine.py` | Desktop `CallAudioEngine` — threaded capture/playback (not PortAudio callbacks) |
| `android.py` | Python ↔ Java bridge on Android |
| `messaging.py` | Routes `CALL_*` packets and assigns audio sequence numbers |

### Jitter buffer

The receive path buffers 2–12 frames (40–240 ms) before playout. Delay adapts to inter-arrival jitter. Out-of-order packets are reordered by sequence number. Missing frames use packet-loss concealment (attenuated repeat of the last good frame).

### Linux microphone selection

On Arch and Ubuntu, `devices.py`:

1. Uses `pactl` to reject `.monitor` (HDMI loopback) sources.
2. Sets Pulse default source to a real `alsa_input` device when needed.
3. Ranks PyAudio devices (prefers Alt Analog, pipewire, default).
4. Hot-swaps to the next ranked device if capture stays silent for ~3 seconds.

## Platform setup

### Linux (Arch / Ubuntu)

```bash
# Arch
sudo pacman -S opus portaudio python-pyaudio pulseaudio

# Ubuntu / Debian
sudo apt install libopus0 portaudio19-dev python3-pyaudio pulseaudio-utils

./run.sh web --share
```

Native audio starts automatically when libopus and PyAudio are available. Otherwise the browser WebCodecs Opus fallback is used.

### Windows

```cmd
run.bat web --share
```

Install PyAudio via pip (run.bat does this). Install [libopus](https://opus-codec.org/) if native audio is unavailable.

### macOS

```bash
brew install opus portaudio
./run.sh web --share
```

### Android

Rebuild/install the APK (API 29+). On call accept, `CallAudioEngine.java` captures and plays Opus natively — the WebView mic is not used for calls. Tap **🔈/🔊** on the call dashboard for speakerphone.

## Troubleshooting

| Symptom | Check |
|---------|-------|
| No audio either direction | Server logs for `[call] Opus out` / `[call] Audio in` and `[call-audio] Opus out` |
| `mic peak 0` on Linux | Logs should show `alsa_input…` not `…monitor`; hot-swap tries alternate devices after ~3 s silence |
| Ctrl+C ignored during call | v0.9.0+ stops audio, sends CALL_END, then `os._exit` — no hung PortAudio cleanup |
| Hang-up one-sided | v0.9.0+ stops engine before CALL_END; remote gets `call_ended` WebSocket event |
| Dashboard shows 0 audio sent/received | `call_stats` WebSocket push; native stats come from server engine |
| `Native unavailable` on desktop | `libopus` installed? `./run.sh install` for PyAudio |
| Garbled audio | Confirm logs show `Opus` not `pcmulaw`; update both peers to v0.8.3+ |
| Android silent | Rebuild APK; API 29+; check logcat `CallAudioEngine` |

## Logs to expect (healthy call)

```
[call] Outgoing to abc123... (call-id)
[call] Accepted by abc123...
[call-audio] Engine started (duplex, Opus 48 kHz, 20 ms)
[call-audio] Opus out #1 (… b64, … B)
[call] Audio in #1 (…) ← abc123...
[call-audio] Opus in #1 (seq=1, … b64, jb=40 ms)
```