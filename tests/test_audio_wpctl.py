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


@pytest.mark.parametrize("digits", [310, 400, 5000])
def test_absurdly_long_number_does_not_raise(digits):
    """float() отдаёт бесконечность молча, а round() на ней падает."""
    assert parse_volume("Volume: " + "9" * digits).volume is None


def test_absurdly_long_fraction_does_not_raise():
    output = "Volume: " + "1" * 50_000 + "." + "2" * 50_000
    assert parse_volume(output).volume is None


def test_long_but_finite_number_is_still_parsed():
    """Граница проверяется с обеих сторон: конечное число обязано разобраться."""
    assert parse_volume("Volume: " + "9" * 300).volume is not None
