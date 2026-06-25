"""Direct HTTP LAN bulk transfer (bypasses slow RNS resource segmentation on same subnet)."""

import os
import secrets
import threading
import time

from chatxz.core.discovery import normalize_hash

_offers_lock = threading.Lock()
_offers = {}


def register_offer(transfer_id, file_path, peer_hash, host, port, ttl=7200):
    token = secrets.token_urlsafe(24)
    with _offers_lock:
        _offers[transfer_id] = {
            "path": file_path,
            "token": token,
            "peer": normalize_hash(peer_hash),
            "host": host,
            "port": int(port or 8742),
            "expires": time.time() + ttl,
            "bytes_sent": 0,
        }
    return token


def set_offer_progress(transfer_id, bytes_sent):
    with _offers_lock:
        offer = _offers.get(transfer_id)
        if offer:
            offer["bytes_sent"] = max(int(bytes_sent), int(offer.get("bytes_sent") or 0))


def get_offer_state(transfer_id):
    with _offers_lock:
        offer = _offers.get(transfer_id)
        if not offer:
            return None
        if time.time() > float(offer.get("expires") or 0):
            _offers.pop(transfer_id, None)
            return None
        return dict(offer)


def peek_offer(transfer_id, token):
    with _offers_lock:
        offer = _offers.get(transfer_id)
        if not offer:
            return None
        if offer.get("token") != token:
            return None
        if time.time() > float(offer.get("expires") or 0):
            _offers.pop(transfer_id, None)
            return None
        return dict(offer)


def pop_offer(transfer_id, token):
    with _offers_lock:
        offer = _offers.get(transfer_id)
        if not offer:
            return None
        if offer.get("token") != token:
            return None
        if time.time() > float(offer.get("expires") or 0):
            _offers.pop(transfer_id, None)
            return None
        data = dict(offer)
        _offers.pop(transfer_id, None)
        return data


def remove_offer(transfer_id):
    with _offers_lock:
        _offers.pop(transfer_id, None)


def cleanup_expired():
    now = time.time()
    with _offers_lock:
        expired = [
            tid for tid, offer in _offers.items()
            if now > float(offer.get("expires") or 0)
        ]
        for tid in expired:
            _offers.pop(tid, None)