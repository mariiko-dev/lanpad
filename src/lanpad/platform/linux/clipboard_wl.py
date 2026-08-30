"""Буфер обмена: wl-copy под Wayland, xclip как запасной путь под X11."""

import shutil
import subprocess

from lanpad.platform.base import ClipboardBackend

TIMEOUT = 3


class WaylandClipboard(ClipboardBackend):
    def __init__(self) -> None:
        self._command = self._pick_command()

    @staticmethod
    def _pick_command() -> list[str] | None:
        if shutil.which("wl-copy"):
            return ["wl-copy"]
        if shutil.which("xclip"):
            return ["xclip", "-selection", "clipboard"]
        return None

    @staticmethod
    def is_available() -> bool:
        return WaylandClipboard._pick_command() is not None

    def copy(self, text: str) -> bool:
        """Положить текст в буфер. Возвращает успех.

        Текст подаётся на стандартный ввод, а не аргументом командной
        строки: так снимается предел её длины и нулевой байт внутри
        текста не превращается в исключение. Обе команды такой режим
        поддерживают штатно.

        Вывод команд отправляется в никуда, а не захватывается: `xclip`
        при захвате селекции уходит в фон, не закрывая унаследованные
        дескрипторы, и чтение труб до конца файла повисло бы до таймаута,
        выдав провал за успешным копированием.

        Признак успеха здесь не формальность. Сессия вставляет текст
        сочетанием клавиш только после успешного копирования — иначе в
        чужое окно уехало бы прежнее содержимое буфера.
        """
        if self._command is None:
            return False
        try:
            subprocess.run(  # noqa: S603
                self._command,
                input=text,
                text=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
                timeout=TIMEOUT,
            )
        except (OSError, ValueError, subprocess.SubprocessError):
            return False
        return True
