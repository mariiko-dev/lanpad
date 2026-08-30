"""HTTP-слой: статика, манифест, обложки и WebSocket-соединение."""

import ipaddress
import json
import mimetypes
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse, urlsplit

from lanpad import ws
from lanpad.config import is_private_client, token_matches
from lanpad.protocol import parse_events
from lanpad.session import Session

IMMUTABLE_EXTENSIONS = {".js", ".css", ".woff2", ".png", ".ico", ".svg"}
IMMUTABLE_HEADER = "public, max-age=31536000, immutable"
PRIVATE_IMMUTABLE_HEADER = "private, max-age=31536000, immutable"
NO_CACHE_HEADER = "no-cache"
MAX_ART_BYTES = 16 * 1024 * 1024
MAX_BODY_BYTES = 1 << 20


def manifest(token: str) -> dict:
    return {
        "name": "lanpad",
        "short_name": "lanpad",
        "description": "Тачпад, клавиатура и пульт для компьютера в локальной сети",
        "start_url": f"/?t={token}",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#000000",
        "theme_color": "#000000",
        "icons": [
            {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"},
            {"src": "/icon-maskable-512.png", "sizes": "512x512",
             "type": "image/png", "purpose": "maskable"},
        ],
    }


def _authority_is_literal(authority: str) -> bool:
    """Хост в запросе — литеральный адрес, а не имя.

    Имя может быть перепривязано к адресу агента, и тогда сравнение
    `Origin` с `Host` перестаёт быть барьером: обе половины пришлёт
    один и тот же чужой сайт. К агенту ходят по адресу из QR.
    """
    try:
        hostname = urlsplit(f"//{authority}").hostname
    except ValueError:
        return False
    if hostname is None:
        return False
    if hostname == "localhost":
        return True
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        return False
    return True


def origin_allowed(origin: str | None, host: str) -> bool:
    """Соединение принимается только со своей же страницы.

    Отсутствие заголовка означает не-браузерного клиента: подделать
    межсайтовый запрос он не может.
    """
    if not _authority_is_literal(host):
        return False
    if origin is None:
        return True
    parsed = urlsplit(origin)
    return parsed.scheme == "http" and parsed.netloc == host


def safe_static_path(web_root: Path, relative: str) -> Path | None:
    """Путь к файлу внутри каталога статики или None, если выход за его пределы.

    Любая негодная форма пути означает отказ, а не исключение: этот путь
    приходит из сети и доступен без токена.
    """
    try:
        candidate = (web_root / unquote(relative).lstrip("/")).resolve()
        root = web_root.resolve()
        if root not in candidate.parents and candidate != root:
            return None
        return candidate if candidate.is_file() else None
    except (OSError, ValueError):
        return None


_HASHED_NAME = re.compile(r"-[0-9a-f]{6,}\.[a-z0-9]+$")


def cache_header_for(path: str) -> str:
    """Заголовок кэширования.

    Вечное кэширование выдаётся только именам с хешем содержимого:
    иначе обновление агента не дойдёт до уже спаренного телефона
    никогда, потому что `immutable` запрещает браузеру перепроверять.
    """
    extension = os.path.splitext(path)[1].lower()
    if extension in IMMUTABLE_EXTENSIONS and path.startswith("/assets/"):
        return IMMUTABLE_HEADER if _HASHED_NAME.search(path) else "no-cache"
    return NO_CACHE_HEADER


def make_handler(session: Session, token: str, web_root: Path):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "lanpad"
        sys_version = ""
        timeout = 30

        # --- вспомогательное ---------------------------------------------

        def send_response(self, code, message=None):
            """Ставить защитные заголовки и на ответах об ошибке.

            Иначе отказ на пути с токеном отдаётся без Referrer-Policy,
            а токен у браузера в адресной строке.
            """
            super().send_response(code, message)
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")

        def _query(self) -> dict:
            return parse_qs(urlparse(self.path).query)

        def _authorised(self) -> bool:
            supplied = self._query().get("t", [""])[0]
            return token_matches(unquote(supplied), token)

        def _client_allowed(self) -> bool:
            return is_private_client(self.client_address[0])

        def _respond(self, code: int, ctype: str, body: bytes | str,
                     cache: str = NO_CACHE_HEADER, extra: dict | None = None) -> None:
            if isinstance(body, str):
                body = body.encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", cache)
            for key, value in (extra or {}).items():
                self.send_header(key, value)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _serve_static(self, relative: str) -> None:
            target = safe_static_path(web_root, relative)
            if target is None:
                self.send_error(404)
                return
            ctype, _ = mimetypes.guess_type(str(target))
            if target.suffix == ".js":
                ctype = "text/javascript"
            elif target.suffix == ".woff2":
                ctype = "font/woff2"
            try:
                body = target.read_bytes()
            except OSError:
                self.send_error(404)
                return
            self._respond(200, ctype or "application/octet-stream",
                          body, cache_header_for(relative))

        # --- маршруты -----------------------------------------------------

        def do_GET(self) -> None:
            if not self._client_allowed():
                self.send_error(403)
                return
            path = urlparse(self.path).path

            if path == "/":
                self._serve_static("/index.html")
            elif path == "/manifest.webmanifest":
                if not self._authorised():
                    self.send_error(403)
                    return
                self._respond(
                    200, "application/manifest+json",
                    json.dumps(manifest(token), ensure_ascii=False),
                    "no-store",
                )
            elif path == "/art":
                self._serve_art()
            elif path == "/ws":
                self._serve_websocket()
            else:
                self._serve_static(path)

        do_HEAD = do_GET

        def do_POST(self) -> None:
            if not self._client_allowed() or urlparse(self.path).path != "/e":
                self.send_error(404)
                return
            if not self._authorised():
                self.send_error(403)
                return
            if not origin_allowed(self.headers.get("Origin"), self.headers.get("Host", "")):
                self.send_error(403)
                return
            try:
                length = int(self.headers.get("Content-Length", 0))
            except (TypeError, ValueError):
                self.send_error(400)
                return
            if not 0 <= length <= MAX_BODY_BYTES:
                self.send_error(413)
                return
            raw = self.rfile.read(length) if length else b"[]"
            session.handle(parse_events(raw))
            self.send_response(204)
            self.end_headers()

        def _serve_art(self) -> None:
            if not self._authorised():
                self.send_error(403)
                return
            raw = session.media_art_path(self._query().get("id", [""])[0])
            if raw is None:
                self.send_error(404)
                return
            try:
                source = Path(raw)
                if source.is_symlink():
                    self.send_error(404)
                    return
                target = source.resolve()
                if not target.is_file() or target.stat().st_size > MAX_ART_BYTES:
                    self.send_error(404)
                    return
            except (OSError, ValueError):
                self.send_error(404)
                return
            ctype, _ = mimetypes.guess_type(str(target))
            if ctype is None or not ctype.startswith("image/"):
                self.send_error(404)
                return
            try:
                body = target.read_bytes()
            except OSError:
                self.send_error(404)
                return
            self._respond(200, ctype, body, PRIVATE_IMMUTABLE_HEADER)

        def _serve_websocket(self) -> None:
            if not self._authorised():
                self.send_error(403)
                return
            if self.headers.get("Upgrade", "").lower() != "websocket":
                self.send_error(400)
                return
            if not origin_allowed(self.headers.get("Origin"), self.headers.get("Host", "")):
                self.send_error(403)
                return
            key = self.headers.get("Sec-WebSocket-Key")
            if not key:
                self.send_error(400)
                return

            self.close_connection = True
            self.send_response(101)
            self.send_header("Upgrade", "websocket")
            self.send_header("Connection", "Upgrade")
            self.send_header("Sec-WebSocket-Accept", ws.accept_key(key))
            self.end_headers()

            connection = self.connection
            connection.settimeout(None)

            def push(state: dict) -> None:
                try:  # noqa: SIM105
                    connection.sendall(ws.encode_frame(json.dumps(state, ensure_ascii=False)))
                except OSError:
                    pass

            session.add_listener(push)
            try:
                push(session.current_state())
                while True:
                    frame = ws.read_frame(connection.recv)
                    if frame is None:
                        break
                    if frame.opcode == ws.OP_PING:
                        connection.sendall(ws.encode_frame(frame.payload, ws.OP_PONG))
                    elif frame.opcode == ws.OP_TEXT and frame.payload:
                        session.handle(parse_events(frame.payload))
            except OSError:
                pass
            finally:
                session.remove_listener(push)

        def log_message(self, *args) -> None:
            """Не засорять вывод: каждое движение курсора — это запрос."""

    return Handler


def make_server(session: Session, token: str, web_root: Path, port: int) -> ThreadingHTTPServer:
    mimetypes.init()
    server = ThreadingHTTPServer(("0.0.0.0", port), make_handler(session, token, web_root))
    server.daemon_threads = True
    return server
