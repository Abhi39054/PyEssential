# Validators (`pyessential.validators`)

Utility functions for validating common data formats using only the Python standard library.

All functions safely return `False` for invalid types (such as `None`, numbers, or empty strings) instead of raising type errors, unless a keyword option itself is invalid (e.g., an unsupported `version` value).

## Quick Overview

| Function | Purpose |
| :--- | :--- |
| `is_email(value)` | Validate email address syntax |
| `is_url(value, *, schemes=..., allow_localhost=True)` | Validate HTTP/HTTPS (or custom scheme) URLs |
| `is_uuid(value, *, version=None)` | Validate UUID strings (optionally by version 1–5) |
| `is_ip(value, *, version=None)` | Validate IPv4 or IPv6 addresses |
| `is_port(value, *, allow_zero=False)` | Validate TCP/UDP port numbers (`1–65535`) |
| `is_hex(value, *, allow_prefix=False)` | Validate hexadecimal strings |
| `is_domain(value)` | Validate domain names with a valid TLD |
| `is_mac_address(value)` | Validate MAC addresses (colon, hyphen, or Cisco dot format) |
| `is_json(value)` | Validate whether a string is valid JSON |
| `is_slug(value)` | Validate URL-friendly lowercase slugs |

---

## Usage

```python
from pyessential.validators import (
    is_email,
    is_url,
    is_uuid,
    is_ip,
    is_port,
    is_hex,
    is_domain,
    is_mac_address,
    is_json,
    is_slug,
)

is_email("user@example.com")              # True
is_url("https://example.com:8080/api")    # True
is_ip("192.168.1.1", version=4)           # True
is_port("8000")                           # True
is_slug("pyessential-v2")                 # True
```

---

## Functions Reference

### `is_email(value) -> bool`

Check whether `value` is a syntactically valid email address (enforces length limits, local-part rules, and a valid domain with a TLD). Does not verify whether the mailbox exists.

* **Parameters:**
  * `value` (`Any`): The value to validate.
* **Returns:** `bool`

**Example:**
```python
is_email("first.last+tag@company.co.in")  # True
is_email("user@localhost")                # False
is_email("user..name@example.com")        # False
```

---

### `is_url(value, *, schemes=("http", "https"), allow_localhost=True) -> bool`

Check whether `value` is a valid URL with an allowed scheme, valid host (domain, IP, or `localhost`), and optional valid port.

* **Parameters:**
  * `value` (`Any`): The value to validate.
  * `schemes` (`Sequence[str]`, keyword-only): Allowed URL schemes. Default is `("http", "https")`.
  * `allow_localhost` (`bool`, keyword-only): Accept `localhost` as a host. Default is `True`.
* **Returns:** `bool`

**Example:**
```python
is_url("https://example.com/docs?page=1")                   # True
is_url("http://localhost:8000", allow_localhost=False)      # False
is_url("ftp://files.example.com/a.zip", schemes=("ftp",))   # True
```

---

### `is_uuid(value, *, version=None) -> bool`

Check whether `value` is a valid UUID string.

* **Parameters:**
  * `value` (`Any`): The value to validate.
  * `version` (`int | None`, keyword-only): Require a specific UUID version (`1` to `5`). Default is `None` (any version).
* **Returns:** `bool`
* **Raises:** `ValueError` if `version` is not `None` and not between `1` and `5`.

**Example:**
```python
is_uuid("550e8400-e29b-41d4-a716-446655440000")             # True
is_uuid("550e8400-e29b-41d4-a716-446655440000", version=4)  # True
is_uuid("not-a-uuid")                                       # False
```

---

### `is_ip(value, *, version=None) -> bool`

Check whether `value` is a valid IPv4 or IPv6 address.

* **Parameters:**
  * `value` (`Any`): The value to validate.
  * `version` (`int | None`, keyword-only): Restrict to `4` (IPv4) or `6` (IPv6). Default is `None` (either).
* **Returns:** `bool`
* **Raises:** `ValueError` if `version` is not `None`, `4`, or `6`.

**Example:**
```python
is_ip("127.0.0.1")               # True
is_ip("2001:db8::1", version=6)  # True
is_ip("127.0.0.1", version=6)    # False
is_ip("256.0.0.1")               # False
```

---

### `is_port(value, *, allow_zero=False) -> bool`

Check whether `value` is a valid TCP/UDP port number (`1–65535`). Accepts both `int` and numeric `str` values; rejects booleans.

* **Parameters:**
  * `value` (`Any`): The value to validate.
  * `allow_zero` (`bool`, keyword-only): Also allow port `0`. Default is `False`.
* **Returns:** `bool`

**Example:**
```python
is_port(8080)                  # True
is_port("443")                 # True
is_port(0, allow_zero=True)    # True
is_port(70000)                 # False
is_port(True)                  # False
```

---

### `is_hex(value, *, allow_prefix=False) -> bool`

Check whether `value` is a valid hexadecimal string.

* **Parameters:**
  * `value` (`Any`): The value to validate.
  * `allow_prefix` (`bool`, keyword-only): Allow a leading `0x` or `0X` prefix. Default is `False`.
* **Returns:** `bool`

**Example:**
```python
is_hex("deadbeef")                     # True
is_hex("0x1A2B", allow_prefix=True)    # True
is_hex("0x1A2B")                       # False
is_hex("xyz")                          # False
```

---

### `is_domain(value) -> bool`

Check whether `value` is a valid domain name with at least two labels and a valid TLD (including Punycode TLDs like `xn--...`).

* **Parameters:**
  * `value` (`Any`): The value to validate.
* **Returns:** `bool`

**Example:**
```python
is_domain("example.com")         # True
is_domain("sub.domain.co.in")    # True
is_domain("localhost")           # False
is_domain("-bad.com")            # False
```

---

### `is_mac_address(value) -> bool`

Check whether `value` is a valid MAC address. Supports colon-separated (`AA:BB:CC:DD:EE:FF`), hyphen-separated (`AA-BB-CC-DD-EE-FF`), and Cisco dot-separated (`AABB.CCDD.EEFF`) formats.

* **Parameters:**
  * `value` (`Any`): The value to validate.
* **Returns:** `bool`

**Example:**
```python
is_mac_address("AA:BB:CC:DD:EE:FF")   # True
is_mac_address("aa-bb-cc-dd-ee-ff")   # True
is_mac_address("aabb.ccdd.eeff")      # True
is_mac_address("AA:BB-CC:DD:EE:FF")   # False
```

---

### `is_json(value) -> bool`

Check whether `value` is a valid JSON string.

* **Parameters:**
  * `value` (`Any`): The value to validate.
* **Returns:** `bool`

**Example:**
```python
is_json('{"name": "PyEssential", "active": true}')  # True
is_json("[1, 2, 3]")                                # True
is_json("{'single': 'quotes'}")                     # False
```

---

### `is_slug(value) -> bool`

Check whether `value` is a valid URL slug (lowercase letters, digits, and single hyphens between words).

* **Parameters:**
  * `value` (`Any`): The value to validate.
* **Returns:** `bool`

**Example:**
```python
is_slug("hello-world-2026")   # True
is_slug("Hello-World")        # False
is_slug("double--hyphen")     # False
```