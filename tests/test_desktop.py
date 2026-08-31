from lanpad import desktop


def test_prefers_a_browser_with_app_mode(monkeypatch):
    """App mode gives a window without an address bar — a real app."""
    monkeypatch.setattr(desktop.shutil, "which",
                        lambda name: "/usr/bin/google-chrome" if name == "google-chrome" else None)
    command = desktop.browser_command(8477)
    assert command is not None
    assert any(part.startswith("--app=http://127.0.0.1:8477/console") for part in command)


def test_falls_back_to_the_next_browser(monkeypatch):
    monkeypatch.setattr(desktop.shutil, "which",
                        lambda name: "/usr/bin/epiphany" if name == "epiphany" else None)
    assert desktop.browser_command(8477) is not None


def test_without_any_browser_there_is_no_command(monkeypatch):
    monkeypatch.setattr(desktop.shutil, "which", lambda _name: None)
    assert desktop.browser_command(8477) is None


def test_entry_is_a_valid_desktop_file():
    text = desktop.entry_text(["/usr/bin/google-chrome", "--app=http://127.0.0.1:8477/console"])
    assert text.startswith("[Desktop Entry]")
    assert "Type=Application" in text
    assert "Exec=/usr/bin/google-chrome" in text
    assert "Icon=lanpad" in text


def test_entry_never_carries_a_token():
    """A .desktop file is world-readable, and the console needs no token."""
    text = desktop.entry_text(["/usr/bin/x", "--app=http://127.0.0.1:8477/console"])
    assert "?t=" not in text
    assert "&t=" not in text
    assert "yTZZry26fEos" not in text


def test_entry_describes_itself():
    """Without a comment the launcher shows a bare name and no hint."""
    text = desktop.entry_text(["/usr/bin/x", "--app=http://127.0.0.1:8477/console"])
    assert "Comment=" in text


def test_entry_path_follows_xdg(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert desktop.entry_path() == tmp_path / "applications" / "lanpad.desktop"


def test_install_writes_the_entry(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setattr(desktop.shutil, "which",
                        lambda name: "/usr/bin/google-chrome" if name == "google-chrome" else None)
    ok, _ = desktop.install(8477)
    assert ok is True
    assert desktop.entry_path().exists()


def test_install_without_a_browser_explains_itself(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setattr(desktop.shutil, "which", lambda _name: None)
    ok, message = desktop.install(8477)
    assert ok is False
    assert "browser" in message.lower()
    assert not desktop.entry_path().exists()
