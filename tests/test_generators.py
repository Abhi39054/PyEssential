# tests/test_generators.py
import pytest

from pyessential.generators import generate_random_int, generate_secret_key


# ---------- generate_random_int ----------

@pytest.mark.parametrize(
    "min_value, max_value",
    [(0, 100), (10, 10), (-10, -5), (-5, 5), (1000, 2000)],
)
def test_generate_random_int_within_range(min_value, max_value):
    # Many draws, so a single lucky value can't hide an off-by-one bug
    for _ in range(100):
        assert min_value <= generate_random_int(min_value, max_value) <= max_value


def test_generate_random_int_default_range():
    for _ in range(100):
        assert 0 <= generate_random_int() <= 100


def test_generate_random_int_reaches_both_ends_of_range():
    # Both bounds are inclusive. Missing a value in 300 draws of 3 options
    # has a probability of about 1e-53, so this test is not flaky.
    assert {generate_random_int(1, 3) for _ in range(300)} == {1, 2, 3}


def test_generate_random_int_single_value_range():
    assert generate_random_int(10, 10) == 10


def test_generate_random_int_multiple_calls():
    assert len({generate_random_int() for _ in range(20)}) > 1


def test_generate_random_int_min_greater_than_max_raises():
    with pytest.raises(ValueError, match="min_value"):
        generate_random_int(10, 1)


# ---------- generate_secret_key ----------

@pytest.mark.parametrize("length", [1, 8, 16, 32, 64])
def test_generate_secret_key_length_is_twice_the_byte_count(length):
    assert len(generate_secret_key(length)) == length * 2


def test_generate_secret_key_default_length():
    assert len(generate_secret_key()) == 64


def test_generate_secret_key_is_hex():
    assert set(generate_secret_key(32)) <= set("0123456789abcdef")


def test_generate_secret_key_different_calls():
    assert generate_secret_key() != generate_secret_key()


@pytest.mark.parametrize("bad_length", [0, -1])
def test_generate_secret_key_invalid_length_raises(bad_length):
    with pytest.raises(ValueError, match="length"):
        generate_secret_key(bad_length)