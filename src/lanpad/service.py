"""Установка автозапуска через systemd --user."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

UNIT_NAME = "lanpad.service"


def unit_text(executable: str) -> str:
    return f"""[Unit]
Description=lanpad — телефон как тачпад и пульт
After=graphical-session.target
PartOf=graphical-session.target
StartLimitIntervalSec=0

[Service]
Type=simple
ExecStart={executable}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
"""


def unit_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")
    return Path(base) / "systemd" / "user" / UNIT_NAME


def install() -> int:
    """Записать юнит и включить службу.

    Проверки идут до записи намеренно: файл, который некому загрузить,
    оставляет систему наполовину установленной, и повторный запуск не
    даёт никакой новой информации.
    """
    executable = shutil.which("lanpad")
    if executable is None:
        print("Команда lanpad не найдена в PATH.", file=sys.stderr)
        print("Установите пакет через `pipx install lanpad` и повторите.", file=sys.stderr)
        return 1

    if shutil.which("systemctl") is None:
        print("Команда systemctl не найдена — автозапуск настроить нечем.", file=sys.stderr)
        print("Эта машина, судя по всему, без systemd. Запускайте агент вручную:", file=sys.stderr)
        print("    lanpad", file=sys.stderr)
        return 1

    target = unit_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(unit_text(executable))
    except OSError as exc:
        print(f"Не удалось записать {target}: {exc.strerror or exc}", file=sys.stderr)
        return 1
    print(f"Юнит записан: {target}")

    for command in (
        ["systemctl", "--user", "daemon-reload"],
        ["systemctl", "--user", "enable", "--now", UNIT_NAME],
    ):
        try:
            result = subprocess.run(command, check=False)
        except OSError as exc:
            print(f"Не удалось выполнить {' '.join(command)}: {exc}", file=sys.stderr)
            return 1
        if result.returncode != 0:
            print(f"Команда не удалась: {' '.join(command)}", file=sys.stderr)
            return result.returncode

    print("Служба включена и запущена.")
    print(f"QR для телефона: journalctl --user -u {UNIT_NAME} -n 40")
    return 0


# An allow-list, not a command builder: this runs systemctl, and the
# request comes from a web page.
ACTIONS = frozenset({"start", "stop", "restart", "enable", "disable"})


def control(action: str) -> tuple[bool, str]:
    """Run one known systemctl action. Returns success and a message."""
    if not isinstance(action, str) or action not in ACTIONS:
        return False, "unknown action"
    if shutil.which("systemctl") is None:
        return False, "systemctl not found — this machine has no systemd"
    command = ["systemctl", "--user", action, UNIT_NAME]
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=10, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    if result.returncode != 0:
        return False, (result.stderr or "").strip() or f"exit {result.returncode}"
    return True, ""


def _query(argument: str) -> bool:
    try:
        result = subprocess.run(
            ["systemctl", "--user", argument, UNIT_NAME],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except Exception:
        # A status query must never take down /console/state; any failure
        # to reach systemctl just means "not known to be active".
        return False
    return result.stdout.strip() in ("active", "enabled")


def status() -> dict:
    """Whether the service runs now and whether it starts at login."""
    if shutil.which("systemctl") is None:
        return {"active": False, "enabled": False}
    return {"active": _query("is-active"), "enabled": _query("is-enabled")}
