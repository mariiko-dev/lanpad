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


@pytest.mark.parametrize("literal", ["NaN", "Infinity", "-Infinity"])
def test_json_constants_are_rejected(literal):
    assert p.parse_events(f'[["m", {literal}, 0]]') == []


@pytest.mark.parametrize("event", ["m", "w", "vol", "volset"])
def test_overflowing_float_is_rejected_for_every_numeric_event(event):
    payload = f'[["{event}", 1e999, 0]]' if event == "m" else f'[["{event}", 1e999]]'
    assert p.parse_events(payload) == []


def test_bad_number_does_not_destroy_the_rest_of_the_batch():
    """Один негодный элемент не должен уносить весь пакет."""
    events = p.parse_events('[["m",1,1],["m",1e999,0],["w",5]]')
    assert events == [p.Move(1, 1), p.Wheel(5)]


def test_nan_inside_batch_does_not_destroy_the_rest():
    events = p.parse_events('[["w",1],["vol",NaN],["w",2]]')
    assert events == [p.Wheel(1), p.Wheel(2)]
