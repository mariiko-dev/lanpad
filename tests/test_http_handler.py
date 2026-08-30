"""Тесты обработчика на двойниках, без единого сетевого сокета.

Здесь проверяются свойства, которые живут в самом обработчике, а не в чистых
функциях: кто пускается к маршруту, что происходит с негодными заголовками,
снимается ли подписка. Без них пять правок безопасности (C1, I2, I3, I4, I7)
можно вернуть назад, не уронив ни один тест.

Обработчик поднимается в обход конструктора (`Handler.__new__`), сокет и поток
ответа — двойники, ответ перехватывается через подмену `send_response`,
`send_header`, `send_error`. Маршруты вызываются напрямую: `do_GET`, `do_POST`.
"""

import email.message
import io
import json
from pathlib import Path

from lanpad import http as h
from lanpad.platform.base import Backends
from lanpad.platform.fake import FakeAudio, FakeClipboard, FakeInput, FakeMedia
from lanpad.session import Session

TOKEN = "test-token-abc123"
LOCAL = "192.168.1.9"
HOSTPORT = "192.168.1.9:8477"


class FakeSocket:
    """Сокет, который ничего никуда не отправляет и сразу «закрыт» на чтении."""

    def __init__(self) -> None:
        self.sent = b""

    def sendall(self, data: bytes) -> None:
        self.sent += data

    def settimeout(self, _value: object) -> None:
        pass

    def recv(self, _n: int) -> bytes:
        return b""


class Recorder:
    """Перехватывает то, что обработчик пытается ответить."""

    def __init__(self) -> None:
        self.code: int | None = None
        self.error: int | None = None
        self.headers: dict[str, str] = {}
        self.ended = False

    def send_response(self, code: int, message: str | None = None) -> None:
        self.code = code

    def send_header(self, name: str, value: str) -> None:
        self.headers[name] = value

    def end_headers(self) -> None:
        self.ended = True

    def send_error(self, code: int, message: str | None = None,
                   explain: str | None = None) -> None:
        self.code = code
        self.error = code

    def log_message(self, *args: object) -> None:
        pass


class ArtMedia(FakeMedia):
    """FakeMedia с настраиваемым путём обложки."""

    def __init__(self) -> None:
        super().__init__()
        self.art: str | None = None

    def art_path_for(self, art_id: str) -> str | None:
        return self.art


def make_session() -> tuple[Session, Backends, list[dict]]:
    backends = Backends(
        input=FakeInput(), audio=FakeAudio(), media=ArtMedia(),
        clipboard=FakeClipboard(),
    )
    sent: list[dict] = []
    session = Session(backends, on_state=sent.append)
    return session, backends, sent


def build(tmp_path, command, path, *, headers=None, body=b"", client=LOCAL, session=None):
    """Собрать обработчик в обход конструктора и подсунуть ему двойники."""
    if session is None:
        session, _, _ = make_session()
    handler_cls = h.make_handler(session, TOKEN, Path(tmp_path))
    handler = handler_cls.__new__(handler_cls)
    handler.command = command
    handler.path = path
    handler.client_address = (client, 44444)
    handler.request_version = "HTTP/1.1"
    message = email.message.Message()
    for name, value in (headers or {}).items():
        message[name] = value
    handler.headers = message
    handler.rfile = io.BytesIO(body)
    handler.wfile = io.BytesIO()
    handler.connection = FakeSocket()
    handler.close_connection = False

    rec = Recorder()
    handler.send_response = rec.send_response
    handler.send_header = rec.send_header
    handler.end_headers = rec.end_headers
    handler.send_error = rec.send_error
    handler.log_message = rec.log_message
    return handler, rec, session


def _ws_headers(**extra: str) -> dict[str, str]:
    base = {
        "Upgrade": "websocket",
        "Origin": f"http://{HOSTPORT}",
        "Host": HOSTPORT,
        "Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ==",
    }
    base.update(extra)
    return base


# --- C1: манифест несёт токен в start_url ----------------------------------

def test_manifest_without_token_is_refused(tmp_path):
    """Манифест несёт токен в start_url — отдавать его без токена нельзя."""
    handler, rec, _ = build(tmp_path, "GET", "/manifest.webmanifest")
    handler.do_GET()
    assert rec.code == 403


def test_manifest_with_token_is_served_and_not_cached(tmp_path):
    """С верным токеном манифест отдаётся, но кэшировать его нельзя."""
    handler, rec, _ = build(tmp_path, "GET", f"/manifest.webmanifest?t={TOKEN}")
    handler.do_GET()
    assert rec.code == 200
    assert rec.headers["Cache-Control"] == "no-store"
    body = json.loads(handler.wfile.getvalue())
    assert body["start_url"] == f"/?t={TOKEN}"


# --- I2: обложка — символическая ссылка и потолок размера ------------------

def test_art_refuses_a_symlink(tmp_path):
    """Ссылка ведёт куда угодно, в том числе за пределы каталога обложек."""
    outside = tmp_path / "outside"
    outside.mkdir()
    real = outside / "secret.png"
    real.write_bytes(b"\x89PNG\r\n\x1a\n")
    link = tmp_path / "cover.png"
    link.symlink_to(real)

    session, backends, _ = make_session()
    backends.media.art = str(link)
    handler, rec, _ = build(tmp_path, "GET", f"/art?t={TOKEN}&id=1", session=session)
    handler.do_GET()
    assert rec.code == 404


def test_art_refuses_a_file_over_the_size_cap(tmp_path):
    """Иначе файл в сотни мегабайт целиком читается в память."""
    big = tmp_path / "big.png"
    with big.open("wb") as fh:
        fh.seek(h.MAX_ART_BYTES + 1)
        fh.write(b"\0")

    session, backends, _ = make_session()
    backends.media.art = str(big)
    handler, rec, _ = build(tmp_path, "GET", f"/art?t={TOKEN}&id=1", session=session)
    handler.do_GET()
    assert rec.code == 404


# --- I3: рукопожатие без ключа --------------------------------------------

def test_websocket_without_key_answers_400(tmp_path):
    """Отсутствующий заголовок рукопожатия не должен ронять обработчик."""
    headers = _ws_headers()
    del headers["Sec-WebSocket-Key"]
    handler, rec, _ = build(tmp_path, "GET", f"/ws?t={TOKEN}", headers=headers)
    handler.do_GET()  # не должно бросить
    assert rec.code == 400


# --- I4: снятие получателя при обрыве ------------------------------------

def test_websocket_removes_its_listener_on_disconnect(tmp_path):
    """Иначе состояние продолжает уходить в мёртвый сокет."""
    session, _, _ = make_session()
    baseline = list(session._listeners)
    handler, rec, _ = build(tmp_path, "GET", f"/ws?t={TOKEN}",
                            headers=_ws_headers(), session=session)
    handler.do_GET()
    assert rec.code == 101
    assert session._listeners == baseline


# --- I7: длина тела ----------------------------------------------------

def test_post_refuses_non_numeric_content_length(tmp_path):
    """Нечисловая длина роняла обработчик."""
    handler, rec, _ = build(tmp_path, "POST", f"/e?t={TOKEN}",
                            headers={"Host": HOSTPORT, "Content-Length": "abc"})
    handler.do_POST()  # не должно бросить
    assert rec.code == 400


def test_post_refuses_oversized_body_without_reading_it(tmp_path):
    """Отрицательная или огромная длина читала тело до конца в память."""
    handler, rec, _ = build(tmp_path, "POST", f"/e?t={TOKEN}", body=b"x" * 64,
                            headers={"Host": HOSTPORT,
                                     "Content-Length": str(h.MAX_BODY_BYTES + 1)})
    handler.do_POST()
    assert rec.code == 413
    assert handler.rfile.tell() == 0


def test_post_from_foreign_origin_is_refused(tmp_path):
    """У /e тот же барьер источника, что и у /ws: событие приходит тем же путём."""
    handler, rec, _ = build(tmp_path, "POST", f"/e?t={TOKEN}", body=b"[]",
                            headers={"Host": HOSTPORT,
                                     "Origin": "http://evil.example",
                                     "Content-Length": "2"})
    handler.do_POST()
    assert rec.code == 403
