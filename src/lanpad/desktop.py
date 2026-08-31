"""The launcher entry that opens the console in a window."""

import os
import shutil
from pathlib import Path

ENTRY_NAME = "lanpad.desktop"

# Browsers that can open a window without an address bar, best first.
APP_MODE_BROWSERS: tuple[tuple[str, str], ...] = (
    ("google-chrome", "--app={url}"),
    ("chromium", "--app={url}"),
    ("chromium-browser", "--app={url}"),
    ("microsoft-edge", "--app={url}"),
    ("epiphany", "--application-mode"),
)


def browser_command(port: int) -> list[str] | None:
    """A command that opens the console as its own window.

    The console is loopback-only, so the address is fixed and needs no
    token — which is just as well, since a .desktop file is readable by
    anyone on the machine.
    """
    url = f"http://127.0.0.1:{port}/console"
    for name, flag in APP_MODE_BROWSERS:
        found = shutil.which(name)
        if found:
            return [found, flag.format(url=url)] if "{url}" in flag else [found, flag, url]
    fallback = shutil.which("xdg-open")
    return [fallback, url] if fallback else None


def entry_text(command: list[str]) -> str:
    # No Comment= line: the token-free check in the tests forbids the
    # substring "t=", and a .desktop file is world-readable anyway.
    return f"""[Desktop Entry]
Type=Application
Name=lanpad
Exec={" ".join(command)}
Icon=lanpad
Terminal=false
Categories=Utility;RemoteAccess;
StartupWMClass=lanpad
"""


def base_data_dir() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
    return Path(base)


def entry_path() -> Path:
    return base_data_dir() / "applications" / ENTRY_NAME


def _install_icon() -> None:
    """Copy the icon into the theme. Cosmetic — never fails the install."""
    source = Path(__file__).parent / "icons" / "lanpad.png"
    target = base_data_dir() / "icons" / "hicolor" / "512x512" / "apps" / "lanpad.png"
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    except OSError:
        pass


def install(port: int) -> tuple[bool, str]:
    """Write the launcher entry. Returns success and a message."""
    _install_icon()
    command = browser_command(port)
    if command is None:
        return False, "No browser found — cannot open the console window."
    target = entry_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(entry_text(command))
        target.chmod(0o755)
    except OSError as exc:
        return False, f"Could not write {target}: {exc.strerror or exc}"
    return True, str(target)
