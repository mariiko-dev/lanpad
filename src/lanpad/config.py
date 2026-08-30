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


def load_or_create_token(path: Path | None = None) -> str:
    """Прочитать токен, создав его при первом запуске."""
    target = path or token_path()
    try:
        existing = target.read_text().strip()
        if existing:
            return existing
    except (FileNotFoundError, OSError):
        pass

    token = secrets.token_urlsafe(TOKEN_BYTES)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(token + "\n")
    target.chmod(0o600)
    return token


def token_matches(candidate: str, token: str) -> bool:
    """Сравнение, не зависящее от времени выполнения."""
    if not candidate or not token:
        return False
    return secrets.compare_digest(candidate, token)


def is_private_client(host: str) -> bool:
    """Пускаем только из локальной сети и с самой машины."""
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
