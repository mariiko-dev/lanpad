import asyncio

import pytest

from lanpad.platform.linux import media_mpris as mm
from lanpad.platform.linux.media_mpris import (
    MprisMedia,
    art_id_for,
    metadata_to_state,
)


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


@pytest.mark.parametrize("length", [
    "abc", "355.0", None, [], {}, object(), float("nan"), float("inf"),
])
def test_broken_length_never_raises(length):
    """Плеер, нарушающий спецификацию, не должен убивать чтение состояния."""
    state = metadata_to_state({"mpris:length": length}, "Playing", 0, True)
    assert state.duration >= 0


def test_negative_length_is_reported_as_zero():
    state = metadata_to_state({"mpris:length": -5_000_000}, "Playing", 0, True)
    assert state.duration == 0.0


def test_broken_position_never_raises():
    state = metadata_to_state({}, "Playing", "не число", True)
    assert state.position == 0.0


@pytest.mark.parametrize("metadata", [
    {},
    {"xesam:title": 42},
    {"xesam:title": None},
    {"xesam:artist": []},
    {"xesam:artist": 7},
    {"mpris:artUrl": ""},
    {"mpris:artUrl": 42},
    {"mpris:artUrl": "file://"},
    {"xesam:title": 1, "xesam:artist": None, "mpris:length": "x", "mpris:artUrl": []},
])
def test_no_metadata_shape_raises(metadata):
    """Ни одна форма метаданных не должна приводить к исключению."""
    metadata_to_state(metadata, "Playing", 0, True)


def media_without_thread() -> MprisMedia:
    """Собрать бэкенд, не поднимая поток D-Bus."""
    backend = MprisMedia.__new__(MprisMedia)
    backend._state = None
    backend._subscribers = []
    return backend


def test_one_broken_subscriber_does_not_starve_the_others():
    backend = media_without_thread()
    seen = []
    backend.subscribe(lambda _s: (_ for _ in ()).throw(RuntimeError("сломался")))
    backend.subscribe(seen.append)
    backend._publish()
    assert len(seen) == 1


def test_broken_subscriber_does_not_propagate():
    backend = media_without_thread()
    backend.subscribe(lambda _s: (_ for _ in ()).throw(RuntimeError("сломался")))
    backend._publish()


def test_departing_player_resets_state_and_notifies():
    """Служба стартует раньше плееров: уход текущего обязан обнулить состояние.

    Без D-Bus: `_bus` — None, поэтому `_attach_any` сразу возвращается.
    """
    backend = media_without_thread()
    backend._stopping = False
    backend._bus = None
    backend._player = object()
    backend._player_name = "org.mpris.MediaPlayer2.vlc"
    backend._state = metadata_to_state(meta(), "Playing", 0, True)
    seen = []
    backend.subscribe(seen.append)

    asyncio.run(backend._players_changed("org.mpris.MediaPlayer2.vlc", ""))

    assert backend._state is None
    assert backend._player is None
    assert backend._player_name is None
    assert seen == [None]


def test_unrelated_player_leaving_is_ignored():
    backend = media_without_thread()
    backend._stopping = False
    backend._bus = None
    backend._player = object()
    backend._player_name = "org.mpris.MediaPlayer2.vlc"
    backend._state = metadata_to_state(meta(), "Playing", 0, True)

    asyncio.run(backend._players_changed("org.mpris.MediaPlayer2.other", ""))

    assert backend._state is not None
    assert backend._player_name == "org.mpris.MediaPlayer2.vlc"


def test_art_paths_are_evicted_once_the_cap_is_passed():
    mm._ART_PATHS.clear()
    for i in range(mm.MAX_ART_ENTRIES + 5):
        mm._remember_art(f"id{i}", f"/covers/{i}.png")
    assert len(mm._ART_PATHS) == mm.MAX_ART_ENTRIES
    assert "id0" not in mm._ART_PATHS
    assert f"id{mm.MAX_ART_ENTRIES + 4}" in mm._ART_PATHS
