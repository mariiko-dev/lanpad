import subprocess

import pytest

from lanpad.platform.linux.clipboard_wl import WaylandClipboard


class RunSpy:
    """Двойник subprocess.run: запоминает вызов, при желании ломается."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple] = []

    def __call__(self, command, **kwargs):
        self.calls.append((command, kwargs))
        if self.error is not None:
            raise self.error
        return subprocess.CompletedProcess(command, 0)


@pytest.fixture
def clipboard(monkeypatch):
    monkeypatch.setattr(
        WaylandClipboard, "_pick_command", staticmethod(lambda: ["wl-copy"])
    )
    return WaylandClipboard()


def test_copy_asks_subprocess_to_check_the_exit_code(clipboard, monkeypatch):
    """Без этого ненулевой код возврата выглядел бы успехом."""
    spy = RunSpy()
    monkeypatch.setattr(subprocess, "run", spy)
    clipboard.copy("текст")
    assert spy.calls[0][1]["check"] is True


def test_copy_reports_failure_on_nonzero_exit(clipboard, monkeypatch):
    error = subprocess.CalledProcessError(1, "wl-copy")
    monkeypatch.setattr(subprocess, "run", RunSpy(error=error))
    assert clipboard.copy("текст") is False


@pytest.mark.parametrize("error", [
    FileNotFoundError("нет команды"),
    PermissionError("нельзя"),
    subprocess.TimeoutExpired("wl-copy", 3),
    ValueError("embedded null byte"),
])
def test_copy_reports_failure_on_any_breakage(clipboard, monkeypatch, error):
    monkeypatch.setattr(subprocess, "run", RunSpy(error=error))
    assert clipboard.copy("текст") is False


def test_copy_sends_text_on_stdin_not_as_argument(clipboard, monkeypatch):
    """Аргументом длинный текст не влезет, а нулевой байт вызовет ошибку."""
    spy = RunSpy()
    monkeypatch.setattr(subprocess, "run", spy)
    clipboard.copy("секрет")
    command, kwargs = spy.calls[0]
    assert "секрет" not in command
    assert kwargs["input"] == "секрет"


def test_copy_discards_command_output_without_reading_it(clipboard, monkeypatch):
    """Захват вывода повесил бы xclip: он уходит в фон, не закрывая дескрипторы."""
    spy = RunSpy()
    monkeypatch.setattr(subprocess, "run", spy)
    clipboard.copy("текст")
    kwargs = spy.calls[0][1]
    assert kwargs["stdout"] is subprocess.DEVNULL
    assert kwargs["stderr"] is subprocess.DEVNULL
    assert "capture_output" not in kwargs


@pytest.mark.parametrize("text", [
    "",
    "две\nстроки",
    "с нулевым\x00байтом",
    "кириллица и эмодзи 🎧",
    "-n",
    "--help",
    "х" * 100_000,
])
def test_copy_survives_difficult_text(clipboard, monkeypatch, text):
    monkeypatch.setattr(subprocess, "run", RunSpy())
    assert clipboard.copy(text) is True


def test_copy_without_any_tool_returns_false(monkeypatch):
    monkeypatch.setattr(WaylandClipboard, "_pick_command", staticmethod(lambda: None))
    assert WaylandClipboard().copy("текст") is False
