# lanpad — агент. План реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Собрать агент lanpad — модульный сервер, который внедряет ввод в Linux, отдаёт состояние звука и медиа по WebSocket и раздаёт веб-приложение в локальной сети.

**Architecture:** Прототип на 605 строк разбирается на модули с одной обязанностью каждый. Между транспортом и операционной системой встаёт слой из четырёх интерфейсов — ввод, звук, медиа, буфер обмена, — за которыми стоят реализации для Linux. Протокол становится двусторонним: события летят от телефона пакетами, состояние возвращается по изменению.

**Tech Stack:** Python 3.11+, evdev (uinput), dbus-next (MPRIS), qrcode + pypng, pytest, ruff, GitHub Actions

**Spec:** [docs/superpowers/specs/2026-08-29-lanpad-design.md](../specs/2026-08-29-lanpad-design.md)

## Global Constraints

- Имя проекта, пакета, CLI и виртуального устройства — `lanpad`. Строка `claude-remote-touchpad` не должна попасть ни в один поставляемый файл — `src/`, `tests/`, метаданные пакета. Проектные документы в `docs/` вправе называть прототип по имени, объясняя переход
- Лицензия GPL-3.0, файл `LICENSE` в корне
- Python `>=3.11`
- Зависимости только устанавливаемые через pip: `evdev`, `dbus-next`, `qrcode`, `pypng`. Системные пакеты (`playerctl`, `PyGObject`) не используются
- Внешние команды, допустимые в рантайме: `wpctl`, `wl-copy`, `xclip`. Их отсутствие обязано деградировать в отключённую возможность, а не в падение
- Порт по умолчанию `8477`, переопределяется переменной `LANPAD_PORT`
- Токен сравнивается только через `secrets.compare_digest`
- Соединения принимаются только с адресов из приватных подсетей и с петлевого интерфейса
- Личные данные прототипа (записка в интерфейсе, файл `token`) не попадают в историю git ни одним коммитом
- Тесты не открывают `/dev/uinput`, не обращаются к D-Bus и не вызывают внешние команды. Всё это подменяется
- Каждая задача заканчивается зелёными `ruff check .` и `pytest`

**Важно про окружение.** Основной VS Code запущен во Flatpak-песочнице, где нет ни `evdev`, ни системных команд. Все команды из этого плана выполняются в обычном терминале хоста, а не в песочнице.

---

### Task 1: Каркас репозитория и CI

Прототип переезжает в `legacy/` и остаётся вне git — так личная записка и файл токена гарантированно не попадут в историю публичного репозитория.

**Files:**
- Create: `pyproject.toml`, `LICENSE`, `.gitignore`, `README.md`, `.github/workflows/ci.yml`
- Create: `src/lanpad/__init__.py`
- Create: `tests/test_package.py`
- Move: `server.py`, `make_icons.py`, `qr.png`, `token`, `web/` → `legacy/`

**Interfaces:**
- Consumes: ничего
- Produces: `lanpad.__version__: str`

- [ ] **Step 1: Убрать прототип из будущей истории git**

```bash
cd ~/Документы/Projects/Mouse
mkdir -p legacy
mv server.py make_icons.py qr.png token web legacy/
```

- [ ] **Step 2: Создать `.gitignore`**

```gitignore
legacy/
token
__pycache__/
*.py[cod]
.pytest_cache/
.ruff_cache/
.venv/
dist/
build/
*.egg-info/
node_modules/
.superpowers/
```

- [ ] **Step 3: Положить текст лицензии GPL-3.0**

```bash
curl -fsSL https://www.gnu.org/licenses/gpl-3.0.txt -o LICENSE
```

- [ ] **Step 4: Создать `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "lanpad"
version = "0.1.0"
description = "Телефон как тачпад, клавиатура и пульт для компьютера в локальной сети"
readme = "README.md"
requires-python = ">=3.11"
license = { text = "GPL-3.0-or-later" }
dependencies = [
    "evdev>=1.7",
    "dbus-next>=0.2.3",
    "qrcode>=7.4",
    "pypng>=0.20220715",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff>=0.6"]

[project.scripts]
lanpad = "lanpad.__main__:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
lanpad = ["web/**/*"]

[tool.ruff]
line-length = 100
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 5: Создать `src/lanpad/__init__.py`**

```python
"""lanpad — телефон как тачпад и пульт для компьютера в локальной сети."""

__version__ = "0.1.0"
```

- [ ] **Step 6: Написать падающий тест**

Создать `tests/test_package.py`:

```python
import lanpad


def test_package_exposes_version():
    assert lanpad.__version__ == "0.1.0"
```

- [ ] **Step 7: Установить окружение и убедиться, что тест падает**

Run: `python3 -m venv .venv && .venv/bin/pip install -e ".[dev]" && .venv/bin/pytest -q`
Expected: до установки — `ModuleNotFoundError: No module named 'lanpad'`; после установки тест проходит

- [ ] **Step 8: Написать заглушку README**

```markdown
# lanpad

Телефон становится тачпадом, клавиатурой и пультом управления медиа для
компьютера в той же локальной сети. Без облака, без учётных записей, без рекламы.

В разработке. Полное описание появится к первому релизу.

## Лицензия

GPL-3.0-or-later
```

- [ ] **Step 9: Создать `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: ruff check .
      - run: pytest -q
```

- [ ] **Step 10: Проверить линтер и тесты**

Run: `.venv/bin/ruff check . && .venv/bin/pytest -q`
Expected: линтер без замечаний, один тест проходит

- [ ] **Step 11: Первый коммит**

```bash
git init -b main
git add pyproject.toml LICENSE .gitignore README.md .github src tests
git status --short
```

Убедиться, что в выводе `git status --short` **нет** `legacy/`, `token`, `web/`. Затем:

```bash
git commit -m "chore: каркас пакета lanpad, лицензия GPL-3.0, CI"
```

- [ ] **Step 12: Перенести спеку и план в репозиторий**

```bash
git add docs/
git commit -m "docs: спецификация и план реализации агента"
```

---

### Task 2: Раскладка клавиш

Таблицы символов и именованных клавиш переезжают из прототипа в отдельный модуль без побочных эффектов. Модуль импортирует `ecodes`, но не открывает устройство — поэтому тестируется где угодно.

**Files:**
- Create: `src/lanpad/keymap.py`
- Create: `tests/test_keymap.py`
- Reference: `legacy/server.py:44-97`

**Interfaces:**
- Consumes: ничего
- Produces:
  - `CHARMAP: dict[str, tuple[int, bool]]` — символ → (код клавиши, нужен ли Shift)
  - `NAMED: dict[str, int]` — имя клавиши в нижнем регистре → код
  - `code_for(name: str) -> int | None` — разбирает и именованные клавиши, и одиночные символы
  - `all_key_codes() -> list[int]` — полный список кодов для объявления виртуального устройства

- [ ] **Step 1: Написать падающие тесты**

Создать `tests/test_keymap.py`:

```python
from evdev import ecodes as E

from lanpad import keymap


def test_lowercase_letter_needs_no_shift():
    assert keymap.CHARMAP["a"] == (E.KEY_A, False)


def test_uppercase_letter_needs_shift():
    assert keymap.CHARMAP["A"] == (E.KEY_A, True)


def test_shifted_digit_maps_to_digit_key():
    assert keymap.CHARMAP["!"] == (E.KEY_1, True)


def test_named_key_lookup_is_case_insensitive():
    assert keymap.code_for("Escape") == E.KEY_ESC
    assert keymap.code_for("escape") == E.KEY_ESC


def test_code_for_accepts_single_character():
    assert keymap.code_for("v") == E.KEY_V


def test_code_for_returns_none_for_unknown():
    assert keymap.code_for("несуществующая") is None


def test_media_keys_present():
    for name in ("play", "next", "prev", "volup", "voldown", "mute"):
        assert keymap.code_for(name) is not None


def test_all_key_codes_includes_mouse_buttons():
    codes = keymap.all_key_codes()
    assert E.BTN_LEFT in codes
    assert E.BTN_RIGHT in codes
    assert E.BTN_MIDDLE in codes
    assert codes == sorted(set(codes))
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `.venv/bin/pytest tests/test_keymap.py -q`
Expected: FAIL с `ModuleNotFoundError: No module named 'lanpad.keymap'`

- [ ] **Step 3: Написать модуль**

Создать `src/lanpad/keymap.py`:

```python
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
```

- [ ] **Step 4: Убедиться, что тесты проходят**

Run: `.venv/bin/pytest tests/test_keymap.py -q && .venv/bin/ruff check .`
Expected: 8 тестов проходят, линтер молчит

- [ ] **Step 5: Коммит**

```bash
git add src/lanpad/keymap.py tests/test_keymap.py
git commit -m "feat: раскладка клавиш отдельным модулем без побочных эффектов"
```

---

### Task 3: Протокол

Разбор входящих событий и сборка состояния для отправки. В прототипе разбор размазан по обработчику и молча глотает ошибки — здесь он становится явным и проверяемым.

**Files:**
- Create: `src/lanpad/protocol.py`
- Create: `tests/test_protocol.py`
- Reference: `legacy/server.py:268-317`

**Interfaces:**
- Consumes: ничего
- Produces:
  - `parse_events(raw: bytes | str) -> list[Event]` — разбирает пакет, пропуская негодные элементы
  - Классы событий: `Move(dx: int, dy: int)`, `Wheel(amount: int)`, `Button(name: str, pressed: bool)`, `Click(name: str)`, `Tap(key: str)`, `KeyHold(key: str, pressed: bool)`, `Combo(keys: list[str])`, `TypeText(text: str)`, `Paste(text: str, terminal: bool)`, `VolumeStep(delta: int)`, `VolumeSet(percent: int)`, `VolumeMuteToggle()`, `MediaCommand(action: str)`, `Seek(position: float)`
  - `AudioState(volume: int | None, muted: bool)`
  - `MediaState(playing: bool, title: str, artist: str, art: str | None, position: float, duration: float, can_seek: bool)`
  - `Capabilities(audio: bool, media: bool, clipboard: bool)`
  - `state_message(audio, media, caps) -> dict` — готовый к сериализации словарь

- [ ] **Step 1: Написать падающие тесты**

Создать `tests/test_protocol.py`:

```python
import json

import pytest

from lanpad import protocol as p


def test_parses_move():
    events = p.parse_events('[["m", 12, -4]]')
    assert events == [p.Move(dx=12, dy=-4)]


def test_parses_batch_in_order():
    events = p.parse_events('[["m",1,2],["click","l"],["w",-3]]')
    assert events == [p.Move(1, 2), p.Click("l"), p.Wheel(-3)]


def test_skips_unknown_event_type():
    assert p.parse_events('[["m",1,1],["выдумка",1],["w",1]]') == [p.Move(1, 1), p.Wheel(1)]


def test_skips_malformed_event_without_failing_batch():
    assert p.parse_events('[["m",1],["w",2]]') == [p.Wheel(2)]


def test_rejects_non_list_payload():
    assert p.parse_events('{"m": 1}') == []


def test_rejects_invalid_json():
    assert p.parse_events("не json") == []


def test_accepts_bytes():
    assert p.parse_events(b'[["w", 5]]') == [p.Wheel(5)]


def test_button_down_and_up():
    assert p.parse_events('[["bd","l"],["bu","l"]]') == [
        p.Button("l", True),
        p.Button("l", False),
    ]


def test_rejects_unknown_button_name():
    assert p.parse_events('[["bd","x"]]') == []


def test_volume_set_is_clamped():
    assert p.parse_events('[["volset", 150]]') == [p.VolumeSet(100)]
    assert p.parse_events('[["volset", -20]]') == [p.VolumeSet(0)]


def test_move_rejects_absurd_values():
    """Защита от подсунутого пакета, уводящего курсор за пределы экрана."""
    assert p.parse_events('[["m", 999999, 0]]') == []


def test_type_text_length_is_limited():
    long_text = "a" * 10_001
    assert p.parse_events(json.dumps([["type", long_text]])) == []


def test_media_commands():
    assert p.parse_events('[["media","play"],["media","next"],["media","prev"]]') == [
        p.MediaCommand("play"),
        p.MediaCommand("next"),
        p.MediaCommand("prev"),
    ]


def test_rejects_unknown_media_command():
    assert p.parse_events('[["media","поехали"]]') == []


def test_seek_accepts_float_seconds():
    assert p.parse_events('[["seek", 134.5]]') == [p.Seek(134.5)]


def test_seek_rejects_negative():
    assert p.parse_events('[["seek", -1]]') == []


def test_combo_keys_are_strings():
    assert p.parse_events('[["combo",["ctrl","c"]]]') == [p.Combo(["ctrl", "c"])]


def test_combo_rejects_non_string_members():
    assert p.parse_events('[["combo",["ctrl", 5]]]') == []


@pytest.mark.parametrize("raw,expected", [
    ('[["paste","привет"]]', p.Paste("привет", terminal=False)),
    ('[["tpaste","ls -la"]]', p.Paste("ls -la", terminal=True)),
])
def test_paste_variants(raw, expected):
    assert p.parse_events(raw) == [expected]


def test_state_message_shape():
    msg = p.state_message(
        audio=p.AudioState(volume=62, muted=False),
        media=p.MediaState(
            playing=True, title="Bohemian Rhapsody", artist="Queen",
            art="/art?id=abc", position=134.2, duration=355.0, can_seek=True,
        ),
        caps=p.Capabilities(audio=True, media=True, clipboard=True),
    )
    assert msg["type"] == "state"
    assert msg["audio"] == {"volume": 62, "muted": False}
    assert msg["media"]["title"] == "Bohemian Rhapsody"
    assert msg["media"]["canSeek"] is True
    assert msg["caps"] == {"audio": True, "media": True, "clipboard": True}


def test_state_message_omits_media_when_absent():
    msg = p.state_message(
        audio=p.AudioState(volume=10, muted=True),
        media=None,
        caps=p.Capabilities(audio=True, media=False, clipboard=False),
    )
    assert msg["media"] is None
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `.venv/bin/pytest tests/test_protocol.py -q`
Expected: FAIL с `ModuleNotFoundError: No module named 'lanpad.protocol'`

- [ ] **Step 3: Написать модуль**

Создать `src/lanpad/protocol.py`:

```python
"""Разбор входящих событий и сборка состояния для отправки телефону.

Разбор намеренно снисходителен к отдельным элементам пакета: негодное
событие отбрасывается, остальные исполняются. Но снисходительность не
означает доверчивость — числовые значения ограничены, чтобы подложенный
пакет не увёл курсор в бесконечность и не заставил агент печатать роман.
"""

import json
from dataclasses import dataclass

from lanpad.keymap import MOUSE_BUTTONS

MAX_MOVE = 4000
MAX_WHEEL = 200
MAX_TEXT = 10_000
MAX_COMBO_KEYS = 6
MEDIA_ACTIONS = frozenset({"play", "next", "prev"})


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


def _parse_one(item: object) -> Event | None:  # noqa: PLR0911, PLR0912
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
        payload = json.loads(raw or "[]")
    except (ValueError, TypeError):
        return []
    if not isinstance(payload, list):
        return []
    parsed = (_parse_one(item) for item in payload)
    return [event for event in parsed if event is not None]


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
```

- [ ] **Step 4: Убедиться, что тесты проходят**

Run: `.venv/bin/pytest tests/test_protocol.py -q && .venv/bin/ruff check .`
Expected: все тесты проходят, линтер молчит

- [ ] **Step 5: Коммит**

```bash
git add src/lanpad/protocol.py tests/test_protocol.py
git commit -m "feat: явный разбор протокола с ограничением значений"
```

---

### Task 4: Интерфейсы платформы и подставные реализации

Четыре интерфейса и их записывающие двойники. Двойники живут в пакете, а не в тестах, потому что понадобятся и в тестах сессии, и в тестах HTTP-слоя.

**Files:**
- Create: `src/lanpad/platform/__init__.py`, `src/lanpad/platform/base.py`, `src/lanpad/platform/fake.py`
- Create: `tests/test_platform_fake.py`

**Interfaces:**
- Consumes: `protocol.AudioState`, `protocol.MediaState`
- Produces:
  - `InputBackend` с методами `move(dx, dy)`, `wheel(amount)`, `button(name, pressed)`, `click(name)`, `tap(key)`, `key_hold(key, pressed)`, `combo(keys)`, `type_text(text)`, `can_type(text) -> bool`, `close()`
  - `AudioBackend` с `state() -> AudioState`, `step(delta)`, `set_percent(percent)`, `toggle_mute()`
  - `MediaBackend` с `state() -> MediaState | None`, `command(action)`, `seek(position)`, `subscribe(callback)`, `art_path_for(art_id) -> str | None`, `close()`
  - `ClipboardBackend` с `copy(text) -> bool`
  - `Backends(input, audio, media, clipboard)` и `Backends.capabilities() -> Capabilities`
  - `FakeInput`, `FakeAudio`, `FakeMedia`, `FakeClipboard` — записывают вызовы в список `calls`

- [ ] **Step 1: Написать падающие тесты**

Создать `tests/test_platform_fake.py`:

```python
from lanpad import protocol as p
from lanpad.platform.base import Backends
from lanpad.platform.fake import FakeAudio, FakeClipboard, FakeInput, FakeMedia


def test_fake_input_records_calls():
    fake = FakeInput()
    fake.move(3, 4)
    fake.click("l")
    assert fake.calls == [("move", 3, 4), ("click", "l")]


def test_ascii_text_can_be_typed_directly():
    assert FakeInput().can_type("hello") is True


def test_cyrillic_text_cannot_be_typed_directly():
    assert FakeInput().can_type("привет") is False


def test_fake_audio_tracks_volume():
    fake = FakeAudio()
    fake.set_percent(40)
    assert fake.state() == p.AudioState(volume=40, muted=False)
    fake.toggle_mute()
    assert fake.state().muted is True


def test_fake_audio_step_clamps():
    fake = FakeAudio()
    fake.set_percent(95)
    fake.step(20)
    assert fake.state().volume == 100


def test_fake_media_notifies_subscriber_on_command():
    fake = FakeMedia()
    seen = []
    fake.subscribe(seen.append)
    fake.command("play")
    assert len(seen) == 1
    assert isinstance(seen[0], p.MediaState)


def test_capabilities_reflect_present_backends():
    full = Backends(FakeInput(), FakeAudio(), FakeMedia(), FakeClipboard())
    assert full.capabilities() == p.Capabilities(audio=True, media=True, clipboard=True)


def test_capabilities_report_missing_backends():
    bare = Backends(FakeInput(), None, None, None)
    assert bare.capabilities() == p.Capabilities(audio=False, media=False, clipboard=False)
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `.venv/bin/pytest tests/test_platform_fake.py -q`
Expected: FAIL с `ModuleNotFoundError: No module named 'lanpad.platform'`

- [ ] **Step 3: Написать `src/lanpad/platform/__init__.py`**

```python
"""Слой платформы: интерфейсы ввода, звука, медиа и буфера обмена."""
```

- [ ] **Step 4: Написать `src/lanpad/platform/base.py`**

```python
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

    def close(self) -> None:
        """Освободить устройство. По умолчанию делать нечего."""


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

    def close(self) -> None:
        """Отписаться от источника событий."""


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
```

- [ ] **Step 5: Написать `src/lanpad/platform/fake.py`**

```python
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
```

- [ ] **Step 6: Убедиться, что тесты проходят**

Run: `.venv/bin/pytest tests/test_platform_fake.py -q && .venv/bin/ruff check .`
Expected: 8 тестов проходят

- [ ] **Step 7: Коммит**

```bash
git add src/lanpad/platform tests/test_platform_fake.py
git commit -m "feat: интерфейсы платформы и записывающие двойники"
```

---

### Task 5: Фрейминг WebSocket

Кодирование и декодирование кадров переезжает в отдельный модуль и впервые получает тесты. В прототипе эта логика вплетена в обработчик и непроверяема.

**Files:**
- Create: `src/lanpad/ws.py`
- Create: `tests/test_ws.py`
- Reference: `legacy/server.py:355-413`

**Interfaces:**
- Consumes: ничего
- Produces:
  - `accept_key(client_key: str) -> str` — значение заголовка `Sec-WebSocket-Accept`
  - `encode_frame(data: bytes | str, opcode: int = OP_TEXT) -> bytes`
  - `read_frame(recv: Callable[[int], bytes | None]) -> Frame | None` — `None` означает закрытие
  - `Frame(opcode: int, payload: bytes)`
  - Константы `OP_TEXT`, `OP_BINARY`, `OP_CLOSE`, `OP_PING`, `OP_PONG`

- [ ] **Step 1: Написать падающие тесты**

Создать `tests/test_ws.py`:

```python
import pytest

from lanpad import ws


def reader_for(data: bytes):
    """Отдаёт байты порциями, как это делал бы сокет."""
    buffer = bytearray(data)

    def recv(n: int) -> bytes | None:
        if not buffer:
            return None
        chunk = bytes(buffer[:n])
        del buffer[:n]
        return chunk

    return recv


def masked_frame(payload: bytes, opcode: int = ws.OP_TEXT) -> bytes:
    mask = b"\x01\x02\x03\x04"
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    header = bytearray([0x80 | opcode])
    length = len(payload)
    if length < 126:
        header.append(0x80 | length)
    elif length < 65536:
        header.append(0x80 | 126)
        header += length.to_bytes(2, "big")
    else:
        header.append(0x80 | 127)
        header += length.to_bytes(8, "big")
    return bytes(header) + mask + masked


def test_accept_key_matches_rfc_example():
    assert ws.accept_key("dGhlIHNhbXBsZSBub25jZQ==") == "s3pPLMBiTxaQ9kYGzzhZRbK+xOo="


def test_encode_short_text_frame():
    frame = ws.encode_frame("hi")
    assert frame == b"\x81\x02hi"


def test_encode_medium_frame_uses_extended_length():
    frame = ws.encode_frame(b"x" * 200)
    assert frame[0] == 0x81
    assert frame[1] == 126
    assert int.from_bytes(frame[2:4], "big") == 200


def test_encode_large_frame_uses_long_length():
    frame = ws.encode_frame(b"x" * 70_000)
    assert frame[1] == 127
    assert int.from_bytes(frame[2:10], "big") == 70_000


def test_reads_masked_text_frame():
    frame = ws.read_frame(reader_for(masked_frame(b'[["w",1]]')))
    assert frame.opcode == ws.OP_TEXT
    assert frame.payload == b'[["w",1]]'


def test_reads_frame_with_extended_length():
    payload = b"y" * 300
    frame = ws.read_frame(reader_for(masked_frame(payload)))
    assert frame.payload == payload


def test_close_frame_returns_none():
    assert ws.read_frame(reader_for(masked_frame(b"", ws.OP_CLOSE))) is None


def test_exhausted_socket_returns_none():
    assert ws.read_frame(reader_for(b"")) is None


def test_ping_frame_is_reported_so_caller_can_pong():
    frame = ws.read_frame(reader_for(masked_frame(b"ping", ws.OP_PING)))
    assert frame.opcode == ws.OP_PING
    assert frame.payload == b"ping"


def test_oversized_frame_is_refused():
    """Кадр, объявляющий гигабайт, не должен приводить к попытке его прочитать."""
    header = bytes([0x81, 0x80 | 127]) + (2**40).to_bytes(8, "big") + b"\x00\x00\x00\x00"
    assert ws.read_frame(reader_for(header)) is None


@pytest.mark.parametrize("text", ["", "привет", "a" * 5000])
def test_encode_accepts_str_and_bytes(text):
    assert ws.encode_frame(text) == ws.encode_frame(text.encode())
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `.venv/bin/pytest tests/test_ws.py -q`
Expected: FAIL с `ModuleNotFoundError: No module named 'lanpad.ws'`

- [ ] **Step 3: Написать модуль**

Создать `src/lanpad/ws.py`:

```python
"""Минимальный фрейминг WebSocket поверх обычного сокета.

Полноценная библиотека здесь избыточна: обмен идёт короткими текстовыми
кадрами в одном направлении и служебными в другом.
"""

import base64
import hashlib
import struct
from collections.abc import Callable
from dataclasses import dataclass

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

OP_TEXT = 0x1
OP_BINARY = 0x2
OP_CLOSE = 0x8
OP_PING = 0x9
OP_PONG = 0xA

MAX_PAYLOAD = 1 << 20  # 1 МиБ — вставка текста заведомо короче


@dataclass(frozen=True)
class Frame:
    opcode: int
    payload: bytes


def accept_key(client_key: str) -> str:
    """Ответ на `Sec-WebSocket-Key` по правилам рукопожатия."""
    digest = hashlib.sha1((client_key + GUID).encode()).digest()  # noqa: S324
    return base64.b64encode(digest).decode()


def encode_frame(data: bytes | str, opcode: int = OP_TEXT) -> bytes:
    """Собрать кадр сервера — без маски, как требует протокол."""
    if isinstance(data, str):
        data = data.encode()
    header = bytearray([0x80 | opcode])
    length = len(data)
    if length < 126:
        header.append(length)
    elif length < 65536:
        header.append(126)
        header += struct.pack(">H", length)
    else:
        header.append(127)
        header += struct.pack(">Q", length)
    return bytes(header) + data


def _read_exactly(recv: Callable[[int], bytes | None], count: int) -> bytes | None:
    buffer = b""
    while len(buffer) < count:
        chunk = recv(count - len(buffer))
        if not chunk:
            return None
        buffer += chunk
    return buffer


def read_frame(recv: Callable[[int], bytes | None]) -> Frame | None:
    """Прочитать один кадр. `None` означает закрытие или негодные данные."""
    header = _read_exactly(recv, 2)
    if header is None:
        return None

    opcode = header[0] & 0x0F
    masked = bool(header[1] & 0x80)
    length = header[1] & 0x7F

    if length == 126:
        extended = _read_exactly(recv, 2)
        if extended is None:
            return None
        length = struct.unpack(">H", extended)[0]
    elif length == 127:
        extended = _read_exactly(recv, 8)
        if extended is None:
            return None
        length = struct.unpack(">Q", extended)[0]

    if length > MAX_PAYLOAD:
        return None

    mask = _read_exactly(recv, 4) if masked else b"\x00\x00\x00\x00"
    if mask is None:
        return None

    payload = _read_exactly(recv, length) if length else b""
    if payload is None:
        return None

    if masked:
        payload = bytes(byte ^ mask[i % 4] for i, byte in enumerate(payload))

    if opcode == OP_CLOSE:
        return None
    return Frame(opcode=opcode, payload=payload)
```

- [ ] **Step 4: Убедиться, что тесты проходят**

Run: `.venv/bin/pytest tests/test_ws.py -q && .venv/bin/ruff check .`
Expected: все тесты проходят

- [ ] **Step 5: Коммит**

```bash
git add src/lanpad/ws.py tests/test_ws.py
git commit -m "feat: фрейминг WebSocket отдельным модулем с тестами"
```

---

### Task 6: Ввод через uinput

Реализация `InputBackend` для Linux. Накопитель дробной прокрутки выносится в чистую функцию, чтобы его можно было проверить без устройства.

**Files:**
- Create: `src/lanpad/platform/linux/__init__.py`, `src/lanpad/platform/linux/input_uinput.py`
- Create: `tests/test_input_uinput.py`
- Reference: `legacy/server.py:98-208`

**Interfaces:**
- Consumes: `keymap.all_key_codes`, `keymap.code_for`, `keymap.CHARMAP`, `keymap.MOUSE_BUTTONS`, `platform.base.InputBackend`
- Produces:
  - `WheelAccumulator` с методом `add(amount: float) -> int`
  - `UinputInput(device_name: str = "lanpad")` — реализация `InputBackend`
  - `UinputUnavailable(RuntimeError)` — поднимается, когда устройство недоступно

- [ ] **Step 1: Написать падающие тесты**

Создать `tests/test_input_uinput.py`:

```python
from lanpad.platform.linux.input_uinput import WheelAccumulator


def test_fractional_scroll_accumulates_until_whole_step():
    acc = WheelAccumulator()
    assert acc.add(0.4) == 0
    assert acc.add(0.4) == 0
    assert acc.add(0.4) == 1


def test_remainder_is_kept_between_calls():
    acc = WheelAccumulator()
    acc.add(1.5)
    assert acc.add(0.6) == 1


def test_negative_direction_works_symmetrically():
    acc = WheelAccumulator()
    assert acc.add(-0.5) == 0
    assert acc.add(-0.6) == -1


def test_whole_values_pass_through_immediately():
    acc = WheelAccumulator()
    assert acc.add(3) == 3


def test_accumulator_does_not_drift_over_many_small_steps():
    acc = WheelAccumulator()
    total = sum(acc.add(0.1) for _ in range(100))
    assert total == 10
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `.venv/bin/pytest tests/test_input_uinput.py -q`
Expected: FAIL с `ModuleNotFoundError`

- [ ] **Step 3: Написать `src/lanpad/platform/linux/__init__.py`**

```python
"""Реализации слоя платформы для Linux."""
```

- [ ] **Step 4: Написать `src/lanpad/platform/linux/input_uinput.py`**

```python
"""Внедрение ввода через /dev/uinput.

Прав суперпользователя не требуется: logind выдаёт владельцу активной
сессии права на запись в устройство.
"""

import threading
import time

from evdev import UInput
from evdev import ecodes as E

from lanpad.keymap import CHARMAP, MOUSE_BUTTONS, all_key_codes, code_for
from lanpad.platform.base import InputBackend

CLICK_HOLD_SECONDS = 0.012
TYPE_DELAY_SECONDS = 0.004


class UinputUnavailable(RuntimeError):
    """Устройство ввода недоступно — нет прав или не загружен модуль uinput."""


class WheelAccumulator:
    """Копит дробные шаги прокрутки до целого щелчка колеса.

    Телефон присылает доли шага; ядро принимает только целые. Без
    накопления медленная прокрутка не приводила бы ни к чему.
    """

    def __init__(self) -> None:
        self._remainder = 0.0

    def add(self, amount: float) -> int:
        self._remainder += amount
        whole = int(self._remainder)
        self._remainder -= whole
        return whole


class UinputInput(InputBackend):
    def __init__(self, device_name: str = "lanpad") -> None:
        capabilities = {
            E.EV_KEY: all_key_codes(),
            E.EV_REL: [E.REL_X, E.REL_Y, E.REL_WHEEL],
        }
        try:
            self._device = UInput(capabilities, name=device_name, version=1)
        except (PermissionError, FileNotFoundError, OSError) as exc:
            raise UinputUnavailable(
                "Нет доступа к /dev/uinput. Проверьте, что модуль uinput загружен "
                "и что вы работаете в активной графической сессии."
            ) from exc
        self._lock = threading.Lock()
        self._wheel = WheelAccumulator()
        time.sleep(0.5)  # дать udev зарегистрировать устройство

    def _emit_key(self, code: int, value: int) -> None:
        self._device.write(E.EV_KEY, code, value)

    def move(self, dx: int, dy: int) -> None:
        if not (dx or dy):
            return
        with self._lock:
            if dx:
                self._device.write(E.EV_REL, E.REL_X, dx)
            if dy:
                self._device.write(E.EV_REL, E.REL_Y, dy)
            self._device.syn()

    def wheel(self, amount: int) -> None:
        with self._lock:
            steps = self._wheel.add(amount)
            if steps:
                self._device.write(E.EV_REL, E.REL_WHEEL, steps)
                self._device.syn()

    def button(self, name: str, pressed: bool) -> None:
        code = MOUSE_BUTTONS.get(name)
        if code is None:
            return
        with self._lock:
            self._emit_key(code, 1 if pressed else 0)
            self._device.syn()

    def click(self, name: str) -> None:
        self.button(name, True)
        time.sleep(CLICK_HOLD_SECONDS)
        self.button(name, False)

    def tap(self, key: str) -> None:
        code = code_for(key)
        if code is None:
            return
        with self._lock:
            self._emit_key(code, 1)
            self._device.syn()
            self._emit_key(code, 0)
            self._device.syn()

    def key_hold(self, key: str, pressed: bool) -> None:
        code = code_for(key)
        if code is None:
            return
        with self._lock:
            self._emit_key(code, 1 if pressed else 0)
            self._device.syn()

    def combo(self, keys: list[str]) -> None:
        codes = [c for c in (code_for(k) for k in keys) if c is not None]
        if not codes:
            return
        modifiers, final = codes[:-1], codes[-1]
        with self._lock:
            for code in modifiers:
                self._emit_key(code, 1)
                self._device.syn()
            self._emit_key(final, 1)
            self._device.syn()
            self._emit_key(final, 0)
            self._device.syn()
            for code in reversed(modifiers):
                self._emit_key(code, 0)
                self._device.syn()

    def type_text(self, text: str) -> None:
        """Набрать текст посимвольно.

        Работает только для символов из раскладки. Кириллица и прочее
        отправляются через буфер обмена — этим занимается сессия.
        """
        if not text or any(char not in CHARMAP for char in text):
            return
        with self._lock:
            for char in text:
                code, needs_shift = CHARMAP[char]
                if needs_shift:
                    self._emit_key(E.KEY_LEFTSHIFT, 1)
                self._emit_key(code, 1)
                self._device.syn()
                self._emit_key(code, 0)
                if needs_shift:
                    self._emit_key(E.KEY_LEFTSHIFT, 0)
                self._device.syn()
                time.sleep(TYPE_DELAY_SECONDS)

    def can_type(self, text: str) -> bool:
        """Можно ли набрать текст напрямую, без буфера обмена."""
        return bool(text) and all(char in CHARMAP for char in text)

    def close(self) -> None:
        self._device.close()
```

- [ ] **Step 5: Убедиться, что тесты проходят**

Run: `.venv/bin/pytest tests/test_input_uinput.py -q && .venv/bin/ruff check .`
Expected: 5 тестов проходят

- [ ] **Step 6: Проверить на живом устройстве**

Run:
```bash
.venv/bin/python -c "
from lanpad.platform.linux.input_uinput import UinputInput
d = UinputInput()
d.move(80, 0)
d.close()
print('курсор сдвинулся вправо')
"
```
Expected: курсор смещается вправо примерно на 80 точек. Если поднялось `UinputUnavailable` — выполнить `sudo modprobe uinput` и повторить.

- [ ] **Step 7: Коммит**

```bash
git add src/lanpad/platform/linux tests/test_input_uinput.py
git commit -m "feat: ввод через uinput с проверяемым накопителем прокрутки"
```

---

### Task 7: Звук через wpctl

Разбор вывода `wpctl` выносится в чистую функцию — её можно проверить без PipeWire. Отсутствие `wpctl` означает отключённую возможность, а не падение.

**Files:**
- Create: `src/lanpad/platform/linux/audio_wpctl.py`
- Create: `tests/test_audio_wpctl.py`
- Reference: `legacy/server.py:234-265`

**Interfaces:**
- Consumes: `platform.base.AudioBackend`, `protocol.AudioState`
- Produces:
  - `parse_volume(output: str) -> AudioState`
  - `WpctlAudio()` — реализация `AudioBackend`
  - `WpctlAudio.is_available() -> bool` — классовый метод, проверяет наличие команды

- [ ] **Step 1: Написать падающие тесты**

Создать `tests/test_audio_wpctl.py`:

```python
from lanpad.platform.linux.audio_wpctl import parse_volume


def test_parses_plain_volume():
    assert parse_volume("Volume: 0.62\n").volume == 62


def test_parses_muted_volume():
    state = parse_volume("Volume: 0.40 [MUTED]\n")
    assert state.volume == 40
    assert state.muted is True


def test_unmuted_by_default():
    assert parse_volume("Volume: 1.00\n").muted is False


def test_rounds_to_nearest_percent():
    assert parse_volume("Volume: 0.335\n").volume == 34


def test_volume_above_one_is_reported_as_is():
    """wpctl умеет выдавать усиление выше 100% — не врём про это."""
    assert parse_volume("Volume: 1.40\n").volume == 140


def test_unparseable_output_gives_none_volume():
    state = parse_volume("устройство не найдено")
    assert state.volume is None
    assert state.muted is False


def test_empty_output_gives_none_volume():
    assert parse_volume("").volume is None
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `.venv/bin/pytest tests/test_audio_wpctl.py -q`
Expected: FAIL с `ModuleNotFoundError`

- [ ] **Step 3: Написать модуль**

Создать `src/lanpad/platform/linux/audio_wpctl.py`:

```python
"""Громкость через PipeWire, командой wpctl."""

import re
import shutil
import subprocess

from lanpad.platform.base import AudioBackend
from lanpad.protocol import AudioState

SINK = "@DEFAULT_AUDIO_SINK@"
TIMEOUT = 2
_VOLUME_RE = re.compile(r"Volume:\s*([0-9.]+)")


def parse_volume(output: str) -> AudioState:
    """Разобрать вывод `wpctl get-volume`."""
    match = _VOLUME_RE.search(output)
    if match is None:
        return AudioState(volume=None, muted=False)
    return AudioState(
        volume=round(float(match.group(1)) * 100),
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
```

- [ ] **Step 4: Убедиться, что тесты проходят**

Run: `.venv/bin/pytest tests/test_audio_wpctl.py -q && .venv/bin/ruff check .`
Expected: 7 тестов проходят

- [ ] **Step 5: Проверить на живой системе**

Run:
```bash
.venv/bin/python -c "
from lanpad.platform.linux.audio_wpctl import WpctlAudio
a = WpctlAudio()
print('доступен:', WpctlAudio.is_available())
print('состояние:', a.state())
"
```
Expected: `доступен: True` и текущая громкость числом

- [ ] **Step 6: Коммит**

```bash
git add src/lanpad/platform/linux/audio_wpctl.py tests/test_audio_wpctl.py
git commit -m "feat: громкость через wpctl с разбором вывода отдельной функцией"
```

---

### Task 8: Медиа через MPRIS

Самая объёмная реализация. D-Bus живёт в собственном потоке с собственным циклом asyncio и толкает изменения через callback. Преобразование метаданных — чистая функция, проверяемая без D-Bus.

**Files:**
- Create: `src/lanpad/platform/linux/media_mpris.py`
- Create: `tests/test_media_mpris.py`

**Interfaces:**
- Consumes: `platform.base.MediaBackend`, `protocol.MediaState`
- Produces:
  - `metadata_to_state(metadata: dict, playback_status: str, position_us: int, can_seek: bool) -> MediaState`
  - `art_id_for(url: str) -> str` — стабильный идентификатор локальной обложки
  - `MprisMedia()` — реализация `MediaBackend`

- [ ] **Step 1: Написать падающие тесты**

Создать `tests/test_media_mpris.py`:

```python
from lanpad.platform.linux.media_mpris import art_id_for, metadata_to_state


def meta(**overrides):
    base = {
        "xesam:title": "Bohemian Rhapsody",
        "xesam:artist": ["Queen"],
        "mpris:length": 355_000_000,
        "mpris:artUrl": "https://cdn.example/cover.jpg",
    }
    base.update(overrides)
    return base


def test_maps_title_and_artist():
    state = metadata_to_state(meta(), "Playing", 134_200_000, True)
    assert state.title == "Bohemian Rhapsody"
    assert state.artist == "Queen"


def test_joins_multiple_artists():
    state = metadata_to_state(meta(**{"xesam:artist": ["Queen", "David Bowie"]}), "Playing", 0, True)
    assert state.artist == "Queen, David Bowie"


def test_converts_microseconds_to_seconds():
    state = metadata_to_state(meta(), "Playing", 134_200_000, True)
    assert state.position == 134.2
    assert state.duration == 355.0


def test_playing_status():
    assert metadata_to_state(meta(), "Playing", 0, True).playing is True
    assert metadata_to_state(meta(), "Paused", 0, True).playing is False
    assert metadata_to_state(meta(), "Stopped", 0, True).playing is False


def test_external_art_url_passes_through():
    state = metadata_to_state(meta(), "Playing", 0, True)
    assert state.art == "https://cdn.example/cover.jpg"


def test_local_art_becomes_proxy_url():
    state = metadata_to_state(meta(**{"mpris:artUrl": "file:///home/u/cover.png"}), "Playing", 0, True)
    assert state.art.startswith("/art?id=")


def test_local_art_id_is_stable():
    assert art_id_for("file:///home/u/cover.png") == art_id_for("file:///home/u/cover.png")


def test_different_local_art_gives_different_id():
    assert art_id_for("file:///a.png") != art_id_for("file:///b.png")


def test_missing_art_is_none():
    data = meta()
    del data["mpris:artUrl"]
    assert metadata_to_state(data, "Playing", 0, True).art is None


def test_missing_title_falls_back_to_empty_string():
    data = meta()
    del data["xesam:title"]
    assert metadata_to_state(data, "Playing", 0, True).title == ""


def test_artist_as_plain_string_is_accepted():
    """Некоторые плееры нарушают спецификацию и шлют строку вместо списка."""
    state = metadata_to_state(meta(**{"xesam:artist": "Queen"}), "Playing", 0, True)
    assert state.artist == "Queen"


def test_can_seek_flag_is_carried_through():
    assert metadata_to_state(meta(), "Playing", 0, False).can_seek is False


def test_missing_length_gives_zero_duration():
    data = meta()
    del data["mpris:length"]
    assert metadata_to_state(data, "Playing", 0, True).duration == 0.0
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `.venv/bin/pytest tests/test_media_mpris.py -q`
Expected: FAIL с `ModuleNotFoundError`

- [ ] **Step 3: Написать модуль**

Создать `src/lanpad/platform/linux/media_mpris.py`:

```python
"""Состояние воспроизведения через MPRIS поверх D-Bus.

D-Bus работает асинхронно, а сервер — потоками. Поэтому клиент живёт в
отдельном потоке с собственным циклом событий и толкает изменения наружу
через callback. Опроса нет: подписка на PropertiesChanged даёт обновления
в момент их появления.
"""

import asyncio
import hashlib
import threading
from collections.abc import Callable
from urllib.parse import unquote, urlparse

from lanpad.platform.base import MediaBackend
from lanpad.protocol import MediaState

BUS_PREFIX = "org.mpris.MediaPlayer2"
OBJECT_PATH = "/org/mpris/MediaPlayer2"
PLAYER_INTERFACE = "org.mpris.MediaPlayer2.Player"

_ART_PATHS: dict[str, str] = {}


def art_id_for(url: str) -> str:
    """Короткий стабильный идентификатор для локального файла обложки."""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _artist_of(metadata: dict) -> str:
    artist = metadata.get("xesam:artist", "")
    if isinstance(artist, str):
        return artist
    if isinstance(artist, list):
        return ", ".join(str(a) for a in artist)
    return ""


def _art_of(metadata: dict) -> str | None:
    url = metadata.get("mpris:artUrl")
    if not url or not isinstance(url, str):
        return None
    if url.startswith("file://"):
        art_id = art_id_for(url)
        _ART_PATHS[art_id] = unquote(urlparse(url).path)
        return f"/art?id={art_id}"
    return url


def metadata_to_state(
    metadata: dict,
    playback_status: str,
    position_us: int,
    can_seek: bool,
) -> MediaState:
    """Превратить сырые метаданные MPRIS в состояние для телефона."""
    length_us = metadata.get("mpris:length") or 0
    return MediaState(
        playing=(playback_status == "Playing"),
        title=str(metadata.get("xesam:title") or ""),
        artist=_artist_of(metadata),
        art=_art_of(metadata),
        position=round(position_us / 1_000_000, 2),
        duration=round(int(length_us) / 1_000_000, 2),
        can_seek=can_seek,
    )


class MprisMedia(MediaBackend):
    """Следит за первым найденным плеером и отдаёт его состояние."""

    def __init__(self) -> None:
        self._state: MediaState | None = None
        self._subscribers: list[Callable[[MediaState | None], None]] = []
        self._loop: asyncio.AbstractEventLoop | None = None
        self._player = None
        self._ready = threading.Event()
        self._stopping = False
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="lanpad-mpris")
        self._thread.start()
        self._ready.wait(timeout=5)

    # --- публичный интерфейс ---------------------------------------------

    def state(self) -> MediaState | None:
        return self._state

    def command(self, action: str) -> None:
        method = {"play": "call_play_pause", "next": "call_next", "prev": "call_previous"}
        name = method.get(action)
        if name:
            self._call_on_player(name)

    def seek(self, position: float) -> None:
        self._call_on_player("call_set_position", seconds=position)

    def subscribe(self, callback: Callable[[MediaState | None], None]) -> None:
        self._subscribers.append(callback)

    def art_path_for(self, art_id: str) -> str | None:
        return _ART_PATHS.get(art_id)

    def close(self) -> None:
        self._stopping = True
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)

    # --- внутреннее -------------------------------------------------------

    def _publish(self) -> None:
        for callback in self._subscribers:
            callback(self._state)

    def _call_on_player(self, method_name: str, **kwargs) -> None:
        if self._loop is None or self._player is None:
            return
        asyncio.run_coroutine_threadsafe(
            self._invoke(method_name, **kwargs), self._loop
        )

    async def _invoke(self, method_name: str, **kwargs) -> None:
        player = self._player
        if player is None:
            return
        try:
            if method_name == "call_set_position":
                track_id = (await player.get_metadata()).get("mpris:trackid")
                if track_id is None:
                    return
                await player.call_set_position(
                    track_id.value if hasattr(track_id, "value") else track_id,
                    int(kwargs["seconds"] * 1_000_000),
                )
            else:
                await getattr(player, method_name)()
        except Exception:  # noqa: BLE001 — плеер мог исчезнуть между вызовами
            return

    def _run_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._connect())
        except Exception:  # noqa: BLE001 — без D-Bus просто нет медиа
            self._ready.set()
            return
        self._ready.set()
        self._loop.run_forever()

    async def _connect(self) -> None:
        from dbus_next import BusType
        from dbus_next.aio import MessageBus

        bus = await MessageBus(bus_type=BusType.SESSION).connect()
        introspection = await bus.introspect("org.freedesktop.DBus", "/org/freedesktop/DBus")
        proxy = bus.get_proxy_object("org.freedesktop.DBus", "/org/freedesktop/DBus", introspection)
        names = await proxy.get_interface("org.freedesktop.DBus").call_list_names()

        player_name = next((n for n in names if n.startswith(BUS_PREFIX + ".")), None)
        if player_name is None:
            self._state = None
            return

        player_introspection = await bus.introspect(player_name, OBJECT_PATH)
        player_proxy = bus.get_proxy_object(player_name, OBJECT_PATH, player_introspection)
        self._player = player_proxy.get_interface(PLAYER_INTERFACE)
        properties = player_proxy.get_interface("org.freedesktop.DBus.Properties")

        async def refresh() -> None:
            try:
                metadata = {k: v.value for k, v in (await self._player.get_metadata()).items()}
                status = await self._player.get_playback_status()
                position = await self._player.get_position()
                can_seek = await self._player.get_can_seek()
            except Exception:  # noqa: BLE001
                self._state = None
            else:
                self._state = metadata_to_state(metadata, status, position, can_seek)
            self._publish()

        def on_properties_changed(interface, changed, invalidated) -> None:  # noqa: ARG001
            if not self._stopping:
                asyncio.create_task(refresh())  # noqa: RUF006

        properties.on_properties_changed(on_properties_changed)
        await refresh()

    @staticmethod
    def is_available() -> bool:
        try:
            import dbus_next  # noqa: F401
        except ImportError:
            return False
        return True
```

- [ ] **Step 4: Убедиться, что тесты проходят**

Run: `.venv/bin/pytest tests/test_media_mpris.py -q && .venv/bin/ruff check .`
Expected: 13 тестов проходят

- [ ] **Step 5: Проверить на живой системе**

Запустить любой плеер (Spotify, YouTube в браузере, `mpv`), затем:

```bash
.venv/bin/python -c "
import time
from lanpad.platform.linux.media_mpris import MprisMedia
m = MprisMedia()
time.sleep(2)
print(m.state())
m.close()
"
```
Expected: название трека, исполнитель, длительность. Если ничего не играет — `None`, это правильно.

- [ ] **Step 6: Коммит**

```bash
git add src/lanpad/platform/linux/media_mpris.py tests/test_media_mpris.py
git commit -m "feat: медиа через MPRIS с push-обновлениями вместо опроса"
```

---

### Task 9: Буфер обмена и выбор реализаций

Буфер обмена с запасным путём для X11 и модуль, который собирает доступные реализации в один набор.

**Files:**
- Create: `src/lanpad/platform/linux/clipboard_wl.py`, `src/lanpad/platform/registry.py`
- Create: `tests/test_registry.py`

**Interfaces:**
- Consumes: все реализации из `platform.linux`, `platform.base.Backends`
- Produces:
  - `WaylandClipboard()` — реализация `ClipboardBackend`, использует `wl-copy`, при его отсутствии `xclip`
  - `WaylandClipboard.is_available() -> bool`
  - `build_backends(input_backend=None) -> Backends` — собирает набор, пропуская недоступное

- [ ] **Step 1: Написать падающие тесты**

Создать `tests/test_registry.py`:

```python
from lanpad.platform import registry
from lanpad.platform.fake import FakeInput


def test_builds_backends_with_given_input():
    backends = registry.build_backends(input_backend=FakeInput())
    assert isinstance(backends.input, FakeInput)


def test_capabilities_match_assembled_backends():
    backends = registry.build_backends(input_backend=FakeInput())
    caps = backends.capabilities()
    assert caps.audio == (backends.audio is not None)
    assert caps.media == (backends.media is not None)
    assert caps.clipboard == (backends.clipboard is not None)


def test_missing_optional_backend_does_not_break_assembly(monkeypatch):
    """Нет wpctl — нет громкости, но агент обязан подняться."""
    from lanpad.platform.linux.audio_wpctl import WpctlAudio

    monkeypatch.setattr(WpctlAudio, "is_available", staticmethod(lambda: False))
    backends = registry.build_backends(input_backend=FakeInput())
    assert backends.audio is None
    assert backends.capabilities().audio is False
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `.venv/bin/pytest tests/test_registry.py -q`
Expected: FAIL с `ModuleNotFoundError: No module named 'lanpad.platform.registry'`

- [ ] **Step 3: Написать `src/lanpad/platform/linux/clipboard_wl.py`**

```python
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
```

- [ ] **Step 4: Написать `src/lanpad/platform/registry.py`**

```python
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
```

- [ ] **Step 5: Убедиться, что тесты проходят**

Run: `.venv/bin/pytest tests/test_registry.py -q && .venv/bin/ruff check .`
Expected: 3 теста проходят

- [ ] **Step 6: Коммит**

```bash
git add src/lanpad/platform/linux/clipboard_wl.py src/lanpad/platform/registry.py tests/test_registry.py
git commit -m "feat: буфер обмена и сборка доступных реализаций платформы"
```

---

### Task 10: Сессия

Сердце агента: превращает разобранные события в вызовы бэкендов и рассылает состояние по изменению. Здесь же живёт правило «непечатаемый текст идёт через буфер обмена».

**Files:**
- Create: `src/lanpad/session.py`
- Create: `tests/test_session.py`

**Interfaces:**
- Consumes: `protocol.*`, `platform.base.Backends`
- Produces:
  - `Session(backends: Backends, on_state: Callable[[dict], None])`
  - `Session.handle(events: list[Event]) -> None`
  - `Session.current_state() -> dict`
  - `Session.set_listener(on_state: Callable[[dict], None]) -> None`
  - `Session.media_art_path(art_id: str) -> str | None`
  - `Session.close() -> None`

- [ ] **Step 1: Написать падающие тесты**

Создать `tests/test_session.py`:

```python
from lanpad import protocol as p
from lanpad.platform.base import Backends
from lanpad.platform.fake import FakeAudio, FakeClipboard, FakeInput, FakeMedia
from lanpad.session import Session


def make_session(clipboard_succeeds: bool = True):
    backends = Backends(
        input=FakeInput(),
        audio=FakeAudio(),
        media=FakeMedia(),
        clipboard=FakeClipboard(succeeds=clipboard_succeeds),
    )
    sent: list[dict] = []
    session = Session(backends, on_state=sent.append)
    return session, backends, sent


def test_move_reaches_input_backend():
    session, backends, _ = make_session()
    session.handle([p.Move(5, -3)])
    assert ("move", 5, -3) in backends.input.calls


def test_click_reaches_input_backend():
    session, backends, _ = make_session()
    session.handle([p.Click("r")])
    assert ("click", "r") in backends.input.calls


def test_events_are_applied_in_order():
    session, backends, _ = make_session()
    session.handle([p.Move(1, 1), p.Click("l"), p.Wheel(2)])
    assert backends.input.calls == [("move", 1, 1), ("click", "l"), ("wheel", 2)]


def test_ascii_text_is_typed_directly():
    session, backends, _ = make_session()
    session.handle([p.TypeText("hello")])
    assert ("type_text", "hello") in backends.input.calls
    assert backends.clipboard.calls == []


def test_cyrillic_text_goes_through_clipboard():
    session, backends, _ = make_session()
    session.handle([p.TypeText("привет")])
    assert ("copy", "привет") in backends.clipboard.calls
    assert ("combo", ["ctrl", "v"]) in backends.input.calls


def test_paste_uses_clipboard_and_ctrl_v():
    session, backends, _ = make_session()
    session.handle([p.Paste("любой текст", terminal=False)])
    assert ("copy", "любой текст") in backends.clipboard.calls
    assert ("combo", ["ctrl", "v"]) in backends.input.calls


def test_terminal_paste_uses_ctrl_shift_v():
    session, backends, _ = make_session()
    session.handle([p.Paste("ls -la", terminal=True)])
    assert ("combo", ["ctrl", "shift", "v"]) in backends.input.calls


def test_failed_clipboard_copy_does_not_paste():
    """Если положить в буфер не удалось, Ctrl+V вставил бы чужое содержимое."""
    session, backends, _ = make_session(clipboard_succeeds=False)
    session.handle([p.Paste("текст", terminal=False)])
    assert not any(call[0] == "combo" for call in backends.input.calls)


def test_volume_set_reaches_audio_backend():
    session, backends, _ = make_session()
    session.handle([p.VolumeSet(70)])
    assert ("set_percent", 70) in backends.audio.calls


def test_media_command_reaches_media_backend():
    session, backends, _ = make_session()
    session.handle([p.MediaCommand("next")])
    assert ("command", "next") in backends.media.calls


def test_seek_reaches_media_backend():
    session, backends, _ = make_session()
    session.handle([p.Seek(42.5)])
    assert ("seek", 42.5) in backends.media.calls


def test_state_is_pushed_after_volume_change():
    session, _, sent = make_session()
    sent.clear()
    session.handle([p.VolumeSet(30)])
    assert sent
    assert sent[-1]["audio"]["volume"] == 30


def test_cursor_movement_does_not_push_state():
    """Иначе каждое движение пальца порождало бы пакет обратно."""
    session, _, sent = make_session()
    sent.clear()
    session.handle([p.Move(1, 1), p.Move(2, 2)])
    assert sent == []


def test_media_change_from_backend_is_pushed():
    session, backends, sent = make_session()
    sent.clear()
    backends.media.command("play")
    assert sent
    assert sent[-1]["media"]["playing"] is True


def test_current_state_includes_capabilities():
    session, _, _ = make_session()
    state = session.current_state()
    assert state["caps"] == {"audio": True, "media": True, "clipboard": True}


def test_missing_backends_are_tolerated():
    backends = Backends(input=FakeInput(), audio=None, media=None, clipboard=None)
    session = Session(backends, on_state=lambda _: None)
    session.handle([p.VolumeSet(50), p.MediaCommand("play"), p.Paste("x", terminal=False)])
    assert backends.input.calls == []
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `.venv/bin/pytest tests/test_session.py -q`
Expected: FAIL с `ModuleNotFoundError: No module named 'lanpad.session'`

- [ ] **Step 3: Написать модуль**

Создать `src/lanpad/session.py`:

```python
"""Применение событий к системе и рассылка состояния телефону.

Состояние отправляется по изменению, а не по расписанию. Движения курсора
изменением не считаются: иначе каждое касание пальца порождало бы пакет в
обратную сторону и съедало ту самую задержку, ради которой всё делается.
"""

from collections.abc import Callable

from lanpad import protocol as p
from lanpad.platform.base import Backends

_CYRILLIC_FALLBACK_KEYS = ["ctrl", "v"]
_TERMINAL_PASTE_KEYS = ["ctrl", "shift", "v"]


class Session:
    def __init__(self, backends: Backends, on_state: Callable[[dict], None]) -> None:
        self._backends = backends
        self._on_state = on_state
        if backends.media is not None:
            backends.media.subscribe(self._on_media_changed)

    # --- приём событий ----------------------------------------------------

    def handle(self, events: list[p.Event]) -> None:
        state_touched = False
        for event in events:
            state_touched |= self._apply(event)
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

    def set_listener(self, on_state: Callable[[dict], None]) -> None:
        """Переключить получателя состояния на время жизни соединения."""
        self._on_state = on_state

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
        self._on_state(self.current_state())

    def close(self) -> None:
        self._backends.close()
```

- [ ] **Step 4: Убедиться, что тесты проходят**

Run: `.venv/bin/pytest tests/test_session.py -q && .venv/bin/ruff check .`
Expected: 16 тестов проходят

- [ ] **Step 5: Коммит**

```bash
git add src/lanpad/session.py tests/test_session.py
git commit -m "feat: сессия применяет события и рассылает состояние по изменению"
```

---

### Task 11: Конфигурация и токен

Порт, пути, генерация и загрузка токена. Токен хранится в каталоге данных пользователя, а не рядом с кодом — иначе он снова окажется в репозитории.

**Files:**
- Create: `src/lanpad/config.py`
- Create: `tests/test_config.py`

**Interfaces:**
- Consumes: ничего
- Produces:
  - `data_dir() -> Path` — каталог данных, создаётся при обращении
  - `load_or_create_token(path: Path | None = None) -> str`
  - `token_matches(candidate: str, token: str) -> bool` — сравнение через `compare_digest`
  - `is_private_client(host: str) -> bool`
  - `port() -> int`
  - `DEFAULT_PORT = 8477`

- [ ] **Step 1: Написать падающие тесты**

Создать `tests/test_config.py`:

```python
import pytest

from lanpad import config


def test_creates_token_when_absent(tmp_path):
    token_file = tmp_path / "token"
    token = config.load_or_create_token(token_file)
    assert token
    assert token_file.read_text().strip() == token


def test_reuses_existing_token(tmp_path):
    token_file = tmp_path / "token"
    first = config.load_or_create_token(token_file)
    assert config.load_or_create_token(token_file) == first


def test_token_file_is_not_world_readable(tmp_path):
    token_file = tmp_path / "token"
    config.load_or_create_token(token_file)
    assert token_file.stat().st_mode & 0o077 == 0


def test_blank_token_file_is_regenerated(tmp_path):
    token_file = tmp_path / "token"
    token_file.write_text("   \n")
    assert config.load_or_create_token(token_file).strip()


def test_token_comparison_accepts_match():
    assert config.token_matches("secret", "secret") is True


def test_token_comparison_rejects_mismatch():
    assert config.token_matches("wrong", "secret") is False


def test_token_comparison_rejects_empty():
    assert config.token_matches("", "secret") is False


@pytest.mark.parametrize("host", [
    "127.0.0.1", "192.168.1.50", "10.0.0.7", "172.16.3.9", "::1", "fe80::1",
])
def test_private_and_loopback_clients_are_allowed(host):
    assert config.is_private_client(host) is True


@pytest.mark.parametrize("host", ["8.8.8.8", "203.0.113.10", "2001:4860:4860::8888"])
def test_public_clients_are_refused(host):
    assert config.is_private_client(host) is False


def test_garbage_host_is_refused():
    assert config.is_private_client("не адрес") is False


def test_port_defaults(monkeypatch):
    monkeypatch.delenv("LANPAD_PORT", raising=False)
    assert config.port() == config.DEFAULT_PORT


def test_port_reads_environment(monkeypatch):
    monkeypatch.setenv("LANPAD_PORT", "9000")
    assert config.port() == 9000


def test_invalid_port_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("LANPAD_PORT", "не число")
    assert config.port() == config.DEFAULT_PORT
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `.venv/bin/pytest tests/test_config.py -q`
Expected: FAIL с `ModuleNotFoundError: No module named 'lanpad.config'`

- [ ] **Step 3: Написать модуль**

Создать `src/lanpad/config.py`:

```python
"""Порт, пути и токен доступа.

Токен лежит в каталоге данных пользователя, а не рядом с исходниками:
в прототипе он лежал в каталоге проекта и рисковал попасть в репозиторий.
"""

import ipaddress
import os
import secrets
from pathlib import Path

DEFAULT_PORT = 8477
TOKEN_BYTES = 9


def data_dir() -> Path:
    """Каталог данных по XDG, создаётся при первом обращении."""
    base = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
    path = Path(base) / "lanpad"
    path.mkdir(parents=True, exist_ok=True)
    return path


def token_path() -> Path:
    return data_dir() / "token"


def load_or_create_token(path: Path | None = None) -> str:
    """Прочитать токен, создав его при первом запуске."""
    target = path or token_path()
    try:
        existing = target.read_text().strip()
        if existing:
            return existing
    except (FileNotFoundError, OSError):
        pass

    token = secrets.token_urlsafe(TOKEN_BYTES)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(token + "\n")
    target.chmod(0o600)
    return token


def token_matches(candidate: str, token: str) -> bool:
    """Сравнение, не зависящее от времени выполнения."""
    if not candidate or not token:
        return False
    return secrets.compare_digest(candidate, token)


def is_private_client(host: str) -> bool:
    """Пускаем только из локальной сети и с самой машины."""
    try:
        address = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return False
    return address.is_private or address.is_loopback or address.is_link_local


def port() -> int:
    raw = os.environ.get("LANPAD_PORT")
    if raw is None:
        return DEFAULT_PORT
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_PORT
    return value if 1 <= value <= 65535 else DEFAULT_PORT
```

- [ ] **Step 4: Убедиться, что тесты проходят**

Run: `.venv/bin/pytest tests/test_config.py -q && .venv/bin/ruff check .`
Expected: 13 тестов проходят

- [ ] **Step 5: Коммит**

```bash
git add src/lanpad/config.py tests/test_config.py
git commit -m "feat: конфигурация, токен в каталоге данных, проверка подсети"
```

---

### Task 12: HTTP-слой

Маршруты, отдача статики, проверки доступа, отдача обложек и WebSocket-соединение.

**Files:**
- Create: `src/lanpad/http.py`
- Create: `tests/test_http.py`
- Reference: `legacy/server.py:416-556`

**Interfaces:**
- Consumes: `config.*`, `session.Session`, `ws.*`, `protocol.parse_events`
- Produces:
  - `manifest(token: str) -> dict`
  - `origin_allowed(origin: str | None, host: str) -> bool`
  - `safe_static_path(web_root: Path, relative: str) -> Path | None`
  - `cache_header_for(path: str) -> str`
  - `make_server(session, token, web_root, port) -> ThreadingHTTPServer`

- [ ] **Step 1: Написать падающие тесты**

Создать `tests/test_http.py`:

```python
from pathlib import Path

import pytest

from lanpad import http as h


def test_manifest_is_standalone_and_carries_token():
    manifest = h.manifest("abc123")
    assert manifest["display"] == "standalone"
    assert manifest["start_url"] == "/?t=abc123"
    assert manifest["name"] == "lanpad"


def test_manifest_lists_icons():
    icons = h.manifest("t")["icons"]
    assert any(icon["sizes"] == "512x512" for icon in icons)


def test_origin_matching_host_is_allowed():
    assert h.origin_allowed("http://192.168.1.50:8477", "192.168.1.50:8477") is True


def test_absent_origin_is_allowed():
    """Не браузер — не подделка межсайтового запроса."""
    assert h.origin_allowed(None, "192.168.1.50:8477") is True


def test_foreign_origin_is_refused():
    assert h.origin_allowed("https://зло.example", "192.168.1.50:8477") is False


def test_origin_with_different_port_is_refused():
    assert h.origin_allowed("http://192.168.1.50:9999", "192.168.1.50:8477") is False


def test_static_path_inside_root_is_resolved(tmp_path):
    (tmp_path / "assets").mkdir()
    target = tmp_path / "assets" / "app.js"
    target.write_text("x")
    assert h.safe_static_path(tmp_path, "/assets/app.js") == target


def test_static_path_escaping_root_is_refused(tmp_path):
    assert h.safe_static_path(tmp_path, "/../../etc/passwd") is None


def test_static_path_with_encoded_traversal_is_refused(tmp_path):
    assert h.safe_static_path(tmp_path, "/assets/../../etc/passwd") is None


def test_missing_static_file_is_refused(tmp_path):
    assert h.safe_static_path(tmp_path, "/нет-такого.js") is None


@pytest.mark.parametrize("path,expected_immutable", [
    ("/assets/app-a1b2c3.js", True),
    ("/assets/font.woff2", True),
    ("/index.html", False),
    ("/manifest.webmanifest", False),
])
def test_cache_headers(path, expected_immutable):
    header = h.cache_header_for(path)
    assert ("immutable" in header) is expected_immutable
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `.venv/bin/pytest tests/test_http.py -q`
Expected: FAIL с `ModuleNotFoundError: No module named 'lanpad.http'`

- [ ] **Step 3: Написать модуль**

Создать `src/lanpad/http.py`:

```python
"""HTTP-слой: статика, манифест, обложки и WebSocket-соединение."""

import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from lanpad import ws
from lanpad.config import is_private_client, token_matches
from lanpad.protocol import parse_events
from lanpad.session import Session

IMMUTABLE_EXTENSIONS = {".js", ".css", ".woff2", ".png", ".ico", ".svg"}
IMMUTABLE_HEADER = "public, max-age=31536000, immutable"
NO_CACHE_HEADER = "no-cache"


def manifest(token: str) -> dict:
    return {
        "name": "lanpad",
        "short_name": "lanpad",
        "description": "Тачпад, клавиатура и пульт для компьютера в локальной сети",
        "start_url": f"/?t={token}",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#000000",
        "theme_color": "#000000",
        "icons": [
            {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"},
            {"src": "/icon-maskable-512.png", "sizes": "512x512",
             "type": "image/png", "purpose": "maskable"},
        ],
    }


def origin_allowed(origin: str | None, host: str) -> bool:
    """Соединение принимается только со своей же страницы.

    Отсутствие заголовка означает не-браузерного клиента: подделать
    межсайтовый запрос он не может.
    """
    if origin is None:
        return True
    parsed = urlparse(origin)
    return parsed.netloc == host


def safe_static_path(web_root: Path, relative: str) -> Path | None:
    """Путь к файлу внутри каталога статики или None, если выход за его пределы."""
    candidate = (web_root / unquote(relative).lstrip("/")).resolve()
    root = web_root.resolve()
    if root not in candidate.parents and candidate != root:
        return None
    return candidate if candidate.is_file() else None


def cache_header_for(path: str) -> str:
    extension = os.path.splitext(path)[1].lower()
    if extension in IMMUTABLE_EXTENSIONS and path.startswith("/assets/"):
        return IMMUTABLE_HEADER
    return NO_CACHE_HEADER


def make_handler(session: Session, token: str, web_root: Path):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        # --- вспомогательное ---------------------------------------------

        def _query(self) -> dict:
            return parse_qs(urlparse(self.path).query)

        def _authorised(self) -> bool:
            supplied = self._query().get("t", [""])[0]
            return token_matches(unquote(supplied), token)

        def _client_allowed(self) -> bool:
            return is_private_client(self.client_address[0])

        def _respond(self, code: int, ctype: str, body: bytes | str,
                     cache: str = NO_CACHE_HEADER, extra: dict | None = None) -> None:
            if isinstance(body, str):
                body = body.encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", cache)
            for key, value in (extra or {}).items():
                self.send_header(key, value)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _serve_static(self, relative: str) -> None:
            target = safe_static_path(web_root, relative)
            if target is None:
                self.send_error(404)
                return
            ctype, _ = mimetypes.guess_type(str(target))
            if target.suffix == ".js":
                ctype = "text/javascript"
            elif target.suffix == ".woff2":
                ctype = "font/woff2"
            self._respond(200, ctype or "application/octet-stream",
                          target.read_bytes(), cache_header_for(relative))

        # --- маршруты -----------------------------------------------------

        def do_GET(self) -> None:  # noqa: N802
            if not self._client_allowed():
                self.send_error(403)
                return
            path = urlparse(self.path).path

            if path == "/":
                self._serve_static("/index.html")
            elif path == "/manifest.webmanifest":
                self._respond(200, "application/manifest+json",
                              json.dumps(manifest(token), ensure_ascii=False))
            elif path == "/art":
                self._serve_art()
            elif path == "/ws":
                self._serve_websocket()
            else:
                self._serve_static(path)

        do_HEAD = do_GET

        def do_POST(self) -> None:  # noqa: N802
            if not self._client_allowed() or urlparse(self.path).path != "/e":
                self.send_error(404)
                return
            if not self._authorised():
                self.send_error(403)
                return
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"[]"
            session.handle(parse_events(raw))
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _serve_art(self) -> None:
            if not self._authorised():
                self.send_error(403)
                return
            path = session.media_art_path(self._query().get("id", [""])[0])
            if path is None or not Path(path).is_file():
                self.send_error(404)
                return
            ctype, _ = mimetypes.guess_type(path)
            self._respond(200, ctype or "image/jpeg", Path(path).read_bytes(),
                          IMMUTABLE_HEADER)

        def _serve_websocket(self) -> None:
            if not self._authorised():
                self.send_error(403)
                return
            if self.headers.get("Upgrade", "").lower() != "websocket":
                self.send_error(400)
                return
            if not origin_allowed(self.headers.get("Origin"), self.headers.get("Host", "")):
                self.send_error(403)
                return

            self.close_connection = True
            self.send_response(101)
            self.send_header("Upgrade", "websocket")
            self.send_header("Connection", "Upgrade")
            self.send_header("Sec-WebSocket-Accept",
                             ws.accept_key(self.headers["Sec-WebSocket-Key"]))
            self.end_headers()

            connection = self.connection
            connection.settimeout(None)

            def push(state: dict) -> None:
                try:
                    connection.sendall(ws.encode_frame(json.dumps(state, ensure_ascii=False)))
                except OSError:
                    pass

            session.set_listener(push)
            push(session.current_state())

            try:
                while True:
                    frame = ws.read_frame(connection.recv)
                    if frame is None:
                        break
                    if frame.opcode == ws.OP_PING:
                        connection.sendall(ws.encode_frame(frame.payload, ws.OP_PONG))
                    elif frame.opcode == ws.OP_TEXT and frame.payload:
                        session.handle(parse_events(frame.payload))
            except OSError:
                pass
            finally:
                session.set_listener(lambda _state: None)

        def log_message(self, *args) -> None:
            """Не засорять вывод: каждое движение курсора — это запрос."""

    return Handler


def make_server(session: Session, token: str, web_root: Path, port: int) -> ThreadingHTTPServer:
    mimetypes.init()
    server = ThreadingHTTPServer(("0.0.0.0", port), make_handler(session, token, web_root))  # noqa: S104
    server.daemon_threads = True
    return server
```

- [ ] **Step 4: Убедиться, что тесты проходят**

Run: `.venv/bin/pytest tests/test_http.py -q && .venv/bin/ruff check .`
Expected: 12 тестов проходят

- [ ] **Step 5: Коммит**

```bash
git add src/lanpad/http.py tests/test_http.py
git commit -m "feat: HTTP-слой с проверкой подсети, Origin и защитой от выхода из каталога"
```

---

### Task 13: QR и запуск

Определение адресов в локальной сети, вывод QR в терминал и точка входа `lanpad`.

**Files:**
- Create: `src/lanpad/qr.py`, `src/lanpad/__main__.py`
- Create: `tests/test_qr.py`
- Reference: `legacy/server.py:559-605`

**Interfaces:**
- Consumes: `config.*`, `platform.registry.build_backends`, `session.Session`, `http.make_server`
- Produces:
  - `lan_addresses() -> list[str]`
  - `connect_url(host: str, port: int, token: str) -> str`
  - `render_terminal(text: str) -> str`
  - `save_png(text: str, path: Path) -> None`
  - `main() -> int`

- [ ] **Step 1: Написать падающие тесты**

Создать `tests/test_qr.py`:

```python
from lanpad import qr


def test_connect_url_contains_host_port_and_token():
    assert qr.connect_url("192.168.1.50", 8477, "abc") == "http://192.168.1.50:8477/?t=abc"


def test_connect_url_escapes_token():
    assert "a%2Bb" in qr.connect_url("10.0.0.1", 8477, "a+b")


def test_terminal_qr_is_non_empty_block():
    rendered = qr.render_terminal("http://192.168.1.50:8477/?t=abc")
    assert rendered.count("\n") > 10


def test_png_is_written(tmp_path):
    target = tmp_path / "qr.png"
    qr.save_png("http://192.168.1.50:8477/?t=abc", target)
    assert target.stat().st_size > 0
    assert target.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_lan_addresses_returns_strings():
    for address in qr.lan_addresses():
        assert isinstance(address, str)
        assert not address.startswith("127.")
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `.venv/bin/pytest tests/test_qr.py -q`
Expected: FAIL с `ModuleNotFoundError: No module named 'lanpad.qr'`

- [ ] **Step 3: Написать `src/lanpad/qr.py`**

```python
"""Адреса в локальной сети и QR для спаривания с телефоном."""

import socket
from pathlib import Path
from urllib.parse import quote

import qrcode
from qrcode.image.pure import PyPNGImage


def lan_addresses() -> list[str]:
    """Адреса машины в локальной сети, без петлевого интерфейса."""
    found: set[str] = set()
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("10.255.255.255", 1))
        found.add(probe.getsockname()[0])
        probe.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            address = info[4][0]
            if not address.startswith("127."):
                found.add(address)
    except socket.gaierror:
        pass
    return sorted(found)


def connect_url(host: str, port: int, token: str) -> str:
    return f"http://{host}:{port}/?t={quote(token, safe='')}"


def render_terminal(text: str) -> str:
    """QR символами полублока — помещается в обычное окно терминала."""
    code = qrcode.QRCode(border=2)
    code.add_data(text)
    code.make(fit=True)
    matrix = code.get_matrix()

    lines = []
    for row in range(0, len(matrix), 2):
        upper = matrix[row]
        lower = matrix[row + 1] if row + 1 < len(matrix) else [False] * len(upper)
        line = "".join(
            "█" if u and lo else "▀" if u else "▄" if lo else " "
            for u, lo in zip(upper, lower, strict=False)
        )
        lines.append(line)
    return "\n".join(lines)


def save_png(text: str, path: Path) -> None:
    image = qrcode.make(text, image_factory=PyPNGImage)
    with open(path, "wb") as handle:
        image.save(handle)
```

- [ ] **Step 4: Написать `src/lanpad/__main__.py`**

```python
"""Точка входа: собрать реализации, поднять сервер, показать QR."""

import argparse
import sys
from pathlib import Path

from lanpad import config, qr
from lanpad.http import make_server
from lanpad.platform.registry import build_backends
from lanpad.session import Session

WEB_ROOT = Path(__file__).parent / "web"


def _print_invitation(token: str, listen_port: int) -> None:
    addresses = qr.lan_addresses()
    if not addresses:
        print("Не удалось определить адрес в локальной сети.")
        print("Проверьте подключение к Wi-Fi и запустите снова.")
        return

    url = qr.connect_url(addresses[0], listen_port, token)
    print()
    print(qr.render_terminal(url))
    print()
    print("Отсканируйте код телефоном, подключённым к той же сети Wi-Fi.")
    print(f"    {url}")
    if len(addresses) > 1:
        print("\nЕсли не открылось, попробуйте другой адрес:")
        for address in addresses[1:]:
            print(f"    {qr.connect_url(address, listen_port, token)}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="lanpad",
        description="Телефон как тачпад и пульт для этого компьютера.",
    )
    parser.add_argument("--port", type=int, default=None, help="порт (по умолчанию 8477)")
    parser.add_argument("--qr", metavar="ФАЙЛ", help="сохранить QR в PNG и выйти")
    parser.add_argument("--install-service", action="store_true",
                        help="установить автозапуск через systemd и выйти")
    args = parser.parse_args()

    token = config.load_or_create_token()
    listen_port = args.port or config.port()

    if args.qr:
        addresses = qr.lan_addresses()
        if not addresses:
            print("Нет адреса в локальной сети.", file=sys.stderr)
            return 1
        qr.save_png(qr.connect_url(addresses[0], listen_port, token), Path(args.qr))
        print(f"QR сохранён: {args.qr}")
        return 0

    if args.install_service:
        from lanpad.service import install

        return install()

    try:
        backends = build_backends()
    except Exception as exc:  # noqa: BLE001
        print(f"Не удалось получить доступ к вводу: {exc}", file=sys.stderr)
        return 1

    session = Session(backends, on_state=lambda _state: None)
    server = make_server(session, token, WEB_ROOT, listen_port)

    _print_invitation(token, listen_port)
    caps = backends.capabilities()
    print(f"Громкость: {'да' if caps.audio else 'нет'}   "
          f"Медиа: {'да' if caps.media else 'нет'}   "
          f"Буфер обмена: {'да' if caps.clipboard else 'нет'}")
    print("Ctrl+C — остановить.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nОстановлено.")
    finally:
        server.shutdown()
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Положить временную статику**

Пока приложение не переписано (это второй план), агенту нужно что-то раздавать:

```bash
mkdir -p src/lanpad/web
cp -r legacy/web/. src/lanpad/web/
rm -f src/lanpad/web/sw.js
```

Затем открыть `src/lanpad/web/assets/app.js` и удалить компонент `NoteOverlay` вместе с массивом `NOTE`, ссылкой `${note && html\`<${NoteOverlay} …\`}` и кнопкой с сердцем в строке состояния. Убедиться, что от записки ничего не осталось:

```bash
grep -rn "NoteOverlay\|note-overlay\|NOTE = \[" src/ && echo "НАЙДЕНО — удалить перед коммитом" || echo "чисто"
```

- [ ] **Step 6: Убедиться, что тесты проходят**

Run: `.venv/bin/pytest -q && .venv/bin/ruff check .`
Expected: весь набор тестов зелёный

- [ ] **Step 7: Запустить агент целиком**

Run: `.venv/bin/lanpad`
Expected: в терминале появляется QR и адрес. Отсканировать телефоном, убедиться, что курсор двигается, громкость меняется, клавиши работают.

- [ ] **Step 8: Коммит**

```bash
git add src/lanpad/qr.py src/lanpad/__main__.py src/lanpad/web tests/test_qr.py
git commit -m "feat: QR для спаривания и точка входа lanpad"
```

---

### Task 14: Установка службы

Команда `lanpad --install-service` пишет systemd-юнит и включает его. В прототипе это делалось руками.

**Files:**
- Create: `src/lanpad/service.py`
- Create: `tests/test_service.py`

**Interfaces:**
- Consumes: ничего
- Produces:
  - `unit_text(executable: str) -> str`
  - `unit_path() -> Path`
  - `install() -> int` — код возврата для CLI

- [ ] **Step 1: Написать падающие тесты**

Создать `tests/test_service.py`:

```python
from lanpad import service


def test_unit_runs_given_executable():
    text = service.unit_text("/usr/bin/lanpad")
    assert "ExecStart=/usr/bin/lanpad" in text


def test_unit_is_tied_to_graphical_session():
    text = service.unit_text("/usr/bin/lanpad")
    assert "After=graphical-session.target" in text
    assert "PartOf=graphical-session.target" in text


def test_unit_restarts_on_failure():
    assert "Restart=on-failure" in service.unit_text("/usr/bin/lanpad")


def test_unit_is_wanted_by_default_target():
    assert "WantedBy=default.target" in service.unit_text("/usr/bin/lanpad")


def test_unit_does_not_mention_prototype_name():
    assert "remote-touchpad" not in service.unit_text("/usr/bin/lanpad")


def test_unit_path_is_in_user_systemd_directory():
    assert service.unit_path().as_posix().endswith("systemd/user/lanpad.service")


def test_unit_path_follows_xdg_config_home(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert service.unit_path() == tmp_path / "systemd" / "user" / "lanpad.service"
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `.venv/bin/pytest tests/test_service.py -q`
Expected: FAIL с `ModuleNotFoundError: No module named 'lanpad.service'`

- [ ] **Step 3: Написать модуль**

Создать `src/lanpad/service.py`:

```python
"""Установка автозапуска через systemd --user."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

UNIT_NAME = "lanpad.service"


def unit_text(executable: str) -> str:
    return f"""[Unit]
Description=lanpad — телефон как тачпад и пульт
After=graphical-session.target
PartOf=graphical-session.target
StartLimitIntervalSec=0

[Service]
Type=simple
ExecStart={executable}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
"""


def unit_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")
    return Path(base) / "systemd" / "user" / UNIT_NAME


def install() -> int:
    executable = shutil.which("lanpad")
    if executable is None:
        print("Команда lanpad не найдена в PATH.", file=sys.stderr)
        print("Установите пакет через `pipx install lanpad` и повторите.", file=sys.stderr)
        return 1

    target = unit_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(unit_text(executable))
    print(f"Юнит записан: {target}")

    for command in (
        ["systemctl", "--user", "daemon-reload"],
        ["systemctl", "--user", "enable", "--now", UNIT_NAME],
    ):
        result = subprocess.run(command, check=False)  # noqa: S603
        if result.returncode != 0:
            print(f"Команда не удалась: {' '.join(command)}", file=sys.stderr)
            return result.returncode

    print("Служба включена и запущена.")
    print(f"QR для телефона: journalctl --user -u {UNIT_NAME} -n 40")
    return 0
```

- [ ] **Step 4: Убедиться, что тесты проходят**

Run: `.venv/bin/pytest -q && .venv/bin/ruff check .`
Expected: весь набор зелёный

- [ ] **Step 5: Убрать старую службу прототипа и проверить новую**

```bash
systemctl --user disable --now remote-touchpad.service 2>/dev/null || true
rm -f ~/.config/systemd/user/remote-touchpad.service
systemctl --user daemon-reload
```

Затем установить пакет и службу:

```bash
pipx install --editable .
lanpad --install-service
systemctl --user status lanpad
```
Expected: служба активна, в журнале виден QR

- [ ] **Step 6: Удалить прототип**

```bash
rm -rf legacy/
```

Убедиться, что агент по-прежнему работает после удаления, затем закоммитить:

```bash
git add src/lanpad/service.py tests/test_service.py
git commit -m "feat: установка автозапуска командой lanpad --install-service"
```

---

## Проверка перед сдачей плана

- [ ] `.venv/bin/pytest -q` — весь набор зелёный
- [ ] `.venv/bin/ruff check .` — без замечаний
- [ ] `grep -rn "NoteOverlay\|note-overlay\|claude-remote" src/ tests/` — пусто
- [ ] `git log --all -p | grep -n "NoteOverlay\|note-overlay"` — пусто, личного содержимого нет во всей истории
- [ ] `git status --short` — нет незакоммиченных файлов и нет `token`
- [ ] Агент поднимается, телефон подключается, курсор двигается, громкость меняется, медиа-состояние приходит
