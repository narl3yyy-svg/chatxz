"""Shared LAN broadcast and unicast target lists (beacon + RNS)."""

from chatxz.utils.platform import is_android, lan_ip, list_network_interfaces


def directed_broadcasts(ip=None):
    """Subnet and interface broadcast addresses."""
    targets = []
    for iface in list_network_interfaces():
        for candidate in (iface.get("broadcast"), iface.get("subnet_broadcast")):
            if candidate and candidate not in targets:
                targets.append(candidate)
    ip = ip or lan_ip()
    if ip:
        parts = ip.split(".")
        if len(parts) == 4:
            directed = f"{parts[0]}.{parts[1]}.{parts[2]}.255"
            if directed not in targets:
                targets.insert(0, directed)
    for candidate in ("255.255.255.255",):
        if candidate not in targets:
            targets.append(candidate)
    return targets


def _sample_subnet_hosts(base, my_host):
    """Small DHCP/gateway sweep — enough for discovery without a full /24."""
    hosts = []
    for i in (1, 2, 3, 4, 5, 10, 20, 50, 100, 101, 102, 103, 104, 105,
              110, 120, 150, 200, 254):
        if str(i) == my_host:
            continue
        host = f"{base}.{i}"
        if host not in hosts:
            hosts.append(host)
    if is_android():
        for i in range(2, 32):
            host = f"{base}.{i}"
            if str(i) != my_host and host not in hosts:
                hosts.append(host)
        for i in range(100, 116):
            host = f"{base}.{i}"
            if str(i) != my_host and host not in hosts:
                hosts.append(host)
    return hosts


def efficient_unicast_hosts(ip=None, known_ips=None, peer_ip=None):
    """Unicast targets for LAN discovery (beacon + RNS)."""
    targets = []
    for host in known_ips or []:
        host = (host or "").strip()
        if host and host not in targets:
            targets.append(host)
    if peer_ip:
        host = peer_ip.strip()
        if host and host not in targets:
            targets.insert(0, host)

    ip = ip or lan_ip()
    if not ip:
        return targets
    parts = ip.split(".")
    if len(parts) != 4:
        return targets
    base = f"{parts[0]}.{parts[1]}.{parts[2]}"
    my_host = parts[3]
    for host in _sample_subnet_hosts(base, my_host):
        if host not in targets:
            targets.append(host)
    return targets
