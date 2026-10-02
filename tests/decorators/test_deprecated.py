import pytest

from pyessential.decorators import deprecated


def test_function_warns_and_still_works():
    @deprecated("use new_func instead", version="0.2.0")
    def old(x):
        return x * 2

    with pytest.warns(DeprecationWarning, match="use new_func instead"):
        assert old(3) == 6


def test_preserves_metadata():
    @deprecated("nope")
    def old():
        """Docstring."""

    assert old.__name__ == "old"
    assert old.__doc__ == "Docstring."


def test_class_warns_on_instantiation():
    @deprecated("use NewClient instead")
    class Old:
        def __init__(self, value):
            self.value = value

    with pytest.warns(DeprecationWarning, match="NewClient"):
        obj = Old(5)
    assert obj.value == 5


def test_custom_category():
    @deprecated("gone soon", category=FutureWarning)
    def old():
        pass

    with pytest.warns(FutureWarning):
        old()