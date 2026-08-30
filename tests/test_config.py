import pytest

from lanpad import config


def test_creates_token_when_absent(tmp_path):
    token_file = tmp_path / "token"
    token = config.load_or_create_token(token_file)
    assert token
    assert token_file.read_text().strip() == token


def test_reuses_existing_token(tmp_path):
    token_file = tmp_path / "token"
    first = config.load_or_create_token(token_file)
    assert config.load_or_create_token(token_file) == first


def test_token_file_is_not_world_readable(tmp_path):
    token_file = tmp_path / "token"
    config.load_or_create_token(token_file)
    assert token_file.stat().st_mode & 0o077 == 0


def test_blank_token_file_is_regenerated(tmp_path):
    token_file = tmp_path / "token"
    token_file.write_text("   \n")
    assert config.load_or_create_token(token_file).strip()


def test_token_comparison_accepts_match():
    assert config.token_matches("secret", "secret") is True


def test_token_comparison_rejects_mismatch():
    assert config.token_matches("wrong", "secret") is False


def test_token_comparison_rejects_empty():
    assert config.token_matches("", "secret") is False


@pytest.mark.parametrize("host", [
    "127.0.0.1", "192.168.1.50", "10.0.0.7", "172.16.3.9", "::1", "fe80::1",
])
def test_private_and_loopback_clients_are_allowed(host):
    assert config.is_private_client(host) is True


@pytest.mark.parametrize("host", ["8.8.8.8", "203.0.113.10", "2001:4860:4860::8888"])
def test_public_clients_are_refused(host):
    assert config.is_private_client(host) is False


def test_garbage_host_is_refused():
    assert config.is_private_client("не адрес") is False


def test_port_defaults(monkeypatch):
    monkeypatch.delenv("LANPAD_PORT", raising=False)
    assert config.port() == config.DEFAULT_PORT


def test_port_reads_environment(monkeypatch):
    monkeypatch.setenv("LANPAD_PORT", "9000")
    assert config.port() == 9000


def test_invalid_port_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("LANPAD_PORT", "не число")
    assert config.port() == config.DEFAULT_PORT
