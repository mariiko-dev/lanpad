import pytest

from lanpad.events import EventLog


def test_entries_come_back_newest_first():
    log = EventLog()
    log.add("info", "first")
    log.add("info", "second")
    assert [e["message"] for e in log.entries()] == ["second", "first"]


def test_entries_carry_kind_and_time():
    log = EventLog()
    log.add("error", "broke")
    entry = log.entries()[0]
    assert entry["kind"] == "error"
    assert isinstance(entry["at"], float)


def test_oldest_entries_are_dropped():
    log = EventLog(capacity=3)
    for i in range(10):
        log.add("info", str(i))
    assert [e["message"] for e in log.entries()] == ["9", "8", "7"]


def test_clear_empties_the_log():
    log = EventLog()
    log.add("info", "something")
    log.clear()
    assert log.entries() == []


@pytest.mark.parametrize("secret", ["yTZZry26fEos", "t=yTZZry26fEos"])
def test_a_token_never_reaches_the_log(secret):
    """The console shows this log; a token in it defeats the whole barrier."""
    log = EventLog()
    log.guard(secret)
    log.add("info", f"phone connected http://192.168.1.5:8477/?{secret}")
    assert secret not in log.entries()[0]["message"]


def test_redaction_keeps_the_rest_of_the_message():
    log = EventLog()
    log.add("info", "phone connected from 192.168.1.5 with t=abc123")
    message = log.entries()[0]["message"]
    assert "192.168.1.5" in message
    assert "abc123" not in message


def test_entries_are_a_copy():
    """A caller mutating the result must not corrupt the log."""
    log = EventLog()
    log.add("info", "something")
    log.entries().clear()
    assert len(log.entries()) == 1


@pytest.mark.parametrize("word", ["disconnected", "reconnecting", "unreachable"])
def test_ordinary_words_survive(word):
    """Matching by shape would eat these: they are token-length."""
    log = EventLog()
    log.guard("yTZZry26fEos")
    log.add("info", f"phone {word} from 192.168.1.5")
    assert word in log.entries()[0]["message"]


def test_a_guarded_token_is_stripped_even_bare():
    log = EventLog()
    log.guard("yTZZry26fEos")
    log.add("info", "token is yTZZry26fEos here")
    assert "yTZZry26fEos" not in log.entries()[0]["message"]


def test_a_token_in_a_query_is_stripped_without_being_guarded():
    """Defence in depth: a URL should be safe before guard() is called."""
    log = EventLog()
    log.add("info", "http://192.168.1.5:8477/?t=whatever")
    assert "whatever" not in log.entries()[0]["message"]
