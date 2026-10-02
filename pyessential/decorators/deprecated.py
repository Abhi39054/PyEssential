import functools
import inspect
import warnings


def deprecated(reason="", *, version=None, category=DeprecationWarning):
    """Mark a function or class as deprecated.

    Args:
        reason: Message shown to the caller, e.g. "use new_func instead".
        version: Optional version in which it was deprecated.
        category: Warning class to emit (default: DeprecationWarning).
    """

    def decorator(obj):
        kind = "class" if inspect.isclass(obj) else "function"
        message = f"{kind} '{obj.__qualname__}' is deprecated"
        if version:
            message += f" since version {version}"
        message += "."
        if reason:
            message += f" {reason}"

        if inspect.isclass(obj):
            original_init = obj.__init__

            @functools.wraps(original_init)
            def new_init(self, *args, **kwargs):
                warnings.warn(message, category, stacklevel=2)
                original_init(self, *args, **kwargs)

            obj.__init__ = new_init
            return obj

        @functools.wraps(obj)
        def wrapper(*args, **kwargs):
            warnings.warn(message, category, stacklevel=2)
            return obj(*args, **kwargs)

        return wrapper

    return decorator