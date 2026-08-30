from lanpad import service


def test_unit_runs_given_executable():
    text = service.unit_text("/usr/bin/lanpad")
    assert "ExecStart=/usr/bin/lanpad" in text


def test_unit_is_tied_to_graphical_session():
    text = service.unit_text("/usr/bin/lanpad")
    assert "After=graphical-session.target" in text
    assert "PartOf=graphical-session.target" in text


def test_unit_restarts_on_failure():
    assert "Restart=on-failure" in service.unit_text("/usr/bin/lanpad")


def test_unit_is_wanted_by_default_target():
    assert "WantedBy=default.target" in service.unit_text("/usr/bin/lanpad")


def test_unit_does_not_mention_prototype_name():
    assert "remote-touchpad" not in service.unit_text("/usr/bin/lanpad")


def test_unit_path_is_in_user_systemd_directory():
    assert service.unit_path().as_posix().endswith("systemd/user/lanpad.service")


def test_unit_path_follows_xdg_config_home(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert service.unit_path() == tmp_path / "systemd" / "user" / "lanpad.service"
