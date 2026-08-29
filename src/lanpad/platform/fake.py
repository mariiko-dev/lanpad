"""Записывающие двойники для тестов.

Живут в пакете, а не в каталоге тестов, потому что нужны и тестам
сессии, и тестам HTTP-слоя.
"""

from collections.abc import Callable

from lanpad.platform.base import AudioBackend, ClipboardBackend, InputBackend, MediaBackend
from lanpad.protocol import AudioState, MediaState


class FakeInput(InputBackend):
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def move(self, dx: int, dy: int) -> None:
        self.calls.append(("move", dx, dy))

    def wheel(self, amount: int) -> None:
        self.calls.append(("wheel", amount))

    def button(self, name: str, pressed: bool) -> None:
        self.calls.append(("button", name, pressed))

    def click(self, name: str) -> None:
        self.calls.append(("click", name))

    def tap(self, key: str) -> None:
        self.calls.append(("tap", key))

    def key_hold(self, key: str, pressed: bool) -> None:
        self.calls.append(("key_hold", key, pressed))

    def combo(self, keys: list[str]) -> None:
        self.calls.append(("combo", list(keys)))

    def type_text(self, text: str) -> None:
        self.calls.append(("type_text", text))


class FakeAudio(AudioBackend):
    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self._volume = 50
        self._muted = False

    def state(self) -> AudioState:
        return AudioState(volume=self._volume, muted=self._muted)

    def step(self, delta: int) -> None:
        self.calls.append(("step", delta))
        self._volume = max(0, min(100, self._volume + delta))

    def set_percent(self, percent: int) -> None:
        self.calls.append(("set_percent", percent))
        self._volume = max(0, min(100, percent))

    def toggle_mute(self) -> None:
        self.calls.append(("toggle_mute",))
        self._muted = not self._muted


class FakeMedia(MediaBackend):
    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self._subscribers: list[Callable[[MediaState | None], None]] = []
        self._state = MediaState(
            playing=False, title="Тишина", artist="", art=None,
            position=0.0, duration=0.0, can_seek=True,
        )

    def state(self) -> MediaState | None:
        return self._state

    def command(self, action: str) -> None:
        self.calls.append(("command", action))
        if action == "play":
            self._state = MediaState(
                playing=not self._state.playing, title=self._state.title,
                artist=self._state.artist, art=self._state.art,
                position=self._state.position, duration=self._state.duration,
                can_seek=self._state.can_seek,
            )
        self._notify()

    def seek(self, position: float) -> None:
        self.calls.append(("seek", position))
        self._notify()

    def subscribe(self, callback: Callable[[MediaState | None], None]) -> None:
        self._subscribers.append(callback)

    def art_path_for(self, art_id: str) -> str | None:
        return None

    def _notify(self) -> None:
        for callback in self._subscribers:
            callback(self._state)


class FakeClipboard(ClipboardBackend):
    def __init__(self, succeeds: bool = True) -> None:
        self.calls: list[tuple] = []
        self._succeeds = succeeds

    def copy(self, text: str) -> bool:
        self.calls.append(("copy", text))
        return self._succeeds
