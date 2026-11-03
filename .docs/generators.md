# Generators

Utility functions for generating random data. Everything here uses Python's
[`secrets`](https://docs.python.org/3/library/secrets.html) module, so the values are
cryptographically secure and suitable for tokens, keys and other security-sensitive uses.

```python
from pyessential.generators import generate_random_int, generate_secret_key
```

## Functions

| Function | Returns | Description |
|---|---|---|
| [`generate_random_int(min_value=0, max_value=100)`](#generate_random_int) | `int` | A secure random integer in a range (both ends included). |
| [`generate_secret_key(length=32)`](#generate_secret_key) | `str` | A secure random hexadecimal key. |

---

## `generate_random_int`

```python
generate_random_int(min_value: int = 0, max_value: int = 100) -> int
```

Generates a cryptographically secure random integer N such that
`min_value <= N <= max_value`. **Both ends of the range are included.**

| Parameter | Default | Description |
|---|---|---|
| `min_value` | `0` | Lowest value that can be returned. |
| `max_value` | `100` | Highest value that can be returned. |

**Raises** `ValueError` if `min_value` is greater than `max_value`.

### Examples

```python
from pyessential.generators import generate_random_int

generate_random_int()          # e.g. 42, anywhere from 0 to 100
generate_random_int(1, 6)      # a dice roll: 1, 2, 3, 4, 5 or 6
generate_random_int(-10, 10)   # negative ranges work too
generate_random_int(7, 7)      # always 7 (min equal to max is allowed)
```

An invalid range raises an error:

```python
generate_random_int(10, 1)
# ValueError: min_value must be less than or equal to max_value
```

---

## `generate_secret_key`

```python
generate_secret_key(length: int = 32) -> str
```

Generates a cryptographically secure random secret key, returned as a hexadecimal string.

| Parameter | Default | Description |
|---|---|---|
| `length` | `32` | Number of random **bytes** to use. |

Because each byte is written as two hex characters, the returned string is `2 * length`
characters long. The default gives a 64-character key.

**Raises** `ValueError` if `length` is less than 1.

### Examples

```python
from pyessential.generators import generate_secret_key

key = generate_secret_key()
len(key)                      # 64
key                           # e.g. 'f3a9...' (64 hex characters)

generate_secret_key(16)       # 32 characters (16 bytes)
```

Typical use, such as a session or signing key for a web app:

```python
SECRET_KEY = generate_secret_key()
```

Generate the key once and store it in an environment variable or secrets manager. A key
generated at every start-up changes each time the app restarts, which would invalidate sessions
and signed tokens.

An invalid length raises an error:

```python
generate_secret_key(0)
# ValueError: length must be at least 1
```

---

## Notes

- **Not reproducible.** These functions draw from the operating system's secure random source,
  so they can't be seeded. If a test needs predictable values, patch the function (for example
  with `unittest.mock.patch`) instead of trying to set a seed.
- **Not for statistics or simulations.** Secure randomness is slower than `random`. For
  non-security uses where you want repeatable results, use the standard `random` module.