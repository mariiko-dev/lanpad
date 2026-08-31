import subprocess

import pytest

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


def test_missing_systemctl_is_explained_not_crashed(monkeypatch, capsys):
    """Стектрейс здесь означал бы, что человек не поймёт, что делать."""
    monkeypatch.setattr(service.shutil, "which", lambda name: "/usr/bin/lanpad"
                        if name == "lanpad" else None)
    assert service.install() == 1
    assert "systemctl" in capsys.readouterr().err


def test_missing_systemctl_leaves_nothing_behind(monkeypatch, tmp_path):
    """Юнит-файл без загрузки оставил бы систему наполовину установленной."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr(service.shutil, "which", lambda name: "/usr/bin/lanpad"
                        if name == "lanpad" else None)
    service.install()
    assert not service.unit_path().exists()


def test_missing_lanpad_command_is_explained(monkeypatch, capsys):
    monkeypatch.setattr(service.shutil, "which", lambda _name: None)
    assert service.install() == 1
    assert "lanpad" in capsys.readouterr().err


def test_failing_systemctl_returns_its_code(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr(service.shutil, "which", lambda _name: "/usr/bin/x")
    monkeypatch.setattr(
        service.subprocess, "run",
        lambda command, **kw: subprocess.CompletedProcess(command, 3),
    )
    assert service.install() == 3


def test_vanished_systemctl_does_not_crash(monkeypatch, tmp_path):
    """Команда могла исчезнуть между проверкой и запуском."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr(service.shutil, "which", lambda _name: "/usr/bin/x")

    def vanished(*args, **kwargs):
        raise FileNotFoundError("команда исчезла")

    monkeypatch.setattr(service.subprocess, "run", vanished)
    assert service.install() == 1


def test_successful_install_reports_success(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr(service.shutil, "which", lambda _name: "/usr/bin/x")
    monkeypatch.setattr(
        service.subprocess, "run",
        lambda command, **kw: subprocess.CompletedProcess(command, 0),
    )
    assert service.install() == 0
    assert service.unit_path().exists()
    assert "journalctl" in capsys.readouterr().out


def test_only_known_actions_are_accepted(monkeypatch):
    """An action list, not a command builder: this runs systemctl."""
    monkeypatch.setattr(service.shutil, "which", lambda _n: "/usr/bin/systemctl")
    ok, message = service.control("rm -rf /")
    assert ok is False
    assert "rm" not in message


@pytest.mark.parametrize("action", ["start", "stop", "restart", "enable", "disable"])
def test_known_actions_call_systemctl(monkeypatch, action):
    calls = []
    monkeypatch.setattr(service.shutil, "which", lambda _n: "/usr/bin/systemctl")
    monkeypatch.setattr(service.subprocess, "run",
                        lambda command, **kw: calls.append(command)
                        or subprocess.CompletedProcess(command, 0))
    ok, _ = service.control(action)
    assert ok is True
    assert calls[0][:3] == ["systemctl", "--user", action]


def test_control_reports_a_failure(monkeypatch):
    monkeypatch.setattr(service.shutil, "which", lambda _n: "/usr/bin/systemctl")
    monkeypatch.setattr(service.subprocess, "run",
                        lambda command, **kw: subprocess.CompletedProcess(command, 1, stderr="нет"))
    ok, _ = service.control("start")
    assert ok is False


def test_control_without_systemctl_explains_itself(monkeypatch):
    monkeypatch.setattr(service.shutil, "which", lambda _n: None)
    ok, message = service.control("start")
    assert ok is False
    assert "systemctl" in message


def test_control_survives_a_vanished_systemctl(monkeypatch):
    monkeypatch.setattr(service.shutil, "which", lambda _n: "/usr/bin/systemctl")

    def vanished(*args, **kwargs):
        raise FileNotFoundError("исчезла")

    monkeypatch.setattr(service.subprocess, "run", vanished)
    assert service.control("start")[0] is False


def test_status_reports_both_flags(monkeypatch):
    monkeypatch.setattr(service.shutil, "which", lambda _n: "/usr/bin/systemctl")
    monkeypatch.setattr(
        service.subprocess, "run",
        lambda command, **kw: subprocess.CompletedProcess(command, 0, stdout="active\n"),
    )
    assert service.status() == {"active": True, "enabled": True}


def test_status_without_systemctl_is_all_false(monkeypatch):
    monkeypatch.setattr(service.shutil, "which", lambda _n: None)
    assert service.status() == {"active": False, "enabled": False}
