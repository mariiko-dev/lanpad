"""Разбор входящих событий и сборка состояния для отправки телефону.

Разбор намеренно снисходителен к отдельным элементам пакета: негодное
событие отбрасывается, остальные исполняются. Но снисходительность не
означает доверчивость — числовые значения ограничены, чтобы подложенный
пакет не увёл курсор в бесконечность и не заставил агент печатать роман.
"""

import json
import math
from dataclasses import dataclass

from lanpad.keymap import MOUSE_BUTTONS

MAX_MOVE = 4000
MAX_WHEEL = 200
MAX_TEXT = 10_000
MAX_COMBO_KEYS = 6
MAX_EVENTS = 512
MEDIA_ACTIONS = frozenset({"play", "next", "prev"})


def _reject_constant(name: str) -> float:
    """JSON допускает NaN и Infinity — для нас это негодные числа."""
    raise ValueError(f"недопустимая константа: {name}")


@dataclass(frozen=True)
class Move:
    dx: int
    dy: int


@dataclass(frozen=True)
class Wheel:
    amount: int


@dataclass(frozen=True)
class Button:
    name: str
    pressed: bool


@dataclass(frozen=True)
class Click:
    name: str


@dataclass(frozen=True)
class Tap:
    key: str


@dataclass(frozen=True)
class KeyHold:
    key: str
    pressed: bool


@dataclass(frozen=True)
class Combo:
    keys: list[str]


@dataclass(frozen=True)
class TypeText:
    text: str


@dataclass(frozen=True)
class Paste:
    text: str
    terminal: bool


@dataclass(frozen=True)
class VolumeStep:
    delta: int


@dataclass(frozen=True)
class VolumeSet:
    percent: int


@dataclass(frozen=True)
class VolumeMuteToggle:
    pass


@dataclass(frozen=True)
class MediaCommand:
    action: str


@dataclass(frozen=True)
class Seek:
    position: float


Event = (
    Move | Wheel | Button | Click | Tap | KeyHold | Combo | TypeText
    | Paste | VolumeStep | VolumeSet | VolumeMuteToggle | MediaCommand | Seek
)


def _bounded_int(value: object, limit: int) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    number = int(value)
    return number if -limit <= number <= limit else None


def _text(value: object) -> str | None:
    if not isinstance(value, str) or len(value) > MAX_TEXT:
        return None
    return value


def _key_name(value: object) -> str | None:
    if not isinstance(value, str) or not value or len(value) > 20:
        return None
    return value


def _parse_one(item: object) -> Event | None:
    if not isinstance(item, list) or not item:
        return None
    kind = item[0]
    args = item[1:]

    match kind:
        case "m" if len(args) == 2:
            dx = _bounded_int(args[0], MAX_MOVE)
            dy = _bounded_int(args[1], MAX_MOVE)
            return Move(dx, dy) if dx is not None and dy is not None else None
        case "w" if len(args) == 1:
            amount = _bounded_int(args[0], MAX_WHEEL)
            return Wheel(amount) if amount is not None else None
        case "bd" | "bu" if len(args) == 1 and args[0] in MOUSE_BUTTONS:
            return Button(args[0], pressed=(kind == "bd"))
        case "click" if len(args) == 1 and args[0] in MOUSE_BUTTONS:
            return Click(args[0])
        case "tap" if len(args) == 1:
            key = _key_name(args[0])
            return Tap(key) if key else None
        case "kd" | "ku" if len(args) == 1:
            key = _key_name(args[0])
            return KeyHold(key, pressed=(kind == "kd")) if key else None
        case "combo" if len(args) == 1 and isinstance(args[0], list):
            keys = args[0]
            if not 0 < len(keys) <= MAX_COMBO_KEYS:
                return None
            if not all(_key_name(k) for k in keys):
                return None
            return Combo(list(keys))
        case "type" if len(args) == 1:
            text = _text(args[0])
            return TypeText(text) if text is not None else None
        case "paste" | "tpaste" if len(args) == 1:
            text = _text(args[0])
            return Paste(text, terminal=(kind == "tpaste")) if text is not None else None
        case "vol" if len(args) == 1:
            delta = _bounded_int(args[0], 100)
            return VolumeStep(delta) if delta is not None else None
        case "volset" if len(args) == 1:
            percent = _bounded_int(args[0], 10_000)
            return VolumeSet(max(0, min(100, percent))) if percent is not None else None
        case "volmute" if not args:
            return VolumeMuteToggle()
        case "media" if len(args) == 1 and args[0] in MEDIA_ACTIONS:
            return MediaCommand(args[0])
        case "seek" if len(args) == 1:
            value = args[0]
            if isinstance(value, bool) or not isinstance(value, int | float):
                return None
            return Seek(float(value)) if 0 <= value <= 86_400 else None
        case _:
            return None


def parse_events(raw: bytes | str) -> list[Event]:
    """Разбирает пакет событий, отбрасывая негодные элементы."""
    try:
        payload = json.loads(raw or "[]", parse_constant=_reject_constant)
    except (ValueError, TypeError):
        return []
    if not isinstance(payload, list):
        return []
    if len(payload) > MAX_EVENTS:
        return []

    events: list[Event] = []
    for item in payload:
        try:
            event = _parse_one(item)
        except (ValueError, TypeError, OverflowError):
            continue
        if event is not None:
            events.append(event)
    return events


@dataclass(frozen=True)
class AudioState:
    volume: int | None
    muted: bool


@dataclass(frozen=True)
class MediaState:
    playing: bool
    title: str
    artist: str
    art: str | None
    position: float
    duration: float
    can_seek: bool


@dataclass(frozen=True)
class Capabilities:
    audio: bool
    media: bool
    clipboard: bool


def state_message(
    audio: AudioState | None,
    media: MediaState | None,
    caps: Capabilities,
) -> dict:
    """Словарь состояния, готовый к отправке телефону."""
    return {
        "type": "state",
        "audio": None if audio is None else {"volume": audio.volume, "muted": audio.muted},
        "media": None if media is None else {
            "playing": media.playing,
            "title": media.title,
            "artist": media.artist,
            "art": media.art,
            "position": media.position,
            "duration": media.duration,
            "canSeek": media.can_seek,
        },
        "caps": {"audio": caps.audio, "media": caps.media, "clipboard": caps.clipboard},
    }
