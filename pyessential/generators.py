"""
    Name: pyessential.generators
    Description: A module providing utility functions for generating random data.
    Author: Abhishek Kumar
"""

import secrets


def generate_random_int(min_value: int = 0, max_value: int = 100) -> int:
    """Generate a cryptographically secure random integer.

    Both ends of the range are included.

    Args:
        min_value (int): The minimum value of the range. Default is 0.
        max_value (int): The maximum value of the range. Default is 100.

    Returns:
        int: A random integer N such that ``min_value <= N <= max_value``.

    Raises:
        ValueError: If ``min_value`` is greater than ``max_value``.
    """
    if min_value > max_value:
        raise ValueError("min_value must be less than or equal to max_value")
    return secrets.randbelow(max_value - min_value + 1) + min_value


def generate_secret_key(length: int = 32) -> str:
    """Generate a cryptographically secure random secret key.

    Args:
        length (int): Number of random bytes to use. Default is 32. The key is
            returned as a hexadecimal string, so it is ``2 * length`` characters
            long (the default gives a 64-character key).

    Returns:
        str: A random hexadecimal secret key.

    Raises:
        ValueError: If ``length`` is less than 1.
    """
    if length < 1:
        raise ValueError("length must be at least 1")
    return secrets.token_hex(length)