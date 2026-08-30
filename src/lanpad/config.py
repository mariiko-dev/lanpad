"""Порт, пути и токен доступа.

Токен лежит в каталоге данных пользователя, а не рядом с исходниками:
в прототипе он лежал в каталоге проекта и рисковал попасть в репозиторий.
"""

import ipaddress
import os
import secrets
from pathlib import Path

DEFAULT_PORT = 8477
TOKEN_BYTES = 9


def data_dir() -> Path:
    """Каталог данных по XDG, создаётся при первом обращении."""
    base = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
    path = Path(base) / "lanpad"
    path.mkdir(parents=True, exist_ok=True)
    return path


def token_path() -> Path:
    return data_dir() / "token"


def _harden(path: Path) -> None:
    """Снять права у всех, кроме владельца.

    Вызывается и для существующего файла: он мог приехать из резервной
    копии или от прежней версии с правами, открытыми всей системе.
    """
    try:
        if path.stat().st_mode & 0o077:
            path.chmod(0o600)
    except OSError:
        pass


def _write_private(path: Path, content: str) -> None:
    """Создать файл сразу с правами 0600.

    Записать, а потом ужесточить — значит на мгновение оставить секрет
    доступным всем, поэтому права задаются в момент создания.
    """
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write(content)
    _harden(path)


def load_or_create_token(path: Path | None = None) -> str:
    """Прочитать токен, создав его при первом запуске.

    Ошибка чтения существующего файла намеренно не перехватывается:
    выписать новый токен вместо старого значит разом обесценить все
    спаренные телефоны, и человек не поймёт, почему всё перестало
    работать. Упасть громко здесь полезнее.
    """
    target = path or token_path()
    try:
        existing = target.read_text().strip()
    except FileNotFoundError:
        existing = ""
    else:
        if existing:
            _harden(target)
            return existing

    token = secrets.token_urlsafe(TOKEN_BYTES)
    target.parent.mkdir(parents=True, exist_ok=True)
    _write_private(target, token + "\n")
    return token


def token_matches(candidate: str, token: str) -> bool:
    """Сравнение, не зависящее от времени выполнения.

    Барьер обязан отказывать, а не падать: `compare_digest` бросает на
    строках с не-ASCII символами, а прислать такую строку может кто
    угодно.
    """
    if not isinstance(candidate, str) or not isinstance(token, str):
        return False
    if not candidate or not token:
        return False
    try:
        return secrets.compare_digest(candidate, token)
    except TypeError:
        return False


def is_private_client(host: str) -> bool:
    """Пускаем только из локальной сети и с самой машины."""
    if not isinstance(host, str):
        return False
    try:
        address = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return False
    return address.is_private or address.is_loopback or address.is_link_local


def port() -> int:
    raw = os.environ.get("LANPAD_PORT")
    if raw is None:
        return DEFAULT_PORT
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_PORT
    return value if 1 <= value <= 65535 else DEFAULT_PORT
