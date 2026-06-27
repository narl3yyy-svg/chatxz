# Changelog

All notable changes to chatxz are documented here. The README lists only the latest release summary.

## [0.5.2] — 2026-06-27

### Fixed
- **Discovered list empty in web UI** — `renderDiscovered` referenced `isSerial` before it was defined (ReferenceError), so peers visible in the server log never rendered in the sidebar.
- **LAN + USB rows merging in UI** — `peerMergeKey` now includes transport so both discovered rows stay visible.

## [0.5.1] — 2026-06-27

### Fixed
- **Separate LAN + USB connections** — discovery stores `hash:lan` and `hash:serial` rows independently; connect API accepts `via` so serial and LAN links to the same peer no longer collide.
- **Android back navigation** — swipe-back from chat returns to the contact list first; second back minimizes the app (WebView `"true"` callback parsing fixed).
- **Transport-aware UI** — linked-peer state, connect, and chat header track per-transport links (`hash:lan` / `hash:serial`).
- **Contact name flash** — saved contacts no longer briefly show the full RNS hash when display name is missing.

## [0.5.0] — 2026-06-27

### Changed
- **Dual LAN + Serial identities** — `identity_lan` and `identity_serial`; separate connect hashes; legacy `identity` auto-migrates to `identity_lan`.
- **No transport failover** — links stay on the transport you chose (LAN or USB).
- **Discovery** — LAN and USB appear as separate rows (`name · LAN` / `name · USB`).
- **Contacts** — one card per person with LAN/USB sub-rows.
- **Announce** — sidebar **Announce LAN** and **Announce Serial** buttons.
- **Settings** — mandatory LAN IPv4 (no Auto); per-transport probe and announce intervals (0–18000 s).
- **Profile** — Regenerate LAN / Regenerate Serial (moved from System).

### Removed
- Auto interface selection; combined single announce; link failover loop.

## [0.4.2] — 2026-06-27

### Fixed
- **LAN wake on contact tap** — opening a contact or discovered peer sends HTTP wake + reconnect so sleeping Android/desktop peers accept messages without manual re-announce.
- **Stale link reconnect** — connect no longer treats zombie RNS links as healthy; unhealthy links are torn down and re-established.
- **RTT on saved contacts** — contact list shows live RTT from discovery even when the stored IP is unchanged.
- **Discovered dedup** — peers already saved as contacts are hidden from Discovered.

### Changed
- **Android APK navigation** — contact list is the main screen; tap a peer to open chat; back once returns to the list, back again backgrounds the app.

## [0.4.1] — 2026-06-27

### Fixed
- **LAN RTT in Discovered** — UDP beacon pings no longer skipped while peers are actively announcing; RTT updates on a configurable interval.
- **Android on desktop** — beacon peers appear even when RNS identity registration is still pending (hash/name/IP sufficient).

### Added
- **Settings → Network → Link ping interval** (5–300s, default 30) — controls LAN UDP and USB serial liveness pings and RTT refresh.

## [0.4.0] — 2026-06-27

### Fixed
- **Serial RNS auto-announce** no longer floods USB with 3–5 packet bursts; one announce per event, periodic serial every 30s when auto-announce is on.
- **Discovered peers UI** updates when transport (`via`), IP, or RTT changes; authoritative peer broadcasts on Announce, scope change, and probe eviction.
- **Live LAN scope drift** (OS IP or pinned interface change without restart) refreshes discovery, drops stale subnet peers, and pushes WebSocket updates automatically.
- **Manual Announce** sends a single serial RNS packet in dual-transport mode instead of 4× bursts that clogged the link.

### Changed
- Connect/failover serial priming uses one announce every 3s instead of multi-packet bursts.
- UI transient empty-peer hold reduced from 120s to 15s; authoritative updates bypass the hold entirely.

### Tests
- `tests/test_serial_announce_policy.py` — serial rate limits, periodic loop, serial discovery visibility.

## [0.3.171] — 2026-06-26

- Fastest-path (RTT) selection per peer in discovered list.
- LAN scope save refreshes discovery paths.
- LAN auto-announce and peer ping every 30s; serial had no periodic auto-announce.

## [0.3.170] — 2026-06-25

- Hide serial badge when USB unplugged; beacon upgrades to LAN.
- Scope checker accepts in-scope LAN for serial-tagged peers.
- Transport matrix tests.

[0.4.0]: https://github.com/narl3yyy-svg/chatxz/compare/v0.3.171...v0.4.0
[0.3.171]: https://github.com/narl3yyy-svg/chatxz/compare/v0.3.170...v0.3.171
[0.3.170]: https://github.com/narl3yyy-svg/chatxz/compare/v0.3.169...v0.3.170