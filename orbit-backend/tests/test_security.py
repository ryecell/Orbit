import security as sec


def test_client_ip_default_ignores_forwarded_header():
    assert sec.client_ip({"x-forwarded-for": "6.6.6.6"}, "10.0.0.1", hops=0) == "10.0.0.1"
    assert sec.client_ip({}, None, hops=0) == "unknown"


def test_client_ip_counts_from_the_right_so_spoofing_fails():
    assert sec.client_ip({"x-forwarded-for": "1.1.1.1, 203.0.113.9"}, "10.0.0.1", hops=1) == "203.0.113.9"
    assert sec.client_ip({"x-forwarded-for": "1.1.1.1, 2.2.2.2, 203.0.113.9"}, "10.0.0.1", hops=1) == "203.0.113.9"
    assert sec.client_ip({"x-forwarded-for": "9.9.9.9, 203.0.113.9, 172.16.0.5"}, "10.0.0.1", hops=2) == "203.0.113.9"


def test_client_ip_short_or_missing_header_falls_back():
    assert sec.client_ip({}, "10.0.0.1", hops=1) == "10.0.0.1"
    assert sec.client_ip({"x-forwarded-for": "203.0.113.9"}, "10.0.0.1", hops=2) == "10.0.0.1"


def test_origin_allowed():
    allowed = ["https://my-orbit.indevs.in", "http://localhost:5173"]
    assert sec.origin_allowed("https://my-orbit.indevs.in", allowed)
    assert sec.origin_allowed("https://my-orbit.indevs.in/", allowed)
    assert sec.origin_allowed(None, allowed)  # non-browser client: token still required
    assert not sec.origin_allowed("https://evil.example", allowed)
    assert not sec.origin_allowed("https://my-orbit.indevs.in.evil.example", allowed)
