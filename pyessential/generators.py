"""
    Name: pyessential.generators
    Description: A module providing utility functions for generating random data.
    Author: Abhishek Kumar
"""

import secrets

def generate_random_int(min_value=0, max_value=100):
    """Generate a random integer within a specified range.

    Args:
        min_value (int): The minimum value of the range. Default is 0.
        max_value (int): The maximum value of the range. Default is 100.

    Returns:
        int: A randomly generated integer within the specified range.
    """
    return secrets.randbelow(max_value - min_value + 1) + min_value


def generate_secret_key(length=32):
    """Generate a secure random secret key.

    Args:
        length (int): The length of the secret key. Default is 32.

    Returns:
        str: A securely generated random secret key.
    """
    return secrets.token_hex(length)