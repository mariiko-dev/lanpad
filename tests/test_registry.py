import pytest

from lanpad.platform import registry
from lanpad.platform.fake import FakeInput
from lanpad.platform.linux.media_mpris import MprisMedia


@pytest.fixture(autouse=True)
def no_live_dbus(monkeypatch):
    """Реестр не должен поднимать настоящую шину D-Bus в тестах.

    Без этого `build_backends` конструирует MprisMedia, тот заводит поток,
    ждёт до пяти секунд и уходит на живую сессионную шину — а её в CI нет.
    """
    monkeypatch.setattr(MprisMedia, "is_available", staticmethod(lambda: False))


def test_builds_backends_with_given_input():
    backends = registry.build_backends(input_backend=FakeInput())
    assert isinstance(backends.input, FakeInput)


def test_capabilities_match_assembled_backends():
    backends = registry.build_backends(input_backend=FakeInput())
    caps = backends.capabilities()
    assert caps.audio == (backends.audio is not None)
    assert caps.media == (backends.media is not None)
    assert caps.clipboard == (backends.clipboard is not None)


def test_unavailable_media_is_reported_as_absent():
    backends = registry.build_backends(input_backend=FakeInput())
    assert backends.media is None
    assert backends.capabilities().media is False


def test_missing_optional_backend_does_not_break_assembly(monkeypatch):
    """Нет wpctl — нет громкости, но агент обязан подняться."""
    from lanpad.platform.linux.audio_wpctl import WpctlAudio

    monkeypatch.setattr(WpctlAudio, "is_available", staticmethod(lambda: False))
    backends = registry.build_backends(input_backend=FakeInput())
    assert backends.audio is None
    assert backends.capabilities().audio is False
