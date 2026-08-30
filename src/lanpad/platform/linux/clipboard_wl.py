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
            return ["wl-copy", "--"]
        if shutil.which("xclip"):
            return ["xclip", "-selection", "clipboard"]
        return None

    @staticmethod
    def is_available() -> bool:
        return WaylandClipboard._pick_command() is not None

    def copy(self, text: str) -> bool:
        if self._command is None:
            return False
        try:
            if self._command[0] == "wl-copy":
                subprocess.run([*self._command, text], check=False, timeout=TIMEOUT)  # noqa: S603
            else:
                subprocess.run(  # noqa: S603
                    self._command, input=text, text=True, check=False, timeout=TIMEOUT,
                )
        except (OSError, subprocess.SubprocessError):
            return False
        return True
