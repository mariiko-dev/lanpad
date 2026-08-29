from lanpad import protocol as p
from lanpad.platform.base import Backends
from lanpad.platform.fake import FakeAudio, FakeClipboard, FakeInput, FakeMedia


def test_fake_input_records_calls():
    fake = FakeInput()
    fake.move(3, 4)
    fake.click("l")
    assert fake.calls == [("move", 3, 4), ("click", "l")]


def test_ascii_text_can_be_typed_directly():
    assert FakeInput().can_type("hello") is True


def test_cyrillic_text_cannot_be_typed_directly():
    assert FakeInput().can_type("привет") is False


def test_fake_audio_tracks_volume():
    fake = FakeAudio()
    fake.set_percent(40)
    assert fake.state() == p.AudioState(volume=40, muted=False)
    fake.toggle_mute()
    assert fake.state().muted is True


def test_fake_audio_step_clamps():
    fake = FakeAudio()
    fake.set_percent(95)
    fake.step(20)
    assert fake.state().volume == 100


def test_fake_media_notifies_subscriber_on_command():
    fake = FakeMedia()
    seen = []
    fake.subscribe(seen.append)
    fake.command("play")
    assert len(seen) == 1
    assert isinstance(seen[0], p.MediaState)


def test_capabilities_reflect_present_backends():
    full = Backends(FakeInput(), FakeAudio(), FakeMedia(), FakeClipboard())
    assert full.capabilities() == p.Capabilities(audio=True, media=True, clipboard=True)


def test_capabilities_report_missing_backends():
    bare = Backends(FakeInput(), None, None, None)
    assert bare.capabilities() == p.Capabilities(audio=False, media=False, clipboard=False)
