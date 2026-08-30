from lanpad import qr


def test_connect_url_contains_host_port_and_token():
    assert qr.connect_url("192.168.1.50", 8477, "abc") == "http://192.168.1.50:8477/?t=abc"


def test_connect_url_escapes_token():
    assert "a%2Bb" in qr.connect_url("10.0.0.1", 8477, "a+b")


def test_terminal_qr_is_non_empty_block():
    rendered = qr.render_terminal("http://192.168.1.50:8477/?t=abc")
    assert rendered.count("\n") > 10


def test_png_is_written(tmp_path):
    target = tmp_path / "qr.png"
    qr.save_png("http://192.168.1.50:8477/?t=abc", target)
    assert target.stat().st_size > 0
    assert target.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_lan_addresses_returns_strings():
    for address in qr.lan_addresses():
        assert isinstance(address, str)
        assert not address.startswith("127.")
