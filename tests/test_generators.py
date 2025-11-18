# tests/test_generators.py
import time
from pyessential.generators import generate_random_int, generate_secret_key


# Test to ensure the generated integer is within the specified range
def test_generate_random_int_within_range():
    min_value = 0
    max_value = 100
    result = generate_random_int(min_value, max_value)
    assert min_value <= result <= max_value, f"Result {result} is not within range {min_value}-{max_value}"

# Test to check the default range
def test_generate_random_int_default_range():
    result = generate_random_int()
    assert 0 <= result <= 100, f"Result {result} is not within default range 0-100"

# Test to check multiple calls produce different results
def test_generate_random_int_multiple_calls():
    results = {generate_random_int() for _ in range(10)}
    assert len(results) > 1, "Multiple calls to generate_random_int produced the same result"

# Test to check edge case where min_value equals max_value
def test_generate_random_int_edge_case():
    min_value = 10
    max_value = 10
    result = generate_random_int(min_value, max_value)
    assert result == min_value, f"Result {result} is not equal to the edge case value {min_value}"

# Test to check negative range
def test_generate_random_int_negative_range():
    min_value = -10
    max_value = -5
    result = generate_random_int(min_value, max_value)
    assert min_value <= result <= max_value, f"Result {result} is not within range {min_value}-{max_value}"

# Test to check large range
def test_generate_random_int_large_range():
    min_value = 1000
    max_value = 2000
    result = generate_random_int(min_value, max_value)
    assert min_value <= result <= max_value, f"Result {result} is not within range {min_value}-{max_value}"

# Test for generate secret key
def test_generate_secret_key_length():
    length = 16
    result = generate_secret_key(length)
    assert len(result) == length * 2, f"Secret key length {len(result)} does not match expected length {length * 2}"

def test_generate_secret_key_different_calls():
    result1 = generate_secret_key()
    result2 = generate_secret_key()
    assert result1 != result2, "Multiple calls to generate_secret_key produced the same result"

def test_generate_secret_key_default_length():
    default_length = 32
    result = generate_secret_key()
    assert len(result) == default_length * 2 , f"Default secret key length {len(result)} does not match expected length {default_length * 2}"
    