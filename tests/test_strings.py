import pytest

from pyessential.strings import (
    is_blank,
    mask_secret,
    normalize_whitespace,
    remove_accents,
    slugify,
    strip_html,
    to_camel_case,
    to_kebab_case,
    to_pascal_case,
    to_snake_case,
    truncate,
)


# ------------------------------------------------------------- remove_accents
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Café", "Cafe"),
        ("naïve résumé", "naive resume"),
        ("São Paulo", "Sao Paulo"),
        ("plain ascii 123", "plain ascii 123"),
        ("", ""),
    ],
)
def test_remove_accents(raw, expected):
    assert remove_accents(raw) == expected


# -------------------------------------------------------------------- slugify
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Hello World!", "hello-world"),
        ("  Café & Bistro -- 2026  ", "cafe-bistro-2026"),
        ("Python_3.12 Release", "python-3-12-release"),
        ("___", ""),
        ("", ""),
    ],
)
def test_slugify_basic(raw, expected):
    assert slugify(raw) == expected


def test_slugify_options():
    assert slugify("Hello World", separator="_") == "hello_world"
    assert slugify("Hello World", lowercase=False) == "Hello-World"
    assert slugify("a very long article title", max_length=12) == "a-very-long"
    assert slugify("hello-world", max_length=6) == "hello"

    with pytest.raises(ValueError):
        slugify("hello", max_length=-1)


# ------------------------------------------------------------------- truncate
def test_truncate_basic():
    assert truncate("hello", 10) == "hello"
    assert truncate("hello world", 8) == "hello..."
    assert truncate("hello world", 8, suffix="~") == "hello w~"
    assert truncate("hello world", 2) == ".."
    assert truncate("hello world", 0) == ""


def test_truncate_whole_word():
    assert truncate("The quick brown fox", 14, whole_word=True) == "The quick..."
    assert truncate("Supercalifragilistic", 10, whole_word=True) == "Superca..."


def test_truncate_negative_raises():
    with pytest.raises(ValueError):
        truncate("hello", -5)


# ---------------------------------------------------------------- mask_secret
def test_mask_secret():
    assert mask_secret("sk-1234567890abcd") == "*************abcd"
    assert mask_secret("sk-1234567890abcd", visible_start=3, visible_end=4) == "sk-**********abcd"
    assert mask_secret("12345678", visible_start=0, visible_end=0) == "********"
    assert mask_secret("secret", visible_start=2, visible_end=2, mask_char="#") == "se##et"
    assert mask_secret("") == ""

    # Short secret should be fully masked rather than leaked
    assert mask_secret("1234", visible_end=4) == "****"
    assert mask_secret("ab", visible_start=2, visible_end=2) == "**"


def test_mask_secret_validation():
    with pytest.raises(ValueError):
        mask_secret("secret", visible_start=-1)
    with pytest.raises(ValueError):
        mask_secret("secret", visible_end=-1)
    with pytest.raises(ValueError):
        mask_secret("secret", mask_char="**")


# ----------------------------------------------------------- case conversions
@pytest.mark.parametrize(
    "raw,snake,kebab,camel,pascal",
    [
        ("hello world", "hello_world", "hello-world", "helloWorld", "HelloWorld"),
        ("camelCaseText", "camel_case_text", "camel-case-text", "camelCaseText", "CamelCaseText"),
        ("PascalCaseText", "pascal_case_text", "pascal-case-text", "pascalCaseText", "PascalCaseText"),
        ("HTTPResponseCode", "http_response_code", "http-response-code", "httpResponseCode", "HttpResponseCode"),
        ("already_snake_case", "already_snake_case", "already-snake-case", "alreadySnakeCase", "AlreadySnakeCase"),
        ("kebab-case-2-test", "kebab_case_2_test", "kebab-case-2-test", "kebabCase2Test", "KebabCase2Test"),
        ("", "", "", "", ""),
    ],
)
def test_case_conversions(raw, snake, kebab, camel, pascal):
    assert to_snake_case(raw) == snake
    assert to_kebab_case(raw) == kebab
    assert to_camel_case(raw) == camel
    assert to_pascal_case(raw) == pascal


# ------------------------------------------------------- normalize_whitespace
def test_normalize_whitespace():
    assert normalize_whitespace("  hello   \t\n  world  ") == "hello world"
    assert normalize_whitespace("   ") == ""
    assert normalize_whitespace("") == ""


# ----------------------------------------------------------------- strip_html
def test_strip_html():
    assert strip_html("<p>Hello <b>world</b>!</p>") == "Hello world!"
    assert strip_html("Tom &amp; Jerry &#39;26") == "Tom & Jerry '26"
    assert strip_html("plain text") == "plain text"
    assert strip_html("") == ""


# ------------------------------------------------------------------- is_blank
@pytest.mark.parametrize("value", [None, "", "   ", "\t\n\r"])
def test_is_blank_true(value):
    assert is_blank(value) is True


@pytest.mark.parametrize("value", ["a", "  a  ", "0"])
def test_is_blank_false(value):
    assert is_blank(value) is False