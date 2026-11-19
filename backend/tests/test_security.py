import pytest

from app.core.security import (
    compute_sha256,
    create_access_token,
    decode_access_token,
    get_password_hash,
    is_valid_sha256,
    verify_password,
)


def test_password_hash_roundtrip():
    hashed = get_password_hash("correct horse battery staple")
    assert hashed.startswith("$2")
    assert verify_password("correct horse battery staple", hashed) is True
    assert verify_password("wrong password", hashed) is False
    assert verify_password("", hashed) is False


def test_malformed_hash_never_raises():
    assert verify_password("anything", "not-a-bcrypt-hash") is False
    assert verify_password("anything", None) is False


def test_password_over_bcrypt_limit_is_rejected():
    with pytest.raises(ValueError):
        get_password_hash("a" * 73)


def test_jwt_roundtrip_and_tamper_detection():
    subject = "8b9e6120-d38a-4d39-a868-cb0a463e2645"
    token = create_access_token(subject)
    assert decode_access_token(token) == subject
    assert decode_access_token(token + "x") is None
    assert decode_access_token("") is None
    assert decode_access_token("not.a.jwt") is None


def test_sha256_normalization_and_validation():
    digest = compute_sha256(" Student@Example.COM ")
    assert digest == compute_sha256("student@example.com")
    assert is_valid_sha256(digest) is True
    assert is_valid_sha256(digest.upper()) is False
    assert is_valid_sha256("short") is False
