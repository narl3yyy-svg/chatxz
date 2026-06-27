"""Saved contact storage (JSON per peer hash)."""

import json
import os


def contacts_dir(config_dir):
    path = os.path.join(config_dir, "contacts")
    os.makedirs(path, exist_ok=True)
    return path


def _contact_path(config_dir, peer_hash):
    clean = (peer_hash or "").strip().replace(":", "")
    return os.path.join(contacts_dir(config_dir), clean)


def normalize_contact(entry):
    """Ensure dual-hash fields exist (v0.5 migration)."""
    if not entry:
        return entry
    h = (entry.get("hash") or "").replace(":", "")
    lan = (entry.get("lan_hash") or "").replace(":", "")
    serial = (entry.get("serial_hash") or "").replace(":", "")
    if h and not lan and not serial:
        entry["lan_hash"] = h
        lan = h
    if lan and not entry.get("hash"):
        entry["hash"] = lan
    if lan and not entry.get("identity_hash") and entry.get("lan_identity_hash"):
        entry["identity_hash"] = entry["lan_identity_hash"]
    return entry


def contact_primary_hash(contact):
    c = normalize_contact(contact or {})
    return (
        (c.get("lan_hash") or "").replace(":", "")
        or (c.get("serial_hash") or "").replace(":", "")
        or (c.get("hash") or "").replace(":", "")
    )


def _contact_hashes(contact):
    c = normalize_contact(contact or {})
    out = set()
    for key in ("hash", "lan_hash", "serial_hash", "identity_hash", "lan_identity_hash", "serial_identity_hash"):
        h = (c.get(key) or "").replace(":", "")
        if h:
            out.add(h)
    return out


def find_contact_by_hash(config_dir, peer_hash):
    """Return a saved contact matching any stored hash field."""
    clean = (peer_hash or "").strip().replace(":", "")
    if not clean:
        return None
    for contact in list_contacts(config_dir):
        if clean in _contact_hashes(contact):
            return normalize_contact(contact)
    return None


def contact_has_hash(config_dir, peer_hash):
    return find_contact_by_hash(config_dir, peer_hash) is not None


def update_contact_transport_hash(
    config_dir,
    old_hash,
    new_hash,
    via=None,
    name=None,
    ip=None,
    port=None,
    identity_hash=None,
):
    """Refresh lan_hash or serial_hash when discovery supersedes one transport row."""
    old_clean = (old_hash or "").strip().replace(":", "")
    new_clean = (new_hash or "").strip().replace(":", "")
    if not old_clean or not new_clean or old_clean == new_clean:
        return None
    contact = find_contact_by_hash(config_dir, old_clean)
    if not contact:
        return None
    entry = dict(contact)
    transport = (via or "").strip().lower()
    is_serial = transport == "serial" or (
        not transport and old_clean == (entry.get("serial_hash") or "").replace(":", "")
    )
    if is_serial:
        entry["serial_hash"] = new_clean
        if identity_hash:
            entry["serial_identity_hash"] = str(identity_hash).strip().replace(":", "")
    else:
        entry["lan_hash"] = new_clean
        entry["hash"] = new_clean
        if identity_hash:
            ident = str(identity_hash).strip().replace(":", "")
            entry["lan_identity_hash"] = ident
            entry["identity_hash"] = ident
        if ip is not None and str(ip).strip():
            entry["ip"] = str(ip).strip()
        if port is not None:
            try:
                entry["port"] = int(port)
            except (TypeError, ValueError):
                pass
    if name is not None and str(name).strip():
        entry["name"] = str(name).strip()
    file_key = contact_primary_hash(entry) or new_clean
    path = _contact_path(config_dir, file_key)
    with open(path, "w") as fh:
        json.dump(normalize_contact(entry), fh, indent=2)
    if old_clean != file_key:
        delete_contact(config_dir, old_clean)
    return normalize_contact(entry)


def load_contact(config_dir, filename):
    path = os.path.join(contacts_dir(config_dir), filename)
    if not os.path.isfile(path):
        return None
    try:
        with open(path) as fh:
            raw = fh.read().strip()
        if not raw:
            return normalize_contact({"hash": filename, "name": filename})
        if raw.startswith("{"):
            data = json.loads(raw)
            if isinstance(data, dict):
                data.setdefault("hash", filename)
                data.setdefault("name", filename)
                return normalize_contact(data)
        return normalize_contact({"hash": filename, "name": raw})
    except Exception:
        return normalize_contact({"hash": filename, "name": filename})


def save_contact(
    config_dir,
    peer_hash,
    name=None,
    ip=None,
    port=None,
    identity_hash=None,
    via=None,
    lan_hash=None,
    serial_hash=None,
    lan_identity_hash=None,
    serial_identity_hash=None,
):
    clean = (peer_hash or "").strip().replace(":", "")
    if not clean:
        raise ValueError("hash required")
    transport = (via or "lan").strip().lower()
    is_serial = transport == "serial"
    display = str(name).strip() if name is not None and str(name).strip() else None

    merged = None
    if display:
        for c in list_contacts(config_dir):
            if (c.get("name") or "").strip().lower() == display.lower():
                merged = dict(normalize_contact(c))
                break

    existing = merged or load_contact(config_dir, clean) or {"hash": clean, "name": clean or display}
    existing = normalize_contact(existing)
    if display:
        existing["name"] = display
    if is_serial:
        existing["serial_hash"] = clean
        if serial_hash:
            existing["serial_hash"] = str(serial_hash).strip().replace(":", "")
        if identity_hash or serial_identity_hash:
            existing["serial_identity_hash"] = str(
                serial_identity_hash or identity_hash
            ).strip().replace(":", "")
    else:
        existing["lan_hash"] = lan_hash or clean
        existing["hash"] = existing["lan_hash"]
        if identity_hash or lan_identity_hash:
            ident = str(lan_identity_hash or identity_hash).strip().replace(":", "")
            existing["lan_identity_hash"] = ident
            existing["identity_hash"] = ident
        if ip is not None and str(ip).strip():
            existing["ip"] = str(ip).strip()
        if port is not None:
            try:
                existing["port"] = int(port)
            except (TypeError, ValueError):
                pass
    if lan_hash:
        existing["lan_hash"] = str(lan_hash).strip().replace(":", "")
        existing["hash"] = existing["lan_hash"]
    if serial_hash:
        existing["serial_hash"] = str(serial_hash).strip().replace(":", "")

    file_key = contact_primary_hash(existing) or clean
    old_key = clean if clean != file_key else None
    path = _contact_path(config_dir, file_key)
    with open(path, "w") as fh:
        json.dump(existing, fh, indent=2)
    if old_key and old_key != file_key:
        delete_contact(config_dir, old_key)
    return existing


def delete_contact(config_dir, peer_hash):
    path = _contact_path(config_dir, peer_hash)
    if os.path.exists(path):
        os.unlink(path)
        return True
    return False


def list_contacts(config_dir):
    out = []
    base = contacts_dir(config_dir)
    for fname in sorted(os.listdir(base)):
        if fname.startswith("."):
            continue
        entry = load_contact(config_dir, fname)
        if entry:
            out.append(entry)
    return out


def migrate_contact_hash(
    config_dir,
    old_hash,
    new_hash,
    name=None,
    ip=None,
    port=None,
    identity_hash=None,
    via=None,
):
    """Update a saved contact when discovery supersedes an alias hash."""
    old_clean = (old_hash or "").strip().replace(":", "")
    new_clean = (new_hash or "").strip().replace(":", "")
    if not old_clean or not new_clean or old_clean == new_clean:
        return False
    entry = find_contact_by_hash(config_dir, old_clean) or load_contact(config_dir, old_clean)
    if not entry:
        return False
    entry = normalize_contact(dict(entry))
    transport = (via or "").strip().lower()
    is_serial = transport == "serial" or (
        not transport
        and old_clean == (entry.get("serial_hash") or "").replace(":", "")
        and old_clean != (entry.get("lan_hash") or entry.get("hash") or "").replace(":", "")
    )
    if is_serial:
        entry["serial_hash"] = new_clean
        if identity_hash:
            entry["serial_identity_hash"] = str(identity_hash).strip().replace(":", "")
    else:
        entry["lan_hash"] = new_clean
        entry["hash"] = new_clean
        if identity_hash:
            ident = str(identity_hash).strip().replace(":", "")
            entry["lan_identity_hash"] = ident
            entry["identity_hash"] = ident
        if ip is not None and str(ip).strip():
            entry["ip"] = str(ip).strip()
        if port is not None:
            try:
                entry["port"] = int(port)
            except (TypeError, ValueError):
                pass
    if name is not None and str(name).strip():
        entry["name"] = str(name).strip()
    file_key = contact_primary_hash(entry) or new_clean
    path = _contact_path(config_dir, file_key)
    with open(path, "w") as fh:
        json.dump(entry, fh, indent=2)
    if old_clean != file_key:
        delete_contact(config_dir, old_clean)
    return True


def migrate_contact_by_ip(config_dir, ip, new_hash, name=None, port=None, identity_hash=None):
    """Replace any saved contact on this LAN IP with the peer's current hash."""
    ip = (ip or "").strip()
    new_clean = (new_hash or "").strip().replace(":", "")
    if not ip or not new_clean:
        return []
    removed = []
    matched = False
    for contact in list_contacts(config_dir):
        if (contact.get("ip") or "").strip() != ip:
            continue
        matched = True
        old_hash = (contact.get("hash") or "").replace(":", "")
        if old_hash and old_hash != new_clean:
            delete_contact(config_dir, old_hash)
            removed.append(old_hash)
    if matched:
        save_contact(
            config_dir,
            new_clean,
            name=name,
            ip=ip,
            port=port,
            identity_hash=identity_hash,
        )
    return removed


def _same_subnet(ip_a, ip_b):
    """True when two IPv4 addresses are on the same LAN scope for contact updates."""
    from chatxz.utils.lan_scope import same_lan_scope
    return same_lan_scope(ip_a, ip_b)


def should_update_contact_ip(contact_ip, new_ip, local_scope_ip=None):
    """Prefer pinned-LAN subnet IPs; ignore cross-subnet beacons when contact is local."""
    new_ip = (new_ip or "").strip()
    contact_ip = (contact_ip or "").strip()
    if not new_ip:
        return False
    if not contact_ip:
        return True
    if contact_ip == new_ip:
        return False
    scope = (local_scope_ip or "").strip()
    if not scope:
        return True
    new_local = _same_subnet(new_ip, scope)
    contact_local = _same_subnet(contact_ip, scope)
    if new_local and not contact_local:
        return True
    if new_local and contact_local:
        return True
    if not new_local and contact_local:
        return False
    return True


def update_contact_endpoint(
    config_dir,
    peer_hash,
    ip=None,
    port=None,
    identity_hash=None,
    peers_equivalent=None,
    name=None,
    local_scope_ip=None,
):
    """Refresh saved contact LAN endpoint when the same peer moves to a new IP."""
    clean = (peer_hash or "").strip().replace(":", "")
    if not clean:
        return None
    target_ip = (ip or "").strip()
    peer_name = (name or "").strip().lower()
    updated = None
    for contact in list_contacts(config_dir):
        ch = (contact.get("hash") or "").replace(":", "")
        ih = (contact.get("identity_hash") or "").replace(":", "")
        same = ch == clean
        if not same and peers_equivalent:
            same = peers_equivalent(ch, clean) or (ih and peers_equivalent(ih, clean))
        if not same and identity_hash:
            ident = str(identity_hash).strip().replace(":", "")
            same = ih == ident or ch == ident
        if not same and peer_name:
            cn = (contact.get("name") or "").strip().lower()
            if cn and cn == peer_name:
                same = True
        if not same:
            continue
        contact_ip = (contact.get("ip") or "").strip()
        if target_ip and should_update_contact_ip(contact_ip, target_ip, local_scope_ip):
            updated = save_contact(
                config_dir,
                ch,
                name=contact.get("name"),
                ip=target_ip,
                port=port if port is not None else contact.get("port"),
                identity_hash=identity_hash or ih or None,
            )
        break
    return updated


def contact_connect_meta(config_dir, peer_hash, peers_equivalent):
    """Return (ip, port) stored on a saved contact, if any."""
    clean = (peer_hash or "").strip().replace(":", "")
    for contact in list_contacts(config_dir):
        ch = (contact.get("hash") or "").replace(":", "")
        ih = (contact.get("identity_hash") or "").replace(":", "")
        if peers_equivalent(ch, clean) or (ih and peers_equivalent(ih, clean)):
            ip = (contact.get("ip") or "").strip() or None
            port = contact.get("port") or 8742
            if ip:
                return ip, port
    return None, None
