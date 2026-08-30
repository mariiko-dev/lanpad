"""Применение событий к системе и рассылка состояния телефону.

Состояние отправляется по изменению, а не по расписанию. Движения курсора
изменением не считаются: иначе каждое касание пальца порождало бы пакет в
обратную сторону и съедало ту самую задержку, ради которой всё делается.
"""

import logging
from collections.abc import Callable
from contextlib import suppress

from lanpad import protocol as p
from lanpad.platform.base import Backends

_log = logging.getLogger(__name__)

_CYRILLIC_FALLBACK_KEYS = ["ctrl", "v"]
_TERMINAL_PASTE_KEYS = ["ctrl", "shift", "v"]


class Session:
    def __init__(self, backends: Backends, on_state: Callable[[dict], None] | None = None) -> None:
        self._backends = backends
        self._listeners: list[Callable[[dict], None]] = []
        if on_state is not None:
            self._listeners.append(on_state)
        if backends.media is not None:
            backends.media.subscribe(self._on_media_changed)

    # --- приём событий ----------------------------------------------------

    def handle(self, events: list[p.Event]) -> None:
        """Применить пакет событий.

        Каждое событие защищено отдельно намеренно. Телефон шлёт
        перетаскивание как пару «нажать — отпустить» с движениями между
        ними, и обрыв пакета посередине оставил бы кнопку зажатой.
        Разбор протокола так же снисходителен к отдельному элементу —
        слой применения обязан вести себя согласованно.
        """
        state_touched = False
        for event in events:
            try:
                state_touched |= self._apply(event)
            except Exception:  # noqa: BLE001
                _log.exception("не удалось применить событие %r", event)
        if state_touched:
            self._push()

    def _apply(self, event: p.Event) -> bool:  # noqa: PLR0911, PLR0912
        """Применить событие. Возвращает True, если состояние могло измениться."""
        backends = self._backends
        match event:
            case p.Move(dx, dy):
                backends.input.move(dx, dy)
            case p.Wheel(amount):
                backends.input.wheel(amount)
            case p.Button(name, pressed):
                backends.input.button(name, pressed)
            case p.Click(name):
                backends.input.click(name)
            case p.Tap(key):
                backends.input.tap(key)
            case p.KeyHold(key, pressed):
                backends.input.key_hold(key, pressed)
            case p.Combo(keys):
                backends.input.combo(keys)
            case p.TypeText(text):
                self._type(text)
            case p.Paste(text, terminal):
                self._paste(text, terminal)
            case p.VolumeStep(delta):
                if backends.audio is not None:
                    backends.audio.step(delta)
                    return True
            case p.VolumeSet(percent):
                if backends.audio is not None:
                    backends.audio.set_percent(percent)
                    return True
            case p.VolumeMuteToggle():
                if backends.audio is not None:
                    backends.audio.toggle_mute()
                    return True
            case p.MediaCommand(action):
                if backends.media is not None:
                    backends.media.command(action)
            case p.Seek(position):
                if backends.media is not None:
                    backends.media.seek(position)
        return False

    # --- текст ------------------------------------------------------------

    def _type(self, text: str) -> None:
        """Набрать текст напрямую, а непечатаемый — через буфер обмена."""
        typer = self._backends.input
        if not typer.can_type(text):
            self._paste(text, terminal=False)
            return
        typer.type_text(text)

    def _paste(self, text: str, terminal: bool) -> None:
        clipboard = self._backends.clipboard
        if clipboard is None or not clipboard.copy(text):
            return
        keys = _TERMINAL_PASTE_KEYS if terminal else _CYRILLIC_FALLBACK_KEYS
        self._backends.input.combo(keys)

    # --- состояние --------------------------------------------------------

    def _on_media_changed(self, _state: p.MediaState | None) -> None:
        self._push()

    def add_listener(self, on_state: Callable[[dict], None]) -> None:
        """Подписать получателя состояния.

        Получателей может быть несколько: телефонов в сети бывает больше
        одного, и каждое соединение подписывается своим.
        """
        self._listeners.append(on_state)

    def remove_listener(self, on_state: Callable[[dict], None]) -> None:
        with suppress(ValueError):
            self._listeners.remove(on_state)

    def media_art_path(self, art_id: str) -> str | None:
        """Путь к файлу обложки — только из метаданных текущего трека."""
        media = self._backends.media
        return None if media is None else media.art_path_for(art_id)

    def current_state(self) -> dict:
        backends = self._backends
        return p.state_message(
            audio=backends.audio.state() if backends.audio is not None else None,
            media=backends.media.state() if backends.media is not None else None,
            caps=backends.capabilities(),
        )

    def _push(self) -> None:
        """Разослать состояние всем подписчикам.

        Сбор состояния и каждая отправка защищены по отдельности:
        получатели живут на другом конце сети, а `_on_media_changed`
        вызывается из диспетчера сигналов D-Bus, и исключение оттуда
        убило бы подписку целиком.
        """
        try:
            state = self.current_state()
        except Exception:  # noqa: BLE001
            _log.exception("не удалось собрать состояние")
            return
        for listener in list(self._listeners):
            try:
                listener(state)
            except Exception:  # noqa: BLE001
                _log.exception("получатель состояния бросил исключение")

    def close(self) -> None:
        self._backends.close()
