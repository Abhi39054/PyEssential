# Strings (`pyessential.strings`)

Utility functions for cleaning, formatting, masking, and transforming strings using only the Python standard library.

## Quick Overview

| Function | Purpose |
| ----- | ----- |
| `remove_accents(text)` | Strip diacritical marks from Unicode characters |
| `slugify(text, *, separator="-", lowercase=True, max_length=None)` | Convert text into a URL-friendly slug |
| `truncate(text, max_length, *, suffix="...", whole_word=False)` | Shorten text to a maximum length with a trailing suffix |
| `mask_secret(secret, *, visible_start=0, visible_end=4, mask_char="*")` | Mask API keys, tokens, or sensitive values for safe logging |
| `to_snake_case(text)` | Convert text to `snake_case` |
| `to_kebab_case(text)` | Convert text to `kebab-case` |
| `to_camel_case(text)` | Convert text to `camelCase` |
| `to_pascal_case(text)` | Convert text to `PascalCase` |
| `normalize_whitespace(text)` | Collapse consecutive whitespace into single spaces and trim ends |
| `strip_html(text)` | Remove HTML tags and decode HTML entities |
| `is_blank(text)` | Check whether a string is `None`, empty, or whitespace-only |

## Usage

```python
from pyessential.strings import (
    remove_accents,
    slugify,
    truncate,
    mask_secret,
    to_snake_case,
    to_kebab_case,
    to_camel_case,
    to_pascal_case,
    normalize_whitespace,
    strip_html,
    is_blank,
)

slugify("Café & Bistro -- 2026")                   # "cafe-bistro-2026"
truncate("The quick brown fox", 14, whole_word=True)  # "The quick..."
mask_secret("sk-1234567890abcd", visible_start=3)  # "sk-**********abcd"
to_snake_case("HTTPResponseCode")                  # "http_response_code"
strip_html("<p>Hello <b>world</b>!</p>")           # "Hello world!"
```

## Functions Reference

### `remove_accents(text) -> str`

Remove diacritical marks (accents) from Unicode characters using NFKD normalization.

* **Parameters:**
  * `text` (`str`): The input string.
* **Returns:** `str`

**Example:**

```python
remove_accents("Café naïve résumé")  # "Cafe naive resume"
remove_accents("São Paulo")          # "Sao Paulo"
```

### `slugify(text, *, separator="-", lowercase=True, max_length=None) -> str`

Convert `text` into a URL-friendly slug by removing accents, replacing non-alphanumeric runs with `separator`, and trimming leading or trailing separators.

* **Parameters:**
  * `text` (`str`): The input string.
  * `separator` (`str`, keyword-only): Character(s) used to join words. Default is `"-"`.
  * `lowercase` (`bool`, keyword-only): Convert output to lowercase. Default is `True`.
  * `max_length` (`int | None`, keyword-only): Maximum length of the returned slug.
* **Returns:** `str`
* **Raises:** `ValueError` if `max_length` is negative.

**Example:**

```python
slugify("Hello World!")                              # "hello-world"
slugify("Hello World", separator="_")                # "hello_world"
slugify("a very long article title", max_length=12)  # "a-very-long"
```

### `truncate(text, max_length, *, suffix="...", whole_word=False) -> str`

Shorten `text` to at most `max_length` characters (including `suffix`). Returns `text` unchanged if it already fits.

* **Parameters:**
  * `text` (`str`): The input string.
  * `max_length` (`int`): Maximum allowed length of the result.
  * `suffix` (`str`, keyword-only): Indicator appended when text is cut. Default is `"..."`.
  * `whole_word` (`bool`, keyword-only): Avoid splitting a word in the middle when possible. Default is `False`.
* **Returns:** `str`
* **Raises:** `ValueError` if `max_length` is negative.

**Example:**

```python
truncate("hello world", 8)                             # "hello..."
truncate("The quick brown fox", 14, whole_word=True)   # "The quick..."
truncate("hello world", 8, suffix="~")                 # "hello w~"
```

### `mask_secret(secret, *, visible_start=0, visible_end=4, mask_char="*") -> str`

Mask a sensitive string (such as an API key, token, or card number) for safe logging. If `visible_start + visible_end` is greater than or equal to the length of `secret`, the entire string is masked so short secrets are never leaked.

* **Parameters:**
  * `secret` (`str`): The sensitive string to mask.
  * `visible_start` (`int`, keyword-only): Leading characters to leave visible. Default is `0`.
  * `visible_end` (`int`, keyword-only): Trailing characters to leave visible. Default is `4`.
  * `mask_char` (`str`, keyword-only): Single character used for masking. Default is `"*"`.
* **Returns:** `str`
* **Raises:** `ValueError` if `visible_start` or `visible_end` is negative, or if `mask_char` is not a single character.

**Example:**

```python
mask_secret("sk-1234567890abcd")                                 # "*************abcd"
mask_secret("sk-1234567890abcd", visible_start=3, visible_end=4) # "sk-**********abcd"
mask_secret("1234", visible_end=4)                               # "****"
```

### `to_snake_case(text) -> str`

Convert `text` (from spaces, `camelCase`, `PascalCase`, `kebab-case`, or acronyms) into `snake_case`.

* **Parameters:**
  * `text` (`str`): The input string.
* **Returns:** `str`

**Example:**

```python
to_snake_case("HTTPResponseCode")  # "http_response_code"
to_snake_case("hello world")       # "hello_world"
```

### `to_kebab_case(text) -> str`

Convert `text` into `kebab-case`.

* **Parameters:**
  * `text` (`str`): The input string.
* **Returns:** `str`

**Example:**

```python
to_kebab_case("PascalCaseText")    # "pascal-case-text"
to_kebab_case("already_snake_case") # "already-snake-case"
```

### `to_camel_case(text) -> str`

Convert `text` into `camelCase`.

* **Parameters:**
  * `text` (`str`): The input string.
* **Returns:** `str`

**Example:**

```python
to_camel_case("hello_world")       # "helloWorld"
to_camel_case("HTTPResponseCode")  # "httpResponseCode"
```

### `to_pascal_case(text) -> str`

Convert `text` into `PascalCase`.

* **Parameters:**
  * `text` (`str`): The input string.
* **Returns:** `str`

**Example:**

```python
to_pascal_case("hello-world")      # "HelloWorld"
to_pascal_case("camelCaseText")    # "CamelCaseText"
```

### `normalize_whitespace(text) -> str`

Collapse consecutive whitespace characters (spaces, tabs, newlines) into a single space and strip leading/trailing whitespace.

* **Parameters:**
  * `text` (`str`): The input string.
* **Returns:** `str`

**Example:**

```python
normalize_whitespace("  hello   \t\n  world  ")  # "hello world"
```

### `strip_html(text) -> str`

Remove HTML tags from `text` and decode HTML character entities.

* **Parameters:**
  * `text` (`str`): The input HTML string.
* **Returns:** `str`

**Example:**

```python
strip_html("<p>Hello <b>world</b>!</p>")  # "Hello world!"
strip_html("Tom &amp; Jerry &#39;26")     # "Tom & Jerry '26"
```

### `is_blank(text) -> bool`

Check whether `text` is `None`, empty, or contains only whitespace characters.

* **Parameters:**
  * `text` (`str | None`): The value to check.
* **Returns:** `bool`

**Example:**

```python
is_blank(None)     # True
is_blank("   \t")  # True
is_blank("hello")  # False
```