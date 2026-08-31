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
