"""Таблицы соответствия символов и имён клавиш кодам ядра Linux.

Модуль не открывает устройство ввода и не имеет побочных эффектов,
поэтому пригоден для импорта в тестах.
"""

from evdev import ecodes as E

CHARMAP: dict[str, tuple[int, bool]] = {}


def _add(char: str, key_name: str, shift: bool) -> None:
    CHARMAP[char] = (getattr(E, key_name), shift)


for _c in "abcdefghijklmnopqrstuvwxyz":
    _add(_c, "KEY_" + _c.upper(), False)
    _add(_c.upper(), "KEY_" + _c.upper(), True)

_SHIFTED_DIGITS = ")!@#$%^&*("
for _i, _c in enumerate("0123456789"):
    _add(_c, "KEY_" + _c, False)
    _add(_SHIFTED_DIGITS[_i], "KEY_" + _c, True)

for _ch, (_key, _shift) in {
    " ": ("KEY_SPACE", False),
    "\t": ("KEY_TAB", False),
    "\n": ("KEY_ENTER", False),
    "`": ("KEY_GRAVE", False), "~": ("KEY_GRAVE", True),
    "-": ("KEY_MINUS", False), "_": ("KEY_MINUS", True),
    "=": ("KEY_EQUAL", False), "+": ("KEY_EQUAL", True),
    "[": ("KEY_LEFTBRACE", False), "{": ("KEY_LEFTBRACE", True),
    "]": ("KEY_RIGHTBRACE", False), "}": ("KEY_RIGHTBRACE", True),
    "\\": ("KEY_BACKSLASH", False), "|": ("KEY_BACKSLASH", True),
    ";": ("KEY_SEMICOLON", False), ":": ("KEY_SEMICOLON", True),
    "'": ("KEY_APOSTROPHE", False), '"': ("KEY_APOSTROPHE", True),
    ",": ("KEY_COMMA", False), "<": ("KEY_COMMA", True),
    ".": ("KEY_DOT", False), ">": ("KEY_DOT", True),
    "/": ("KEY_SLASH", False), "?": ("KEY_SLASH", True),
}.items():
    _add(_ch, _key, _shift)

NAMED: dict[str, int] = {
    "backspace": E.KEY_BACKSPACE, "enter": E.KEY_ENTER, "tab": E.KEY_TAB,
    "escape": E.KEY_ESC, "esc": E.KEY_ESC, "space": E.KEY_SPACE,
    "delete": E.KEY_DELETE, "insert": E.KEY_INSERT,
    "up": E.KEY_UP, "down": E.KEY_DOWN, "left": E.KEY_LEFT, "right": E.KEY_RIGHT,
    "home": E.KEY_HOME, "end": E.KEY_END,
    "pageup": E.KEY_PAGEUP, "pagedown": E.KEY_PAGEDOWN,
    "ctrl": E.KEY_LEFTCTRL, "alt": E.KEY_LEFTALT, "shift": E.KEY_LEFTSHIFT,
    "super": E.KEY_LEFTMETA, "meta": E.KEY_LEFTMETA,
    "volup": E.KEY_VOLUMEUP, "voldown": E.KEY_VOLUMEDOWN, "mute": E.KEY_MUTE,
    "play": E.KEY_PLAYPAUSE, "next": E.KEY_NEXTSONG, "prev": E.KEY_PREVIOUSSONG,
    "brightup": E.KEY_BRIGHTNESSUP, "brightdown": E.KEY_BRIGHTNESSDOWN,
}
for _i in range(1, 13):
    NAMED[f"f{_i}"] = getattr(E, f"KEY_F{_i}")

MOUSE_BUTTONS: dict[str, int] = {
    "l": E.BTN_LEFT,
    "r": E.BTN_RIGHT,
    "m": E.BTN_MIDDLE,
}


def code_for(name: str) -> int | None:
    """Код клавиши по имени (`escape`) или по одиночному символу (`v`)."""
    if not name:
        return None
    lowered = name.lower()
    if lowered in NAMED:
        return NAMED[lowered]
    if name in CHARMAP:
        return CHARMAP[name][0]
    if lowered in CHARMAP:
        return CHARMAP[lowered][0]
    return None


def all_key_codes() -> list[int]:
    """Все коды, которые виртуальное устройство обязано уметь отправлять."""
    codes = {code for code, _ in CHARMAP.values()}
    codes |= set(NAMED.values())
    codes |= set(MOUSE_BUTTONS.values())
    return sorted(codes)
