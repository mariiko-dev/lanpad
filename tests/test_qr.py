from lanpad import qr


def _failing_socket(*args, **kwargs):
    raise OSError("сети нет")


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


def test_lan_addresses_puts_the_routed_address_first(monkeypatch):
    """Сеть не трогаем: подменяем оба источника адресов."""

    class FakeProbe:
        def __init__(self, *args, **kwargs):
            pass

        def connect(self, *args):
            pass

        def getsockname(self):
            return ("192.168.1.50", 0)

        def close(self):
            pass

    monkeypatch.setattr(qr.socket, "socket", FakeProbe)
    monkeypatch.setattr(qr.socket, "gethostname", lambda: "машина")
    monkeypatch.setattr(qr.socket, "getaddrinfo", lambda *a, **kw: [
        (None, None, None, None, ("127.0.0.1", 0)),
        (None, None, None, None, ("10.8.0.3", 0)),
        (None, None, None, None, ("192.168.1.50", 0)),
    ])
    assert qr.lan_addresses() == ["192.168.1.50", "10.8.0.3"]


def test_lan_addresses_drops_loopback(monkeypatch):
    monkeypatch.setattr(qr.socket, "socket", _failing_socket)
    monkeypatch.setattr(qr.socket, "gethostname", lambda: "машина")
    monkeypatch.setattr(qr.socket, "getaddrinfo", lambda *a, **kw: [
        (None, None, None, None, ("127.0.0.1", 0)),
        (None, None, None, None, ("127.0.1.1", 0)),
    ])
    assert qr.lan_addresses() == []


def test_lan_addresses_survives_a_machine_without_network(monkeypatch):
    monkeypatch.setattr(qr.socket, "socket", _failing_socket)
    monkeypatch.setattr(qr.socket, "gethostname", lambda: "машина")

    def no_resolver(*args, **kwargs):
        raise qr.socket.gaierror("имя не разрешается")

    monkeypatch.setattr(qr.socket, "getaddrinfo", no_resolver)
    assert qr.lan_addresses() == []
