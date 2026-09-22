from __future__ import annotations

import socket


def build_discovery_payload(device_name, ip_address, port, version, storage_used=0, storage_limit=50_000_000_000):
    return {
        "device_name": device_name,
        "ip_address": ip_address,
        "port": port,
        "version": version,
        "storage_used": storage_used,
        "storage_limit": storage_limit,
    }


def get_local_ip_addresses():
    candidates = []
    for family, _, _, _, sockaddr in socket.getaddrinfo(socket.gethostname(), None):
        if family == socket.AF_INET:
            ip = sockaddr[0]
            if not ip.startswith("127."):
                candidates.append(ip)
    return sorted(set(candidates))
