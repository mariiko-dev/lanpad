import pytest

from lanpad import http as h


def test_manifest_is_standalone_and_carries_token():
    manifest = h.manifest("abc123")
    assert manifest["display"] == "standalone"
    assert manifest["start_url"] == "/?t=abc123"
    assert manifest["name"] == "lanpad"


def test_manifest_lists_icons():
    icons = h.manifest("t")["icons"]
    assert any(icon["sizes"] == "512x512" for icon in icons)


def test_origin_matching_host_is_allowed():
    assert h.origin_allowed("http://192.168.1.50:8477", "192.168.1.50:8477") is True


def test_absent_origin_is_allowed():
    """Не браузер — не подделка межсайтового запроса."""
    assert h.origin_allowed(None, "192.168.1.50:8477") is True


def test_foreign_origin_is_refused():
    assert h.origin_allowed("https://зло.example", "192.168.1.50:8477") is False


def test_origin_with_different_port_is_refused():
    assert h.origin_allowed("http://192.168.1.50:9999", "192.168.1.50:8477") is False


def test_static_path_inside_root_is_resolved(tmp_path):
    (tmp_path / "assets").mkdir()
    target = tmp_path / "assets" / "app.js"
    target.write_text("x")
    assert h.safe_static_path(tmp_path, "/assets/app.js") == target


def test_static_path_escaping_root_is_refused(tmp_path):
    assert h.safe_static_path(tmp_path, "/../../etc/passwd") is None


def test_static_path_with_encoded_traversal_is_refused(tmp_path):
    assert h.safe_static_path(tmp_path, "/assets/../../etc/passwd") is None


def test_missing_static_file_is_refused(tmp_path):
    assert h.safe_static_path(tmp_path, "/нет-такого.js") is None


@pytest.mark.parametrize("path,expected_immutable", [
    ("/assets/app-a1b2c3.js", True),
    ("/assets/font.woff2", True),
    ("/index.html", False),
    ("/manifest.webmanifest", False),
])
def test_cache_headers(path, expected_immutable):
    header = h.cache_header_for(path)
    assert ("immutable" in header) is expected_immutable
