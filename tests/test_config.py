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


@pytest.mark.parametrize("host", [
    "8.8.8.8",
    "1.1.1.1",
    "93.184.216.34",
    "2001:4860:4860::8888",
    "2606:4700:4700::1111",
])
def test_public_clients_are_refused(host):
    assert config.is_private_client(host) is False


@pytest.mark.parametrize("host", ["203.0.113.10", "198.51.100.5", "192.0.2.7"])
def test_documentation_ranges_count_as_private(host):
    """Диапазоны из RFC 5737 зарезервированы под примеры и не маршрутизируются.

    Python относит их к приватным по реестру IANA. Выглядят они как
    публичные, поэтому легко принять отказ за ошибку и «починить» его.
    """
    assert config.is_private_client(host) is True


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


@pytest.mark.parametrize("candidate", [
    "токен", "tokén", "🔑", 123, None, b"token", ["token"],
])
def test_token_comparison_refuses_instead_of_raising(candidate):
    """Барьер обязан отказывать, а не падать от присланного мусора."""
    assert config.token_matches(candidate, "token") is False


def test_token_comparison_survives_non_ascii_stored_token():
    assert config.token_matches("token", "токен") is False


def test_existing_token_file_permissions_are_hardened(tmp_path):
    """Файл мог приехать из резервной копии с правами, открытыми всем."""
    token_file = tmp_path / "token"
    token_file.write_text("существующий\n")
    token_file.chmod(0o644)
    assert config.load_or_create_token(token_file) == "существующий"
    assert token_file.stat().st_mode & 0o077 == 0


def test_created_token_file_is_private_from_the_start(tmp_path):
    token_file = tmp_path / "token"
    config.load_or_create_token(token_file)
    assert token_file.stat().st_mode & 0o077 == 0


def test_unreadable_token_file_raises_instead_of_regenerating(tmp_path):
    """Тихая перегенерация обесценила бы все спаренные телефоны."""
    token_file = tmp_path / "token"
    token_file.write_text("важный\n")
    token_file.chmod(0o200)
    with pytest.raises(OSError):
        config.load_or_create_token(token_file)
    token_file.chmod(0o600)
    assert token_file.read_text().strip() == "важный"


@pytest.mark.parametrize("host", [None, 123, b"127.0.0.1", ["127.0.0.1"]])
def test_non_string_host_is_refused(host):
    assert config.is_private_client(host) is False
