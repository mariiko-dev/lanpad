import threading

import pytest
from evdev import ecodes as E

from lanpad.platform.linux.input_uinput import UinputInput, WheelAccumulator


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


class ExplodingDevice:
    """Виртуальное устройство, ломающееся после N успешных записей.

    Событие записывается до выброса — так тест видит и то, что агент
    пытался отправить уже на сломанном устройстве.
    """

    def __init__(self, fail_after: int, error: type[Exception] = OSError) -> None:
        self.fail_after = fail_after
        self.error = error
        self.events: list[tuple[int, int, int]] = []

    def write(self, etype: int, code: int, value: int) -> None:
        self.events.append((etype, code, value))
        if len(self.events) > self.fail_after:
            raise self.error("устройство отвалилось")

    def syn(self) -> None:
        pass

    def close(self) -> None:
        pass


def backend_with(device: ExplodingDevice) -> UinputInput:
    backend = UinputInput.__new__(UinputInput)
    backend._device = device
    backend._lock = threading.Lock()
    backend._wheel = WheelAccumulator()
    return backend


def held_keys(events: list[tuple[int, int, int]]) -> set[int]:
    """Клавиши, оставшиеся нажатыми по итогам последовательности."""
    state: dict[int, int] = {}
    for etype, code, value in events:
        if etype == E.EV_KEY:
            state[code] = value
    return {code for code, value in state.items() if value == 1}


def test_combo_releases_modifiers_when_device_fails():
    device = ExplodingDevice(fail_after=2)
    backend = backend_with(device)
    with pytest.raises(OSError):
        backend.combo(["ctrl", "shift", "c"])
    assert held_keys(device.events) == set()


def test_combo_releases_everything_when_first_write_fails():
    device = ExplodingDevice(fail_after=0)
    backend = backend_with(device)
    with pytest.raises(OSError):
        backend.combo(["ctrl", "c"])
    assert held_keys(device.events) == set()


def sweep_positions(action, text_or_keys, limit: int, error: type[Exception]):
    """Прогнать сбой устройства на каждой позиции последовательности."""
    leaks = {}
    for fail_after in range(limit):
        device = ExplodingDevice(fail_after=fail_after, error=error)
        backend = backend_with(device)
        try:  # noqa: SIM105
            action(backend, text_or_keys)
        except Exception:
            pass
        held = held_keys(device.events)
        if held:
            leaks[fail_after] = sorted(held)
    return leaks


def test_type_text_never_leaves_keys_held_at_any_failure_point():
    leaks = sweep_positions(lambda b, t: b.type_text(t), "aAbB", 14, OSError)
    assert leaks == {}


def test_combo_never_leaves_keys_held_at_any_failure_point():
    leaks = sweep_positions(lambda b, k: b.combo(k), ["ctrl", "shift", "c"], 10, OSError)
    assert leaks == {}


def test_type_text_survives_a_non_oserror_device():
    leaks = sweep_positions(lambda b, t: b.type_text(t), "aA", 8, RuntimeError)
    assert leaks == {}


def test_combo_survives_a_non_oserror_device():
    leaks = sweep_positions(lambda b, k: b.combo(k), ["ctrl", "alt", "t"], 8, RuntimeError)
    assert leaks == {}


def test_combo_leaves_nothing_held_on_the_happy_path():
    device = ExplodingDevice(fail_after=1000)
    backend = backend_with(device)
    backend.combo(["ctrl", "alt", "t"])
    assert held_keys(device.events) == set()


def test_type_text_leaves_nothing_held_on_the_happy_path():
    device = ExplodingDevice(fail_after=1000)
    backend = backend_with(device)
    backend.type_text("aA")
    assert held_keys(device.events) == set()


def test_click_never_leaves_the_button_held_at_any_failure_point():
    """Отпускание кнопки идёт через `finally`, как в combo и type_text."""
    leaks = sweep_positions(lambda b, n: b.click(n), "l", 5, OSError)
    assert leaks == {}


def test_click_survives_a_non_oserror_device():
    leaks = sweep_positions(lambda b, n: b.click(n), "l", 5, RuntimeError)
    assert leaks == {}


def test_click_leaves_nothing_held_on_the_happy_path():
    device = ExplodingDevice(fail_after=1000)
    backend = backend_with(device)
    backend.click("l")
    assert held_keys(device.events) == set()
