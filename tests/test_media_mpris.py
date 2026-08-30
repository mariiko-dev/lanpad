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
    state = metadata_to_state(
        meta(**{"xesam:artist": ["Queen", "David Bowie"]}), "Playing", 0, True
    )
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
    state = metadata_to_state(
        meta(**{"mpris:artUrl": "file:///home/u/cover.png"}), "Playing", 0, True
    )
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
