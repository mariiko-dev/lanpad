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


class Boom(Exception):
    """Отдельный тип, чтобы не спутать с настоящей ошибкой в тесте."""


def test_failing_event_does_not_abort_the_rest_of_the_batch():
    session, backends, _ = make_session()
    backends.audio.set_percent = lambda _p: (_ for _ in ()).throw(Boom())
    session.handle([p.Move(1, 1), p.VolumeSet(50), p.Click("l")])
    assert ("click", "l") in backends.input.calls


def test_button_release_survives_a_failure_earlier_in_the_batch():
    """Иначе кнопка мыши останется зажатой после перетаскивания."""
    session, backends, _ = make_session()
    backends.audio.set_percent = lambda _p: (_ for _ in ()).throw(Boom())
    session.handle([p.Button("l", True), p.VolumeSet(50), p.Button("l", False)])
    assert ("button", "l", False) in backends.input.calls


def test_failing_event_does_not_propagate():
    session, backends, _ = make_session()
    backends.input.move = lambda _dx, _dy: (_ for _ in ()).throw(Boom())
    session.handle([p.Move(1, 1)])


def test_broken_listener_does_not_break_input_handling():
    session, backends, _ = make_session()
    session.add_listener(lambda _s: (_ for _ in ()).throw(Boom()))
    session.handle([p.VolumeSet(40), p.Click("l")])
    assert ("click", "l") in backends.input.calls


def test_broken_listener_does_not_propagate_from_media_subscription():
    """Исключение отсюда ушло бы в диспетчер сигналов D-Bus и убило подписку."""
    session, backends, _ = make_session()
    session.add_listener(lambda _s: (_ for _ in ()).throw(Boom()))
    backends.media.command("play")


def test_failing_state_collection_does_not_propagate():
    session, backends, _ = make_session()
    backends.audio.state = lambda: (_ for _ in ()).throw(Boom())
    session.handle([p.VolumeSet(40)])


def test_state_reaches_every_listener():
    """Телефонов в сети бывает больше одного."""
    session, _, _ = make_session()
    first, second = [], []
    session.add_listener(first.append)
    session.add_listener(second.append)
    session.handle([p.VolumeSet(30)])
    assert len(first) == 1
    assert len(second) == 1


def test_removed_listener_stops_receiving():
    session, _, _ = make_session()
    seen = []
    session.add_listener(seen.append)
    session.remove_listener(seen.append)
    session.handle([p.VolumeSet(30)])
    assert seen == []


def test_removing_an_unknown_listener_is_harmless():
    session, _, _ = make_session()
    session.remove_listener(lambda _s: None)


def test_every_event_type_reaches_its_backend():
    """Пропущенная ветка в match молча проглотила бы события."""
    session, backends, _ = make_session()
    session.handle([
        p.Wheel(3),
        p.Button("m", True),
        p.Button("m", False),
        p.Tap("escape"),
        p.KeyHold("ctrl", True),
        p.KeyHold("ctrl", False),
        p.Combo(["ctrl", "c"]),
        p.VolumeStep(-5),
        p.VolumeMuteToggle(),
    ])
    assert ("wheel", 3) in backends.input.calls
    assert ("button", "m", True) in backends.input.calls
    assert ("button", "m", False) in backends.input.calls
    assert ("tap", "escape") in backends.input.calls
    assert ("key_hold", "ctrl", True) in backends.input.calls
    assert ("key_hold", "ctrl", False) in backends.input.calls
    assert ("combo", ["ctrl", "c"]) in backends.input.calls
    assert ("step", -5) in backends.audio.calls
    assert ("toggle_mute",) in backends.audio.calls
