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
