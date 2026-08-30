"""Сборка доступных реализаций платформы в один набор.

Недоступная возможность не мешает запуску: она просто не попадает в
набор и отключается в интерфейсе телефона.
"""

import sys

from lanpad.platform.base import Backends, InputBackend


def build_backends(input_backend: InputBackend | None = None) -> Backends:
    """Собрать набор реализаций для текущей системы.

    `input_backend` позволяет подставить двойник в тестах.
    """
    if not sys.platform.startswith("linux"):
        raise RuntimeError(
            f"Платформа {sys.platform} пока не поддерживается. "
            "Реализован только Linux."
        )

    from lanpad.platform.linux.audio_wpctl import WpctlAudio
    from lanpad.platform.linux.clipboard_wl import WaylandClipboard
    from lanpad.platform.linux.media_mpris import MprisMedia

    if input_backend is None:
        from lanpad.platform.linux.input_uinput import UinputInput

        input_backend = UinputInput()

    audio = WpctlAudio() if WpctlAudio.is_available() else None
    clipboard = WaylandClipboard() if WaylandClipboard.is_available() else None

    media = None
    if MprisMedia.is_available():
        try:
            media = MprisMedia()
        except Exception:  # noqa: BLE001 — нет сессионной шины, работаем без медиа
            media = None

    return Backends(input=input_backend, audio=audio, media=media, clipboard=clipboard)
