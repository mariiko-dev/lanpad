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
