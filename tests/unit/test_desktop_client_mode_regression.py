import sys
import types

import desktop_launcher


def test_desktop_mode_defaults_to_client(monkeypatch, tmp_path):
    monkeypatch.delenv("JZ_DESKTOP_MODE", raising=False)
    monkeypatch.setenv("DESKTOP_CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(desktop_launcher, "_bundle_path", lambda relative: str(tmp_path / "missing.json"))

    assert desktop_launcher.read_desktop_mode() == "client"


def test_desktop_mode_env_overrides_config(monkeypatch, tmp_path):
    (tmp_path / "config.json").write_text('{"desktop": {"mode": "client"}}', encoding="utf-8")
    monkeypatch.setenv("DESKTOP_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("JZ_DESKTOP_MODE", "browser")

    assert desktop_launcher.read_desktop_mode() == "browser"


def test_desktop_mode_reads_user_config(monkeypatch, tmp_path):
    (tmp_path / "config.json").write_text('{"desktop": {"mode": "browser"}}', encoding="utf-8")
    monkeypatch.delenv("JZ_DESKTOP_MODE", raising=False)
    monkeypatch.setenv("DESKTOP_CONFIG_DIR", str(tmp_path))

    assert desktop_launcher.read_desktop_mode() == "browser"


def test_client_window_returns_false_when_pywebview_is_missing(monkeypatch):
    monkeypatch.setitem(sys.modules, "webview", None)

    assert desktop_launcher._run_client_window("http://127.0.0.1:8000") is False


def test_client_window_uses_pywebview_create_window(monkeypatch):
    calls = {}

    def fake_create_window(title, url, **kwargs):
        calls["title"] = title
        calls["url"] = url
        calls["kwargs"] = kwargs

    fake_webview = types.SimpleNamespace(
        create_window=fake_create_window,
        start=lambda **kwargs: calls.setdefault("start_kwargs", kwargs),
    )
    monkeypatch.setitem(sys.modules, "webview", fake_webview)
    monkeypatch.setattr(desktop_launcher, "_desktop_icon_path", lambda: "/tmp/jz-logo.png")

    assert desktop_launcher._run_client_window("http://127.0.0.1:8765") is True
    assert calls["title"] == "金策智算"
    assert calls["url"] == "http://127.0.0.1:8765"
    assert calls["kwargs"]["width"] == 1440
    assert calls["kwargs"]["height"] == 900
    assert calls["kwargs"]["min_size"] == (1180, 720)
    assert calls["kwargs"]["background_color"] == "#f6fbf8"
    assert calls["start_kwargs"]["icon"] == "/tmp/jz-logo.png"


def test_desktop_launcher_contains_browser_fallback_path():
    source = desktop_launcher.__loader__.get_source(desktop_launcher.__name__)

    assert "open_browser_on_ready=False" in source
    assert "Falling back to browser display mode" in source
    assert "open_browser_on_ready=True" in source
