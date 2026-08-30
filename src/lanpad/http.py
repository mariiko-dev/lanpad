"""HTTP-слой: статика, манифест, обложки и WebSocket-соединение."""

import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from lanpad import ws
from lanpad.config import is_private_client, token_matches
from lanpad.protocol import parse_events
from lanpad.session import Session

IMMUTABLE_EXTENSIONS = {".js", ".css", ".woff2", ".png", ".ico", ".svg"}
IMMUTABLE_HEADER = "public, max-age=31536000, immutable"
NO_CACHE_HEADER = "no-cache"


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


def origin_allowed(origin: str | None, host: str) -> bool:
    """Соединение принимается только со своей же страницы.

    Отсутствие заголовка означает не-браузерного клиента: подделать
    межсайтовый запрос он не может.
    """
    if origin is None:
        return True
    parsed = urlparse(origin)
    return parsed.netloc == host


def safe_static_path(web_root: Path, relative: str) -> Path | None:
    """Путь к файлу внутри каталога статики или None, если выход за его пределы."""
    candidate = (web_root / unquote(relative).lstrip("/")).resolve()
    root = web_root.resolve()
    if root not in candidate.parents and candidate != root:
        return None
    return candidate if candidate.is_file() else None


def cache_header_for(path: str) -> str:
    extension = os.path.splitext(path)[1].lower()
    if extension in IMMUTABLE_EXTENSIONS and path.startswith("/assets/"):
        return IMMUTABLE_HEADER
    return NO_CACHE_HEADER


def make_handler(session: Session, token: str, web_root: Path):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        # --- вспомогательное ---------------------------------------------

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
            self._respond(200, ctype or "application/octet-stream",
                          target.read_bytes(), cache_header_for(relative))

        # --- маршруты -----------------------------------------------------

        def do_GET(self) -> None:  # noqa: N802
            if not self._client_allowed():
                self.send_error(403)
                return
            path = urlparse(self.path).path

            if path == "/":
                self._serve_static("/index.html")
            elif path == "/manifest.webmanifest":
                self._respond(200, "application/manifest+json",
                              json.dumps(manifest(token), ensure_ascii=False))
            elif path == "/art":
                self._serve_art()
            elif path == "/ws":
                self._serve_websocket()
            else:
                self._serve_static(path)

        do_HEAD = do_GET

        def do_POST(self) -> None:  # noqa: N802
            if not self._client_allowed() or urlparse(self.path).path != "/e":
                self.send_error(404)
                return
            if not self._authorised():
                self.send_error(403)
                return
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"[]"
            session.handle(parse_events(raw))
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _serve_art(self) -> None:
            if not self._authorised():
                self.send_error(403)
                return
            raw = session.media_art_path(self._query().get("id", [""])[0])
            if raw is None:
                self.send_error(404)
                return
            target = Path(raw).resolve()
            if not target.is_file() or target.is_symlink():
                self.send_error(404)
                return
            ctype, _ = mimetypes.guess_type(str(target))
            if ctype is None or not ctype.startswith("image/"):
                self.send_error(404)
                return
            self._respond(200, ctype, target.read_bytes(), IMMUTABLE_HEADER)

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

            self.close_connection = True
            self.send_response(101)
            self.send_header("Upgrade", "websocket")
            self.send_header("Connection", "Upgrade")
            self.send_header("Sec-WebSocket-Accept",
                             ws.accept_key(self.headers["Sec-WebSocket-Key"]))
            self.end_headers()

            connection = self.connection
            connection.settimeout(None)

            def push(state: dict) -> None:
                try:  # noqa: SIM105
                    connection.sendall(ws.encode_frame(json.dumps(state, ensure_ascii=False)))
                except OSError:
                    pass

            session.set_listener(push)
            push(session.current_state())

            try:
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
                session.set_listener(lambda _state: None)

        def log_message(self, *args) -> None:
            """Не засорять вывод: каждое движение курсора — это запрос."""

    return Handler


def make_server(session: Session, token: str, web_root: Path, port: int) -> ThreadingHTTPServer:
    mimetypes.init()
    server = ThreadingHTTPServer(("0.0.0.0", port), make_handler(session, token, web_root))  # noqa: S104
    server.daemon_threads = True
    return server
