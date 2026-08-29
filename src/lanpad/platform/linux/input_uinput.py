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
        # Округление гасит накопленную ошибку float: без него сумма ста
        # шагов по 0.1 давала бы 9 целых щелчков вместо 10.
        whole = int(round(self._remainder, 9))
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

    def _press(self, code: int, pressed: list[int]) -> None:
        """Нажать клавишу, заранее записав её в список удерживаемых.

        Запись идёт до отправки события намеренно: если отправка сорвётся
        на полпути, клавиша всё равно попадёт в список и будет отпущена.
        Лишнее отпускание ненажатой клавиши безвредно, зажатая — нет.
        """
        pressed.append(code)
        self._emit_key(code, 1)
        self._device.syn()

    def _release_one(self, code: int) -> None:
        """Отпустить клавишу, что бы ни случилось с устройством."""
        try:
            self._emit_key(code, 0)
            self._device.syn()
        except OSError:
            pass

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
            pressed: list[int] = []
            try:
                for code in modifiers:
                    self._press(code, pressed)
                self._press(final, pressed)
            finally:
                while pressed:
                    self._release_one(pressed.pop())

    def type_text(self, text: str) -> None:
        """Набрать текст посимвольно.

        Работает только для символов из раскладки. Кириллица и прочее
        отправляются через буфер обмена — этим занимается сессия.
        """
        if not self.can_type(text):
            return
        with self._lock:
            shift_down = False
            try:
                for char in text:
                    code, needs_shift = CHARMAP[char]
                    if needs_shift:
                        self._emit_key(E.KEY_LEFTSHIFT, 1)
                        shift_down = True
                    self._emit_key(code, 1)
                    self._device.syn()
                    self._emit_key(code, 0)
                    if needs_shift:
                        self._emit_key(E.KEY_LEFTSHIFT, 0)
                        shift_down = False
                    self._device.syn()
                    time.sleep(TYPE_DELAY_SECONDS)
            finally:
                if shift_down:
                    self._release_one(E.KEY_LEFTSHIFT)

    def can_type(self, text: str) -> bool:
        """Можно ли набрать текст напрямую, без буфера обмена."""
        return bool(text) and all(char in CHARMAP for char in text)

    def close(self) -> None:
        self._device.close()
