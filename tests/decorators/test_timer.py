# tests/decorators/test_timer.py
import asyncio
import re
import time

import pytest

from pyessential.decorators import timeit


def test_time_it_returns_correct_value():
    @timeit
    def add(a, b):
        return a + b

    assert add(2, 3) == 5


def test_time_it_passes_args_and_kwargs():
    @timeit
    def greet(name, punctuation="!"):
        return f"Hello, {name}{punctuation}"

    assert greet("Abhi", punctuation="?") == "Hello, Abhi?"


def test_time_it_execution_time(capsys):
    @timeit
    def sleep_a_bit():
        time.sleep(0.01)

    sleep_a_bit()

    out = capsys.readouterr().out
    match = re.search(r"\[sleep_a_bit\] executed in (\d+\.\d{4}) seconds\.", out)
    assert match is not None
    assert float(match.group(1)) >= 0.005


def test_time_it_preserves_metadata():
    @timeit
    def documented():
        """My docstring."""

    assert documented.__name__ == "documented"
    assert documented.__doc__ == "My docstring."


def test_time_it_prints_even_on_exception(capsys):
    @timeit
    def boom():
        raise ValueError("fail")

    with pytest.raises(ValueError, match="fail"):
        boom()

    assert "[boom] executed in" in capsys.readouterr().out


def test_time_it_async_returns_value_and_prints(capsys):
    @timeit
    async def nap():
        await asyncio.sleep(0.01)
        return "done"

    assert asyncio.run(nap()) == "done"
    assert "[nap] executed in" in capsys.readouterr().out


def test_time_it_async_prints_even_on_exception(capsys):
    @timeit
    async def async_boom():
        raise RuntimeError("async fail")

    with pytest.raises(RuntimeError, match="async fail"):
        asyncio.run(async_boom())

    assert "[async_boom] executed in" in capsys.readouterr().out