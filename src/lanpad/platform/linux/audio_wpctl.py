"""Громкость через PipeWire, командой wpctl."""

import math
import re
import shutil
import subprocess

from lanpad.platform.base import AudioBackend
from lanpad.protocol import AudioState

SINK = "@DEFAULT_AUDIO_SINK@"
TIMEOUT = 2
_VOLUME_RE = re.compile(r"Volume:\s*([0-9]+(?:\.[0-9]+)?)")


def parse_volume(output: str) -> AudioState:
    """Разобрать вывод `wpctl get-volume`.

    Любая неожиданная форма вывода означает «громкость неизвестна», а не
    падение: сломанный звук не должен ронять агент целиком. Бесконечность
    проверяется отдельно — `float` возвращает её молча, без исключения.
    """
    match = _VOLUME_RE.search(output)
    if match is None:
        return AudioState(volume=None, muted=False)
    try:
        level = float(match.group(1))
    except (ValueError, OverflowError):
        return AudioState(volume=None, muted=False)
    if not math.isfinite(level):
        return AudioState(volume=None, muted=False)
    return AudioState(
        volume=round(level * 100),
        muted="[MUTED]" in output,
    )


class WpctlAudio(AudioBackend):
    @staticmethod
    def is_available() -> bool:
        return shutil.which("wpctl") is not None

    def _run(self, *args: str) -> str:
        try:
            result = subprocess.run(  # noqa: S603
                ["wpctl", *args],
                capture_output=True, text=True, timeout=TIMEOUT, check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return ""
        return result.stdout

    def state(self) -> AudioState:
        return parse_volume(self._run("get-volume", SINK))

    def step(self, delta: int) -> None:
        sign = "+" if delta >= 0 else "-"
        self._run("set-volume", "-l", "1.0", SINK, f"{abs(int(delta))}%{sign}")

    def set_percent(self, percent: int) -> None:
        clamped = max(0, min(100, int(percent)))
        self._run("set-volume", "-l", "1.0", SINK, f"{clamped}%")

    def toggle_mute(self) -> None:
        self._run("set-mute", SINK, "toggle")
