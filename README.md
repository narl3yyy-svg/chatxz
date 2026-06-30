# chatxz

**Encrypted peer-to-peer messaging** over the [Reticulum Network Stack](https://reticulum.network/). No accounts, no cloud relay for 1:1 chat — messages, files, and calls travel over AES-256 encrypted links on your LAN, USB serial, or optional TCP hub.

**Current version: 1.0.4** · [Releases](https://github.com/narl3yyy-svg/chatxz/releases) · [Changelog](CHANGELOG.md)

---

## What you get

| | |
|---|---|
| **Messaging** | Per-peer threads, delivery receipts, offline queue, emoji picker |
| **Calls** | Voice, video, and screen share over RNS — no WebRTC, no STUN/TURN |
| **Files** | Any size via encrypted RNS resources; large LAN files can use direct HTTP with `--share` |
| **Discovery** | UDP beacon + RNS announce on your pinned IPv4; saved contacts with custom names |
| **Transports** | **UDP LAN** or **TCP LAN** on desktop; **TCP LAN** default on Android; **USB serial** for direct cable links |
| **Privacy** | End-to-end encrypted RNS links; port 8742 is local UI only |

Open a chat, wait for **Link: Active**, then message, send files, or tap 📞 📹 🖥 in the header.

---

## Quick start

### Linux / macOS

```bash
git clone https://github.com/narl3yyy-svg/chatxz.git
cd chatxz
./run.sh web --share
```

Open **http://localhost:8742** (or `http://<your-lan-ip>:8742` with `--share`).

### Windows (cmd only)

```cmd
git clone https://github.com/narl3yyy-svg/chatxz.git
cd chatxz
run.bat web --share
```

Open **http://127.0.0.1:8742**.

### Android

1. Download **`chatxz-1.0.4.apk`** (or latest) from [GitHub Releases](https://github.com/narl3yyy-svg/chatxz/releases).
2. Install, grant notification permission, complete setup (display name + LAN IPv4).
3. Tap a discovered peer or saved contact to connect.

Fresh Android installs use **TCP LAN** for stable mobile links. UDP remains available in **Settings → Network** for low-bandwidth mode. **Restart the app** after updating so settings migration applies.

---

## First-time setup

1. Choose a **display name**.
2. Pick your **LAN IPv4** from the list (required — scopes discovery and wake).
3. Tap **Announce LAN** (sidebar) or enable auto-announce in Settings.
4. Tap a peer in **Discovered** or open a saved contact — header shows **Connected** when the RNS link is live.

### Sidebar

| Action | What it does |
|--------|----------------|
| **Announce LAN** | RNS announce + UDP beacon on your pinned IPv4 |
| **Announce Serial** | RNS announce on USB (when serial is online) |
| **Discovered row** | Open chat on that transport |
| **Contact LAN/USB row** | Open chat on the saved path for that peer |

---

## Networking

### Dual identity (LAN + USB)

Each device can have **two RNS identities**:

| Transport | Identity | Connect hash | Label |
|-----------|----------|--------------|-------|
| LAN (UDP/TCP) | `identity_lan` | LAN hash | `peer · LAN` |
| USB serial | `identity_serial` | Serial hash | `peer · USB` |

- No automatic transport failover — the row you tap is the path used.
- LAN and USB can both stay linked to the same peer (separate sub-rows on one contact card).
- Legacy `identities/identity` migrates to `identity_lan` on upgrade.

### LAN transport

| Platform | Default | Notes |
|----------|---------|-------|
| **Desktop** | UDP LAN | Fast discovery on Wi‑Fi/Ethernet; optional TCP LAN in Settings |
| **Android** | TCP LAN | Stable on mobile; auto-migrated from UDP on update; UDP optional |

**Phone ↔ desktop:** if the phone uses TCP, the desktop may need **TCP LAN** enabled (Settings → Network → Primary LAN transport) so it listens on TCP 4242. Both sides can use UDP LAN for a simpler desktop-only mesh.

**Firewall (private LAN):** UDP **4242** (RNS), **8743** (beacon), TCP **8742** (web UI), TCP **4242** when using TCP LAN or hub.

### Connection stability (v1.0.4)

- No wake spam when already linked — HTTP peer wake is debounced (20s).
- Inbound links adopted before duplicate outbound attempts.
- UI syncs link state from the server on WebSocket reconnect (no false **Connected**).
- Background failover retries dropped sessions until you tap **Disconnect**.

### USB serial

Plug in a USB adapter, set device + baud in Settings → Network, Apply, restart. Use **Announce Serial** and connect via the USB row. Works across pinned subnets (e.g. 10.0.5.x ↔ 10.0.30.x).

---

## Voice, video, and screen (v1.0.0+)

1. Open a chat with **Link: Active**.
2. Tap **📞** (voice), **📹** (video), or **🖥** (screen) in the header.
3. Callee uses the in-page **Accept / Decline** bar.
4. Hang up on either side ends the call for both (v1.0.2+).

**Architecture**

- **Signaling:** `__call` JSON over the RNS link (invite, accept, reject, hangup).
- **Media:** `CXMZ` packets — Opus audio, JPEG video/screen; chunked for RNS MTU (v1.0.3+).
- **Engine:** Rust `chatxz-media` with Python fallback; browser ↔ server via `/ws/media`.

Grant microphone/camera when prompted. Use `http://localhost:8742` (not a random LAN IP) on desktop if the browser blocks permissions.

---

## TCP hub (optional group chat)

A **hub** relays encrypted **group chat** over the internet on **TCP 4242**. It does not mix with normal LAN/UDP discovery peers.

| Role | Behavior |
|------|----------|
| **Hub server** | Listens on `0.0.0.0:4242`; relays group messages to TCP-connected clients |
| **Hub client** | Dials your hub host (public IP, DDNS, or VPN) |
| **Hub off** | P2P only |

Hub server mode reserves TCP 4242 — use **UDP LAN** for local peers while hub is on, or set hub to **Off** to use **TCP LAN** for 1:1 LAN chat.

---

## How it works

```
Browser  ←WebSocket/HTTP→  Local server (UI, port 8742)
         ←/ws/media→       Media engine (Opus, jitter buffer)
                                ↓
                          Reticulum (RNS) — encrypted P2P
                                ↓
                           Remote peer
```

Chat payloads, call media, and files use encrypted RNS links. No external voice servers or WebRTC infrastructure.

**Config & data**

| Platform | Location |
|----------|----------|
| Linux / macOS / Windows | `~/.config/chatxz/` |
| Android | App private storage |
| Portable (`CHATXZ_PORTABLE`) | `chatxz-data/` beside the app |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| **Connected but messages don't send** | Hard-refresh (`Ctrl+Shift+R`); check header shows **Link: Active**; v1.0.4+ syncs state from server |
| **Repeated “Waking peer”** | Update to v1.0.4; don't refresh while linked |
| **Phone one-sided connect** | Restart Android app (TCP migration); enable TCP LAN on desktop peer if needed |
| **Call buttons greyed out** | Open the peer's chat first; wait for **Link: Active** |
| **No call audio** | Both sides v1.0.3+; callee must Accept; grant microphone |
| **Port in use** | `bash scripts/stop-chatxz.sh` then restart |
| **Serial peer missing** | Tap **Announce Serial**; check USB permissions (Android OTG) |

**Stop server:** `Ctrl+C` in the terminal (releases 8742, 4242, 8743).

---

## Development

```bash
./run.sh web --share --debug    # verbose RNS + chatxz trace
bash scripts/check.sh           # unit tests + smoke checks before push
bash scripts/sync-android.sh    # sync Python tree into Android APK
bash scripts/bump-version.sh 1.0.5   # bump version everywhere
```

**Build Android APK locally**

```bash
cd android && ./gradlew assembleRelease
```

Tag pushes trigger [CI APK builds](.github/workflows/build-apk.yml) on GitHub Actions.

---

## Recent releases

- **v1.0.4** — Connection stability: wake debounce, truthful link state, Android TCP LAN default
- **v1.0.3** — Call audio MTU chunking; Accept/Decline incoming call bar
- **v1.0.2** — Bilateral hangup, UDP-first call media, low-latency LAN audio
- **v1.0.1** — Call buttons use open chat peer; Android CI fix
- **v1.0.0** — Voice/video/screen calls over RNS with Rust media engine

Full history: [CHANGELOG.md](CHANGELOG.md)

---

## License

[GNU General Public License v3.0](LICENSE) (GPLv3)