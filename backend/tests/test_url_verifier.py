from app.services.url_verifier import is_safe_http_url


def test_public_https_urls_are_allowed():
    assert is_safe_http_url("https://example.com/project")
    assert is_safe_http_url("http://github.com/example/repo")
    assert is_safe_http_url("https://8.8.8.8/status")


def test_non_http_and_private_targets_are_blocked():
    assert is_safe_http_url("javascript:alert(1)") is False
    assert is_safe_http_url("ftp://example.com/file") is False
    assert is_safe_http_url("file:///etc/passwd") is False
    assert is_safe_http_url("http://localhost:5432") is False
    assert is_safe_http_url("http://127.0.0.1") is False
    assert is_safe_http_url("http://10.0.0.5/internal") is False
    assert is_safe_http_url("http://192.168.1.1/admin") is False
    assert is_safe_http_url("http://169.254.169.254/latest/meta-data") is False
    assert is_safe_http_url("http://[::1]/") is False
    assert is_safe_http_url("http://service.local/") is False


def test_credentials_in_url_are_rejected():
    assert is_safe_http_url("https://user:password@example.com/path") is False
    assert is_safe_http_url("") is False
    assert is_safe_http_url(None) is False
