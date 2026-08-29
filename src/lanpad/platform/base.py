"""Интерфейсы, за которыми прячется операционная система.

Каждый интерфейс независим. Отсутствие любого из них, кроме ввода,
означает лишь отключённую возможность, а не поломку агента.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass

from lanpad.protocol import AudioState, Capabilities, MediaState


class InputBackend(ABC):
    """Внедрение движений курсора и нажатий клавиш."""

    @abstractmethod
    def move(self, dx: int, dy: int) -> None: ...

    @abstractmethod
    def wheel(self, amount: int) -> None: ...

    @abstractmethod
    def button(self, name: str, pressed: bool) -> None: ...

    @abstractmethod
    def click(self, name: str) -> None: ...

    @abstractmethod
    def tap(self, key: str) -> None: ...

    @abstractmethod
    def key_hold(self, key: str, pressed: bool) -> None: ...

    @abstractmethod
    def combo(self, keys: list[str]) -> None: ...

    @abstractmethod
    def type_text(self, text: str) -> None: ...

    def can_type(self, text: str) -> bool:
        """Можно ли набрать текст напрямую, без буфера обмена.

        Раскладка покрывает латиницу и знаки препинания. Кириллица и
        эмодзи набираются вставкой — это решает сессия.
        """
        return bool(text) and text.isascii()

    def close(self) -> None:  # noqa: B027
        """Освободить устройство. По умолчанию делать нечего."""
        pass


class AudioBackend(ABC):
    @abstractmethod
    def state(self) -> AudioState: ...

    @abstractmethod
    def step(self, delta: int) -> None: ...

    @abstractmethod
    def set_percent(self, percent: int) -> None: ...

    @abstractmethod
    def toggle_mute(self) -> None: ...


class MediaBackend(ABC):
    @abstractmethod
    def state(self) -> MediaState | None: ...

    @abstractmethod
    def command(self, action: str) -> None: ...

    @abstractmethod
    def seek(self, position: float) -> None: ...

    @abstractmethod
    def subscribe(self, callback: Callable[[MediaState | None], None]) -> None:
        """Вызывать callback при каждом изменении состояния воспроизведения."""

    @abstractmethod
    def art_path_for(self, art_id: str) -> str | None:
        """Путь к файлу обложки по её идентификатору, если он всё ещё актуален."""

    def close(self) -> None:  # noqa: B027
        """Отписаться от источника событий."""
        pass


class ClipboardBackend(ABC):
    @abstractmethod
    def copy(self, text: str) -> bool:
        """Положить текст в буфер. Возвращает успех."""


@dataclass
class Backends:
    """Набор реализаций, доступных на этой машине."""

    input: InputBackend
    audio: AudioBackend | None
    media: MediaBackend | None
    clipboard: ClipboardBackend | None

    def capabilities(self) -> Capabilities:
        return Capabilities(
            audio=self.audio is not None,
            media=self.media is not None,
            clipboard=self.clipboard is not None,
        )

    def close(self) -> None:
        self.input.close()
        if self.media is not None:
            self.media.close()
