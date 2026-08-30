"""Тесты точки входа.

Проверяют не текст сообщений, а свойства, без которых агент невозможно
использовать: вывод обязан доходить до журнала, а не оседать в буфере.
"""

import io
import sys

from lanpad.__main__ import _use_line_buffering


class FakeStream(io.StringIO):
    """Поток, помнящий, о чём его просили."""

    def __init__(self) -> None:
        super().__init__()
        self.line_buffering_set: bool | None = None

    def reconfigure(self, *, line_buffering: bool | None = None, **_kwargs) -> None:
        self.line_buffering_set = line_buffering


def test_output_is_line_buffered(monkeypatch):
    """Иначе QR оседает в буфере и не доходит до журнала systemd."""
    stream = FakeStream()
    monkeypatch.setattr(sys, "stdout", stream)
    _use_line_buffering()
    assert stream.line_buffering_set is True


def test_survives_a_stream_without_reconfigure(monkeypatch):
    """Вывод могли подменить объектом попроще — падать из-за этого нельзя."""
    monkeypatch.setattr(sys, "stdout", io.StringIO())
    _use_line_buffering()
