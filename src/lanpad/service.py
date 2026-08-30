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
    executable = shutil.which("lanpad")
    if executable is None:
        print("Команда lanpad не найдена в PATH.", file=sys.stderr)
        print("Установите пакет через `pipx install lanpad` и повторите.", file=sys.stderr)
        return 1

    target = unit_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(unit_text(executable))
    print(f"Юнит записан: {target}")

    for command in (
        ["systemctl", "--user", "daemon-reload"],
        ["systemctl", "--user", "enable", "--now", UNIT_NAME],
    ):
        result = subprocess.run(command, check=False)  # noqa: S603
        if result.returncode != 0:
            print(f"Команда не удалась: {' '.join(command)}", file=sys.stderr)
            return result.returncode

    print("Служба включена и запущена.")
    print(f"QR для телефона: journalctl --user -u {UNIT_NAME} -n 40")
    return 0
