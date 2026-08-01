"""Web 终端登录认证（系统用户密码 PAM/su + token）测试。"""
import json
import sys
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server


def _make_server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.FlashAPIHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd


def test_pam_wrong_password_false():
    assert server.pam_authenticate("nobody", "wrong-pass-xyz") is False


def test_pam_empty_password_false():
    assert server.pam_authenticate("nobody", "") is False


def test_pam_missing_user_false():
    assert server.pam_authenticate("no_such_user_zzz", "x") is False


def test_su_wrong_password_false():
    assert server.su_authenticate("nobody", "wrong-pass-xyz") is False


def test_verify_wrong_password_false():
    assert server.verify_system_password("nobody", "wrong-pass-xyz") is False


def test_shadow_crypt_verify(monkeypatch):
    import crypt

    h = crypt.crypt("secret123", crypt.mksalt(crypt.METHOD_SHA512))
    assert server._crypt_password("secret123", h) == h
    assert server._crypt_password("wrong", h) != h


def test_shadow_locked_hash_false(monkeypatch):
    _real_open = open

    def fake_open(path, *a, **k):
        if path == "/etc/shadow":
            return _real_open("/dev/null", "r")
        return _real_open(path, *a, **k)

    monkeypatch.setattr("builtins.open", fake_open)
    assert server.shadow_authenticate("locked", "x") is False


def test_shadow_unknown_user_false(monkeypatch):
    assert server.shadow_authenticate("ghost_user_zzz", "x") is False


def test_shadow_unreadable_none(monkeypatch):
    def fake_open(path, *a, **k):
        raise PermissionError("denied")

    monkeypatch.setattr("builtins.open", fake_open)
    assert server.shadow_authenticate("root", "x") is None


def test_token_issue_check_ok():
    token = server._issue_terminal_token("alice")
    assert len(token) >= 32
    assert server._check_terminal_token(token) == "alice"


def test_token_bogus_none():
    assert server._check_terminal_token("bogus") is None
    assert server._check_terminal_token(None) is None
    assert server._check_terminal_token("") is None


def test_token_expiry():
    token = server._issue_terminal_token("alice")
    with server.TERMINAL_TOKENS_LOCK:
        server.TERMINAL_TOKENS[token] = ("alice", time.time() - 1)
    assert server._check_terminal_token(token) is None
    assert token not in server.TERMINAL_TOKENS


def test_login_rate_limit():
    with server.LOGIN_LOCK:
        server.LOGIN_ATTEMPTS.clear()
    first = server._login_record("bob", success=False)
    assert first == 0.0
    second = server._login_record("bob", success=False)
    assert second == server.LOGIN_BASE_DELAY
    assert server._login_blocked("bob") is False
    with server.LOGIN_LOCK:
        server.LOGIN_ATTEMPTS["bob"] = {"count": 30, "last": time.time()}
    assert server._login_blocked("bob") is True
    assert server._login_record("bob", success=True) == 0.0
    assert "bob" not in server.LOGIN_ATTEMPTS


def test_auth_endpoint_requires_username_password():
    httpd = _make_server()
    try:
        import urllib.request

        req = urllib.request.Request(
            f"http://127.0.0.1:{httpd.server_address[1]}/api/terminal/auth",
            data=json.dumps({}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=5)
        except urllib.error.HTTPError as e:
            assert e.code == 400
        else:
            raise AssertionError("expected 400")
    finally:
        httpd.shutdown()


def test_status_endpoint_shapes():
    httpd = _make_server()
    try:
        import urllib.request

        token = server._issue_terminal_token("carol")
        url = (
            f"http://127.0.0.1:{httpd.server_address[1]}/api/terminal/status"
            + "?" + urlencode({"token": token})
        )
        with urllib.request.urlopen(url, timeout=5) as r:
            data = json.loads(r.read().decode())
            assert data["enabled"] is True
            assert data["authenticated"] is True
    finally:
        httpd.shutdown()
