"""Console routes on doubles, without opening a single socket.

The handler is built past its constructor (`Handler.__new__`); the socket
and the response stream are doubles; the reply is captured by swapping
`send_response`, `send_header`, `send_error`. Routes are called directly.
Modelled on `tests/test_http_handler.py`.
"""

import email.message
import io
import json
from pathlib import Path

import pytest

from lanpad import http as h
from lanpad import service
from lanpad.platform.base import Backends
from lanpad.platform.fake import FakeAudio, FakeClipboard, FakeInput, FakeMedia
from lanpad.session import Session

TOKEN = "consoletoken123"
NETWORK_CLIENT = "192.168.1.9"


def make_session() -> Session:
    backends = Backends(FakeInput(), FakeAudio(), FakeMedia(), FakeClipboard())
    return Session(backends)


class _Recorder:
    """Captures whatever the handler tries to answer."""

    def __init__(self) -> None:
        self.code: int | None = None

    def send_response(self, code: int, message: str | None = None) -> None:
        self.code = code

    def send_header(self, name: str, value: str) -> None:
        pass

    def end_headers(self) -> None:
        pass

    def send_error(self, code: int, message: str | None = None,
                   explain: str | None = None) -> None:
        self.code = code

    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture
def handler_from_network(tmp_path):
    """Drive a console route as a client from the local network."""

    def run(path: str) -> int:
        handler_cls = h.make_handler(make_session(), TOKEN, Path(tmp_path))
        handler = handler_cls.__new__(handler_cls)
        handler.command = "GET"
        handler.path = path
        handler.client_address = (NETWORK_CLIENT, 44444)
        handler.request_version = "HTTP/1.1"
        handler.headers = email.message.Message()
        handler.rfile = io.BytesIO(b"")
        handler.wfile = io.BytesIO()

        rec = _Recorder()
        handler.send_response = rec.send_response
        handler.send_header = rec.send_header
        handler.end_headers = rec.end_headers
        handler.send_error = rec.send_error
        handler.log_message = rec.log_message

        handler.do_GET()
        return rec.code

    return run


@pytest.fixture
def handler_post_from_network(tmp_path):
    """Drive a console POST route as a client from the local network."""

    def run(path: str, body: bytes = b"{}") -> int:
        handler_cls = h.make_handler(make_session(), TOKEN, Path(tmp_path))
        handler = handler_cls.__new__(handler_cls)
        handler.command = "POST"
        handler.path = path
        handler.client_address = (NETWORK_CLIENT, 44444)
        handler.request_version = "HTTP/1.1"
        handler.headers = email.message.Message()
        handler.headers["Content-Length"] = str(len(body))
        handler.rfile = io.BytesIO(body)
        handler.wfile = io.BytesIO()

        rec = _Recorder()
        handler.send_response = rec.send_response
        handler.send_header = rec.send_header
        handler.end_headers = rec.end_headers
        handler.send_error = rec.send_error
        handler.log_message = rec.log_message

        handler.do_POST()
        return rec.code

    return run


@pytest.fixture
def handler_post_from_loopback(tmp_path):
    """Drive a console POST route as a client on this machine."""

    def run(path: str, body: bytes = b"{}",
            headers: dict[str, str] | None = None) -> int:
        handler_cls = h.make_handler(make_session(), TOKEN, Path(tmp_path))
        handler = handler_cls.__new__(handler_cls)
        handler.command = "POST"
        handler.path = path
        handler.client_address = ("127.0.0.1", 44444)
        handler.request_version = "HTTP/1.1"
        message = email.message.Message()
        supplied = headers or {}
        for name, value in supplied.items():
            message[name] = value
        if "Content-Length" not in supplied:
            message["Content-Length"] = str(len(body))
        handler.headers = message
        handler.rfile = io.BytesIO(body)
        handler.wfile = io.BytesIO()

        rec = _Recorder()
        handler.send_response = rec.send_response
        handler.send_header = rec.send_header
        handler.end_headers = rec.end_headers
        handler.send_error = rec.send_error
        handler.log_message = rec.log_message

        handler.do_POST()
        return rec.code

    return run


def test_state_carries_everything_the_window_shows():
    state = h.console_state(make_session(), TOKEN, 8477)
    assert isinstance(state["addresses"], list)
    assert state["port"] == 8477
    assert state["caps"]["audio"] is True
    assert isinstance(state["events"], list)
    assert isinstance(state["connected"], int)


def test_state_url_contains_the_token():
    """The window shows the pairing link; without the token it is useless."""
    state = h.console_state(make_session(), TOKEN, 8477)
    if state["url"]:
        assert TOKEN in state["url"]


def test_state_is_serialisable():
    json.dumps(h.console_state(make_session(), TOKEN, 8477))


def test_console_refuses_a_client_from_the_network(handler_from_network):
    """The console shows the QR, and the QR carries the token."""
    code = handler_from_network("/console")
    assert code == 403


def test_console_state_refuses_a_client_from_the_network(handler_from_network):
    assert handler_from_network("/console/state") == 403


def test_console_qr_refuses_a_client_from_the_network(handler_from_network):
    assert handler_from_network("/console/qr.png") == 403


def test_service_control_refuses_a_client_from_the_network(handler_post_from_network):
    """A web page from the Wi-Fi must not be able to stop the agent."""
    assert handler_post_from_network("/console/service", b'{"action":"stop"}') == 403


def test_service_control_refuses_a_foreign_origin(handler_post_from_loopback):
    """A browser on this machine is a loopback client too: any open tab
    could otherwise stop the service with a plain cross-site POST."""
    code = handler_post_from_loopback(
        "/console/service", b'{"action":"stop"}',
        headers={"Origin": "http://evil.example", "Host": "127.0.0.1:8477"},
    )
    assert code == 403


def test_service_control_accepts_its_own_origin(handler_post_from_loopback):
    code = handler_post_from_loopback(
        "/console/service", b'{"action":"unknown"}',
        headers={"Origin": "http://127.0.0.1:8477", "Host": "127.0.0.1:8477"},
    )
    assert code == 200


def test_service_control_accepts_a_request_without_origin(handler_post_from_loopback):
    """Not a browser — it cannot forge a cross-site request."""
    code = handler_post_from_loopback(
        "/console/service", b'{"action":"unknown"}', headers={"Host": "127.0.0.1:8477"},
    )
    assert code == 200


def test_service_control_refuses_a_bad_content_length(handler_post_from_loopback):
    code = handler_post_from_loopback(
        "/console/service", b"{}", headers={"Host": "127.0.0.1:8477", "Content-Length": "abc"},
    )
    assert code == 400


def test_service_control_refuses_an_oversized_body(handler_post_from_loopback):
    code = handler_post_from_loopback(
        "/console/service", b"{}", headers={"Host": "127.0.0.1:8477", "Content-Length": "99999"},
    )
    assert code == 413


def test_unknown_action_never_reaches_the_system(handler_post_from_loopback, monkeypatch):
    """The allow-list must stop it before anything runs."""
    calls = []
    monkeypatch.setattr(service.subprocess, "run", lambda cmd, **kw: calls.append(cmd))
    handler_post_from_loopback(
        "/console/service", b'{"action":"rm -rf /"}',
        headers={"Host": "127.0.0.1:8477"},
    )
    assert calls == []
