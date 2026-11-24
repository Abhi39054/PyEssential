"""
    Name: pyessential.validators
    Description: A module providing utility functions for validating common data formats.
"""

import ipaddress
import json
import re
import uuid
from typing import Any, Optional, Sequence
from urllib.parse import urlparse

__all__ = [
    "is_email",
    "is_url",
    "is_uuid",
    "is_ip",
    "is_port",
    "is_hex",
    "is_domain",
    "is_mac_address",
    "is_json",
    "is_slug",
]

# ---------------------------------------------------------------- patterns
_EMAIL_LOCAL_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+\Z")
_DOMAIN_LABEL_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\Z")
_TLD_RE = re.compile(r"^(?:[A-Za-z]{2,63}|xn--[A-Za-z0-9-]{2,59})\Z")
_HEX_RE = re.compile(r"^[0-9A-Fa-f]+\Z")
_MAC_RE = re.compile(
    r"^(?:[0-9A-Fa-f]{2}([:-])[0-9A-Fa-f]{2}(?:\1[0-9A-Fa-f]{2}){4}"
    r"|[0-9A-Fa-f]{4}\.[0-9A-Fa-f]{4}\.[0-9A-Fa-f]{4})\Z"
)
_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*\Z")


# ------------------------------------------------------------- public API
def is_domain(value: Any) -> bool:
    """Check whether ``value`` is a valid domain name (e.g. ``example.com``).

    Args:
        value (Any): The value to validate.

    Returns:
        bool: True if ``value`` is a valid domain name.
    """
    if not isinstance(value, str) or not value or len(value) > 253:
        return False
    if value.endswith("."):
        return False
    labels = value.split(".")
    if len(labels) < 2:
        return False
    if not _TLD_RE.match(labels[-1]):
        return False
    return all(_DOMAIN_LABEL_RE.match(label) for label in labels)


def is_email(value: Any) -> bool:
    """Check whether ``value`` is a valid email address.

    Performs practical syntax validation (length limits, local-part rules, and a valid
    domain with TLD). Does not verify whether the mailbox actually exists.

    Args:
        value (Any): The value to validate.

    Returns:
        bool: True if ``value`` is a valid email address.
    """
    if not isinstance(value, str) or not value or len(value) > 254:
        return False
    if value.count("@") != 1:
        return False
    local, domain = value.split("@", 1)
    if not local or len(local) > 64:
        return False
    if local.startswith(".") or local.endswith(".") or ".." in local:
        return False
    if not _EMAIL_LOCAL_RE.match(local):
        return False
    return is_domain(domain)


def is_url(
    value: Any, *, schemes: Sequence[str] = ("http", "https"), allow_localhost: bool = True
) -> bool:
    """Check whether ``value`` is a valid URL.

    Args:
        value (Any): The value to validate.
        schemes (Sequence[str]): Allowed URL schemes. Default is ``("http", "https")``.
        allow_localhost (bool): Whether ``localhost`` is accepted as a host.
            Default is True.

    Returns:
        bool: True if ``value`` is a valid URL.
    """
    if not isinstance(value, str) or not value:
        return False
    if any(ch.isspace() for ch in value):
        return False

    try:
        parsed = urlparse(value)
        port = parsed.port
    except ValueError:
        return False

    if parsed.scheme.lower() not in {s.lower() for s in schemes}:
        return False
    if not parsed.netloc or not parsed.hostname:
        return False
    if port is not None and not is_port(port):
        return False

    host = parsed.hostname
    if allow_localhost and host.lower() == "localhost":
        return True
    return is_domain(host) or is_ip(host)


def is_uuid(value: Any, *, version: Optional[int] = None) -> bool:
    """Check whether ``value`` is a valid UUID string.

    Args:
        value (Any): The value to validate.
        version (int, optional): Require a specific UUID version (1 to 5).
            Default is None (any valid UUID).

    Returns:
        bool: True if ``value`` is a valid UUID.

    Raises:
        ValueError: If ``version`` is not None and not between 1 and 5.
    """
    if version is not None and version not in (1, 2, 3, 4, 5):
        raise ValueError("version must be between 1 and 5")
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError):
        return False
    if version is not None and parsed.version != version:
        return False
    return True


def is_ip(value: Any, *, version: Optional[int] = None) -> bool:
    """Check whether ``value`` is a valid IPv4 or IPv6 address.

    Args:
        value (Any): The value to validate.
        version (int, optional): Restrict to ``4`` (IPv4) or ``6`` (IPv6).
            Default is None (accept either).

    Returns:
        bool: True if ``value`` is a valid IP address.

    Raises:
        ValueError: If ``version`` is not None, 4, or 6.
    """
    if version is not None and version not in (4, 6):
        raise ValueError("version must be 4 or 6")
    if not isinstance(value, str) or not value:
        return False
    try:
        addr = ipaddress.ip_address(value)
    except ValueError:
        return False
    if version is not None and addr.version != version:
        return False
    return True


def is_port(value: Any, *, allow_zero: bool = False) -> bool:
    """Check whether ``value`` is a valid TCP/UDP port number (1-65535).

    Accepts both ``int`` and numeric ``str`` values (e.g. ``8080`` or ``"8080"``).
    Booleans are rejected.

    Args:
        value (Any): The value to validate.
        allow_zero (bool): Also allow port ``0``. Default is False.

    Returns:
        bool: True if ``value`` is a valid port number.
    """
    if isinstance(value, bool):
        return False
    if isinstance(value, str):
        if not value.isdigit():
            return False
        port = int(value)
    elif isinstance(value, int):
        port = value
    else:
        return False

    minimum = 0 if allow_zero else 1
    return minimum <= port <= 65535


def is_hex(value: Any, *, allow_prefix: bool = False) -> bool:
    """Check whether ``value`` is a valid hexadecimal string.

    Args:
        value (Any): The value to validate.
        allow_prefix (bool): Allow a leading ``0x`` or ``0X`` prefix. Default is False.

    Returns:
        bool: True if ``value`` contains only hexadecimal characters.
    """
    if not isinstance(value, str) or not value:
        return False
    target = value
    if allow_prefix and target.startswith(("0x", "0X")):
        target = target[2:]
    if not target:
        return False
    return bool(_HEX_RE.match(target))


def is_mac_address(value: Any) -> bool:
    """Check whether ``value`` is a valid MAC address.

    Supports colon-separated (``AA:BB:CC:DD:EE:FF``), hyphen-separated
    (``AA-BB-CC-DD-EE-FF``), and dot-separated Cisco format (``AABB.CCDD.EEFF``).

    Args:
        value (Any): The value to validate.

    Returns:
        bool: True if ``value`` is a valid MAC address.
    """
    if not isinstance(value, str) or not value:
        return False
    return bool(_MAC_RE.match(value))


def is_json(value: Any) -> bool:
    """Check whether ``value`` is a valid JSON string.

    Args:
        value (Any): The value to validate.

    Returns:
        bool: True if ``value`` can be parsed as JSON.
    """
    if not isinstance(value, str) or not value:
        return False
    try:
        json.loads(value)
    except ValueError:
        return False
    return True


def is_slug(value: Any) -> bool:
    """Check whether ``value`` is a valid URL slug (lowercase letters, digits, single hyphens).

    Args:
        value (Any): The value to validate.

    Returns:
        bool: True if ``value`` is a valid slug.
    """
    if not isinstance(value, str) or not value:
        return False
    return bool(_SLUG_RE.match(value))