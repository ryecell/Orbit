"""Small, dependency-free security helpers (unit-tested without the web stack)."""
import os
from typing import Iterable, Optional


def client_ip(headers, peer: Optional[str], hops: Optional[int] = None) -> str:
    """
    The address used for rate limiting.

    Behind a platform proxy (Render, etc.) the socket peer is the proxy, so every visitor would
    share one rate-limit bucket. The proxy APPENDS the real address to X-Forwarded-For, and anything a
    client puts in that header sits to the LEFT of it — so we count from the right, skipping only
    the proxies we trust:

        ORBIT_PROXY_HOPS=0  (default)  ignore X-Forwarded-For, use the socket peer (safe, local dev)
        ORBIT_PROXY_HOPS=1             take the last entry   (one trusted proxy in front)
        ORBIT_PROXY_HOPS=2             take the second-to-last (e.g. CDN + platform proxy)

    A forged X-Forwarded-For can't pick the address as long as the hop count matches reality.
    """
    if hops is None:
        try:
            hops = int(os.environ.get("ORBIT_PROXY_HOPS", "0"))
        except ValueError:
            hops = 0
    peer = peer or "unknown"
    if hops <= 0:
        return peer
    raw = headers.get("x-forwarded-for", "")
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if len(parts) < hops:
        return peer  # header shorter than expected: don't trust it, fall back
    return parts[-hops]


def origin_allowed(origin: Optional[str], allowed: Iterable[str]) -> bool:
    """
    WebSocket handshakes aren't covered by CORS, so a malicious web page could try to open one
    from a visitor's browser. Browsers always send Origin on such a handshake: reject any that
    isn't ours. Non-browser clients send no Origin and still need a valid token, so they pass.
    """
    if not origin:
        return True
    return origin.rstrip("/") in {a.rstrip("/") for a in allowed}
