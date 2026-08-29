import pytest

from lanpad import ws


def reader_for(data: bytes):
    """Отдаёт байты порциями, как это делал бы сокет."""
    buffer = bytearray(data)

    def recv(n: int) -> bytes | None:
        if not buffer:
            return None
        chunk = bytes(buffer[:n])
        del buffer[:n]
        return chunk

    return recv


def masked_frame(payload: bytes, opcode: int = ws.OP_TEXT) -> bytes:
    mask = b"\x01\x02\x03\x04"
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    header = bytearray([0x80 | opcode])
    length = len(payload)
    if length < 126:
        header.append(0x80 | length)
    elif length < 65536:
        header.append(0x80 | 126)
        header += length.to_bytes(2, "big")
    else:
        header.append(0x80 | 127)
        header += length.to_bytes(8, "big")
    return bytes(header) + mask + masked


def test_accept_key_matches_rfc_example():
    assert ws.accept_key("dGhlIHNhbXBsZSBub25jZQ==") == "s3pPLMBiTxaQ9kYGzzhZRbK+xOo="


def test_encode_short_text_frame():
    frame = ws.encode_frame("hi")
    assert frame == b"\x81\x02hi"


def test_encode_medium_frame_uses_extended_length():
    frame = ws.encode_frame(b"x" * 200)
    assert frame[0] == 0x81
    assert frame[1] == 126
    assert int.from_bytes(frame[2:4], "big") == 200


def test_encode_large_frame_uses_long_length():
    frame = ws.encode_frame(b"x" * 70_000)
    assert frame[1] == 127
    assert int.from_bytes(frame[2:10], "big") == 70_000


def test_reads_masked_text_frame():
    frame = ws.read_frame(reader_for(masked_frame(b'[["w",1]]')))
    assert frame.opcode == ws.OP_TEXT
    assert frame.payload == b'[["w",1]]'


def test_reads_frame_with_extended_length():
    payload = b"y" * 300
    frame = ws.read_frame(reader_for(masked_frame(payload)))
    assert frame.payload == payload


def test_close_frame_returns_none():
    assert ws.read_frame(reader_for(masked_frame(b"", ws.OP_CLOSE))) is None


def test_exhausted_socket_returns_none():
    assert ws.read_frame(reader_for(b"")) is None


def test_ping_frame_is_reported_so_caller_can_pong():
    frame = ws.read_frame(reader_for(masked_frame(b"ping", ws.OP_PING)))
    assert frame.opcode == ws.OP_PING
    assert frame.payload == b"ping"


def test_oversized_frame_is_refused():
    """Кадр, объявляющий гигабайт, не должен приводить к попытке его прочитать."""
    header = bytes([0x81, 0x80 | 127]) + (2**40).to_bytes(8, "big") + b"\x00\x00\x00\x00"
    assert ws.read_frame(reader_for(header)) is None


@pytest.mark.parametrize("text", ["", "привет", "a" * 5000])
def test_encode_accepts_str_and_bytes(text):
    assert ws.encode_frame(text) == ws.encode_frame(text.encode())
