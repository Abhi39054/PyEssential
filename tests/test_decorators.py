# tests/test_decorators.py
import time
from pyessential.decorators import timeit

# Example: Simple test to ensure the function returns correctly
def test_time_it_returns_correct_value():
    @timeit
    def add(a, b):
        return a + b

    # Check if the result is correct
    assert add(2, 3) == 5

# Example: Test with some time delay
def test_time_it_execution_time(capsys):
    @timeit
    def sleep_a_bit():
        time.sleep(0.01)

    sleep_a_bit()

    captured = capsys.readouterr()
    assert "executed in" in captured.out