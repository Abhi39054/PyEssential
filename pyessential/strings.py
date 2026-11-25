"""
    Name: pyessential.strings
    Description: A module providing utility functions for cleaning, formatting, and transforming strings.
"""

import html
import re
import unicodedata
from html.parser import HTMLParser
from typing import List, Optional

__all__ = [
    "remove_accents",
    "slugify",
    "truncate",
    "mask_secret",
    "to_snake_case",
    "to_camel_case",
    "to_pascal_case",
    "to_kebab_case",
    "normalize_whitespace",
    "strip_html",
    "is_blank",
]

# ---------------------------------------------------------------- helpers
_ACRONYM_BOUNDARY_RE = re.compile(r"([A-Z]+)([A-Z][a-z])")
_LOWER_TO_UPPER_RE = re.compile(r"([a-z0-9])([A-Z])")
_WORD_RE = re.compile(r"[A-Za-z0-9]+")
_WHITESPACE_RE = re.compile(r"\s+")


def _split_words(text: str) -> List[str]:
    """Split a string into alphanumeric words across camelCase, PascalCase, snake_case, and spaces."""
    if not text:
        return []
    separated = _ACRONYM_BOUNDARY_RE.sub(r"\1 \2", text)
    separated = _LOWER_TO_UPPER_RE.sub(r"\1 \2", separated)
    return _WORD_RE.findall(separated)


class _HTMLStripper(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self._parts: List[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def handle_entityref(self, name: str) -> None:
        self._parts.append(html.unescape(f"&{name};"))

    def handle_charref(self, name: str) -> None:
        self._parts.append(html.unescape(f"&#{name};"))

    def get_text(self) -> str:
        return "".join(self._parts)


# ------------------------------------------------------------- public API
def remove_accents(text: str) -> str:
    """Remove diacritical marks (accents) from Unicode characters.

    Example: ``"Café naïve"`` -> ``"Cafe naive"``.

    Args:
        text (str): The input string.

    Returns:
        str: The string with combining accent marks removed.
    """
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def slugify(
    text: str,
    *,
    separator: str = "-",
    lowercase: bool = True,
    max_length: Optional[int] = None,
) -> str:
    """Convert ``text`` into a URL-friendly slug.

    Removes accents, replaces non-alphanumeric runs with ``separator``, and strips
    leading or trailing separators.

    Args:
        text (str): The input string.
        separator (str): Character(s) used to join words. Default is ``"-"``.
        lowercase (bool): Convert the result to lowercase. Default is True.
        max_length (int, optional): Maximum length of the returned slug.

    Returns:
        str: The generated slug.

    Raises:
        ValueError: If ``max_length`` is negative.
    """
    if max_length is not None and max_length < 0:
        raise ValueError("max_length must not be negative")

    cleaned = remove_accents(text)
    if lowercase:
        cleaned = cleaned.lower()

    words = _WORD_RE.findall(cleaned)
    slug = separator.join(words)

    if max_length is not None and len(slug) > max_length:
        slug = slug[:max_length]
        if separator:
            slug = slug.rstrip(separator)

    return slug


def truncate(
    text: str,
    max_length: int,
    *,
    suffix: str = "...",
    whole_word: bool = False,
) -> str:
    """Shorten ``text`` to at most ``max_length`` characters, appending ``suffix`` if cut.

    Args:
        text (str): The input string.
        max_length (int): Maximum allowed length of the returned string (including ``suffix``).
        suffix (str): Trailing indicator added when ``text`` is shortened. Default is ``"..."``.
        whole_word (bool): Avoid cutting in the middle of a word when possible. Default is False.

    Returns:
        str: The original or truncated string.

    Raises:
        ValueError: If ``max_length`` is negative.
    """
    if max_length < 0:
        raise ValueError("max_length must not be negative")
    if len(text) <= max_length:
        return text
    if max_length <= len(suffix):
        return suffix[:max_length]

    cut_at = max_length - len(suffix)
    prefix = text[:cut_at]

    if whole_word and not text[cut_at].isspace():
        last_space = prefix.rfind(" ")
        if last_space > 0:
            prefix = prefix[:last_space]

    return prefix.rstrip() + suffix


def mask_secret(
    secret: str,
    *,
    visible_start: int = 0,
    visible_end: int = 4,
    mask_char: str = "*",
) -> str:
    """Mask a sensitive string (API key, token, card number) for safe logging.

    If ``visible_start + visible_end`` is greater than or equal to the length of ``secret``,
    the entire string is masked so short secrets are never leaked in plain text.

    Args:
        secret (str): The sensitive string to mask.
        visible_start (int): Number of leading characters to leave unmasked. Default is 0.
        visible_end (int): Number of trailing characters to leave unmasked. Default is 4.
        mask_char (str): Single character used for masking. Default is ``"*"``.

    Returns:
        str: The masked string.

    Raises:
        ValueError: If ``visible_start`` or ``visible_end`` is negative, or ``mask_char``
            is not a single character.
    """
    if visible_start < 0 or visible_end < 0:
        raise ValueError("visible_start and visible_end must not be negative")
    if len(mask_char) != 1:
        raise ValueError("mask_char must be a single character")
    if not secret:
        return ""

    length = len(secret)
    if visible_start + visible_end >= length:
        return mask_char * length

    start = secret[:visible_start] if visible_start else ""
    end = secret[-visible_end:] if visible_end else ""
    masked_len = length - visible_start - visible_end
    return f"{start}{mask_char * masked_len}{end}"


def to_snake_case(text: str) -> str:
    """Convert ``text`` to ``snake_case``.

    Args:
        text (str): The input string.

    Returns:
        str: The ``snake_case`` representation.
    """
    return "_".join(word.lower() for word in _split_words(remove_accents(text)))


def to_kebab_case(text: str) -> str:
    """Convert ``text`` to ``kebab-case``.

    Args:
        text (str): The input string.

    Returns:
        str: The ``kebab-case`` representation.
    """
    return "-".join(word.lower() for word in _split_words(remove_accents(text)))


def to_pascal_case(text: str) -> str:
    """Convert ``text`` to ``PascalCase``.

    Args:
        text (str): The input string.

    Returns:
        str: The ``PascalCase`` representation.
    """
    return "".join(word.capitalize() for word in _split_words(remove_accents(text)))


def to_camel_case(text: str) -> str:
    """Convert ``text`` to ``camelCase``.

    Args:
        text (str): The input string.

    Returns:
        str: The ``camelCase`` representation.
    """
    words = _split_words(remove_accents(text))
    if not words:
        return ""
    return words[0].lower() + "".join(word.capitalize() for word in words[1:])


def normalize_whitespace(text: str) -> str:
    """Collapse consecutive whitespace characters into a single space and strip ends.

    Args:
        text (str): The input string.

    Returns:
        str: The normalized string.
    """
    return _WHITESPACE_RE.sub(" ", text).strip()


def strip_html(text: str) -> str:
    """Remove HTML tags from ``text`` and decode HTML entities.

    Args:
        text (str): The input HTML string.

    Returns:
        str: Plain text with tags removed.
    """
    if not text:
        return ""
    stripper = _HTMLStripper()
    stripper.feed(text)
    stripper.close()
    return stripper.get_text()


def is_blank(text: Optional[str]) -> bool:
    """Check whether ``text`` is ``None``, empty, or contains only whitespace.

    Args:
        text (str | None): The value to check.

    Returns:
        bool: True if ``text`` is blank.
    """
    return text is None or not text.strip()