"""Минимальный фрейминг WebSocket поверх обычного сокета.

Полноценная библиотека здесь избыточна: обмен идёт короткими текстовыми
кадрами в одном направлении и служебными в другом.
"""

import base64
import hashlib
import struct
from collections.abc import Callable
from dataclasses import dataclass

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

OP_TEXT = 0x1
OP_BINARY = 0x2
OP_CLOSE = 0x8
OP_PING = 0x9
OP_PONG = 0xA

MAX_PAYLOAD = 1 << 20  # 1 МиБ — вставка текста заведомо короче


@dataclass(frozen=True)
class Frame:
    opcode: int
    payload: bytes


def accept_key(client_key: str) -> str:
    """Ответ на `Sec-WebSocket-Key` по правилам рукопожатия."""
    digest = hashlib.sha1((client_key + GUID).encode()).digest()
    return base64.b64encode(digest).decode()


def encode_frame(data: bytes | str, opcode: int = OP_TEXT) -> bytes:
    """Собрать кадр сервера — без маски, как требует протокол."""
    if isinstance(data, str):
        data = data.encode()
    header = bytearray([0x80 | opcode])
    length = len(data)
    if length < 126:
        header.append(length)
    elif length < 65536:
        header.append(126)
        header += struct.pack(">H", length)
    else:
        header.append(127)
        header += struct.pack(">Q", length)
    return bytes(header) + data


def _read_exactly(recv: Callable[[int], bytes | None], count: int) -> bytes | None:
    buffer = b""
    while len(buffer) < count:
        chunk = recv(count - len(buffer))
        if not chunk:
            return None
        buffer += chunk
    return buffer


def read_frame(recv: Callable[[int], bytes | None]) -> Frame | None:
    """Прочитать один кадр. `None` означает закрытие или негодные данные."""
    header = _read_exactly(recv, 2)
    if header is None:
        return None

    opcode = header[0] & 0x0F
    masked = bool(header[1] & 0x80)
    length = header[1] & 0x7F

    if length == 126:
        extended = _read_exactly(recv, 2)
        if extended is None:
            return None
        length = struct.unpack(">H", extended)[0]
    elif length == 127:
        extended = _read_exactly(recv, 8)
        if extended is None:
            return None
        length = struct.unpack(">Q", extended)[0]

    if length > MAX_PAYLOAD:
        return None

    mask = _read_exactly(recv, 4) if masked else b"\x00\x00\x00\x00"
    if mask is None:
        return None

    payload = _read_exactly(recv, length) if length else b""
    if payload is None:
        return None

    if masked:
        payload = bytes(byte ^ mask[i % 4] for i, byte in enumerate(payload))

    if opcode == OP_CLOSE:
        return None
    return Frame(opcode=opcode, payload=payload)
