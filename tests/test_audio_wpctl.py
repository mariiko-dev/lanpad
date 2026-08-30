import pytest

from lanpad.platform.linux.audio_wpctl import WpctlAudio, parse_volume


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


@pytest.mark.parametrize("garbage", [
    "Volume: .\n",
    "Volume: ..\n",
    "Volume: 1.2.3\n",
    "Volume: 1.\n",
    "Volume: не число\n",
    "Volume:\n",
    "   \n",
    "",
])
def test_garbage_output_never_raises(garbage):
    """Сломанный звук не должен ронять агент."""
    state = parse_volume(garbage)
    assert state.volume is None or isinstance(state.volume, int)


def test_trailing_garbage_after_valid_number_is_ignored():
    assert parse_volume("Volume: 0.62.7\n").volume == 62


def test_state_survives_garbage_from_the_command(monkeypatch):
    """Даже если команда вернула мусор, чтение состояния не падает."""
    monkeypatch.setattr(WpctlAudio, "_run", lambda self, *args: "Volume: 1.2.3\n")
    assert WpctlAudio().state() == parse_volume("Volume: 1.2.3\n")


def test_no_digit_count_makes_parsing_raise():
    """Точечные значения дважды промахнулись мимо границы — метём весь диапазон."""
    for digits in range(1, 400):
        parse_volume("Volume: " + "9" * digits)
    for digits in (1_000, 10_000, 100_000):
        parse_volume("Volume: " + "9" * digits)


def test_implausible_level_is_reported_as_unknown():
    """Число из сотен цифр — не показание громкости, а мусор."""
    assert parse_volume("Volume: " + "9" * 50).volume is None
    assert parse_volume("Volume: 1000000").volume is None


def test_plausible_gain_is_still_reported():
    """Граница проверяется с обеих сторон: настоящее усиление обязано пройти."""
    assert parse_volume("Volume: 1.40").volume == 140
    assert parse_volume("Volume: 11.00").volume == 1100


def test_huge_fraction_does_not_raise():
    output = "Volume: " + "9" * 50_000 + "." + "9" * 50_000
    assert parse_volume(output).volume is None


def test_state_survives_every_dangerous_input(monkeypatch):
    """Ни один опасный вывод команды не должен ронять чтение состояния."""
    dangerous = [
        "Volume: " + "9" * 307,
        "Volume: " + "9" * 309,
        "Volume: .",
        "Volume: 1.2.3",
        "Volume:",
        "",
    ]
    for output in dangerous:
        def make_mock(result):
            return lambda self, *a: result
        monkeypatch.setattr(WpctlAudio, "_run", make_mock(output))
        # Ensure no exception is raised; result may be None or valid int
        WpctlAudio().state()
