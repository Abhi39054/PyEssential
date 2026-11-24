import uuid
import pytest

from pyessential.validators import (
    is_domain,
    is_email,
    is_hex,
    is_ip,
    is_json,
    is_mac_address,
    is_port,
    is_slug,
    is_url,
    is_uuid,
)


# ------------------------------------------------------------------ is_domain
@pytest.mark.parametrize(
    "value",
    [
        "example.com",
        "sub.domain.co.in",
        "my-site123.org",
        "xn--bcher-kva.example",
    ],
)
def test_is_domain_valid(value):
    assert is_domain(value) is True


@pytest.mark.parametrize(
    "value",
    [
        "",
        None,
        123,
        "localhost",
        "-bad.com",
        "bad-.com",
        "example.c",
        "example..com",
        "example.com.",
        "example.com\n",
        "http://example.com",
    ],
)
def test_is_domain_invalid(value):
    assert is_domain(value) is False


# ------------------------------------------------------------------- is_email
@pytest.mark.parametrize(
    "value",
    [
        "user@example.com",
        "first.last+tag@sub.domain.org",
        "user_123@company.co.in",
    ],
)
def test_is_email_valid(value):
    assert is_email(value) is True


@pytest.mark.parametrize(
    "value",
    [
        "",
        None,
        42,
        "plainaddress",
        "@example.com",
        "user@",
        "user@localhost",
        ".user@example.com",
        "user.@example.com",
        "user..name@example.com",
        "user name@example.com",
        "user@example.com\n",
        "a" * 65 + "@example.com",
    ],
)
def test_is_email_invalid(value):
    assert is_email(value) is False


# --------------------------------------------------------------------- is_url
@pytest.mark.parametrize(
    "value",
    [
        "https://example.com",
        "http://sub.example.com:8080/path?a=1&b=2#top",
        "http://localhost:8000/docs",
        "http://127.0.0.1:5000/api",
        "https://[2001:db8::1]/resource",
    ],
)
def test_is_url_valid(value):
    assert is_url(value) is True


@pytest.mark.parametrize(
    "value",
    [
        "",
        None,
        123,
        "example.com",
        "ftp://example.com",
        "http://",
        "https://bad host.com",
        "https://example.com:99999",
        "https://example.com\n",
    ],
)
def test_is_url_invalid(value):
    assert is_url(value) is False


def test_is_url_custom_schemes_and_localhost():
    assert is_url("ftp://files.example.com/a.zip", schemes=("ftp",)) is True
    assert is_url("http://localhost:8000", allow_localhost=False) is False


# -------------------------------------------------------------------- is_uuid
def test_is_uuid_valid_and_versions():
    v1 = str(uuid.uuid1())
    v4 = str(uuid.uuid4())
    v5 = str(uuid.uuid5(uuid.NAMESPACE_DNS, "example.com"))

    assert is_uuid(v1) is True
    assert is_uuid(v4, version=4) is True
    assert is_uuid(v4, version=1) is False
    assert is_uuid(v5, version=5) is True


@pytest.mark.parametrize("value", ["", None, 123, "not-a-uuid", "12345678-1234-1234-1234-1234567890abZ"])
def test_is_uuid_invalid(value):
    assert is_uuid(value) is False


def test_is_uuid_bad_version_raises():
    with pytest.raises(ValueError):
        is_uuid(str(uuid.uuid4()), version=9)


# ---------------------------------------------------------------------- is_ip
@pytest.mark.parametrize("value", ["127.0.0.1", "192.168.1.1", "0.0.0.0", "::1", "2001:db8::1"])
def test_is_ip_valid(value):
    assert is_ip(value) is True


def test_is_ip_version_filtering():
    assert is_ip("192.168.0.1", version=4) is True
    assert is_ip("192.168.0.1", version=6) is False
    assert is_ip("2001:db8::1", version=6) is True
    assert is_ip("2001:db8::1", version=4) is False

    with pytest.raises(ValueError):
        is_ip("127.0.0.1", version=5)


@pytest.mark.parametrize("value", ["", None, 123, "256.0.0.1", "1.2.3", "example.com", "127.0.0.1\n"])
def test_is_ip_invalid(value):
    assert is_ip(value) is False


# -------------------------------------------------------------------- is_port
@pytest.mark.parametrize("value", [1, 80, 443, 8080, 65535, "80", "65535"])
def test_is_port_valid(value):
    assert is_port(value) is True


@pytest.mark.parametrize("value", [0, -1, 65536, "0", "-80", "8080a", "", None, True, False, 80.5])
def test_is_port_invalid(value):
    assert is_port(value) is False


def test_is_port_allow_zero():
    assert is_port(0, allow_zero=True) is True
    assert is_port("0", allow_zero=True) is True


# --------------------------------------------------------------------- is_hex
@pytest.mark.parametrize("value", ["0", "deadbeef", "DEADBEEF", "1a2B3c"])
def test_is_hex_valid(value):
    assert is_hex(value) is True


@pytest.mark.parametrize("value", ["", None, 0xFF, "0x1A", "xyz", "12 34", "deadbeef\n"])
def test_is_hex_invalid(value):
    assert is_hex(value) is False


def test_is_hex_allow_prefix():
    assert is_hex("0xdeadbeef", allow_prefix=True) is True
    assert is_hex("0X1A2B", allow_prefix=True) is True
    assert is_hex("0x", allow_prefix=True) is False


# ------------------------------------------------------------- is_mac_address
@pytest.mark.parametrize("value", ["AA:BB:CC:DD:EE:FF", "aa-bb-cc-dd-ee-ff", "aabb.ccdd.eeff"])
def test_is_mac_address_valid(value):
    assert is_mac_address(value) is True


@pytest.mark.parametrize("value", ["", None, 123, "AA:BB:CC:DD:EE", "AA:BB-CC:DD:EE:FF", "GG:BB:CC:DD:EE:FF"])
def test_is_mac_address_invalid(value):
    assert is_mac_address(value) is False


# -------------------------------------------------------------------- is_json
@pytest.mark.parametrize("value", ['{"a": 1}', "[1, 2, 3]", '"hello"', "true", "null", "42"])
def test_is_json_valid(value):
    assert is_json(value) is True


@pytest.mark.parametrize("value", ["", None, {"a": 1}, "{bad}", "{'a': 1}"])
def test_is_json_invalid(value):
    assert is_json(value) is False


# -------------------------------------------------------------------- is_slug
@pytest.mark.parametrize("value", ["hello", "hello-world", "pyessential-v2-release"])
def test_is_slug_valid(value):
    assert is_slug(value) is True


@pytest.mark.parametrize("value", ["", None, 123, "Hello-World", "-leading", "trailing-", "double--hyphen", "has space"])
def test_is_slug_invalid(value):
    assert is_slug(value) is False