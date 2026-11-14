"""
    Name: pyessential.json_utils
    Description: A module providing utility functions for working with JSON.
    Author: Abhishek Kumar
"""

import copy
import dataclasses
import json
import os
import re
import shutil
import uuid
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path, PurePath
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    MutableMapping,
    Sequence,
    Union,
)
from uuid import UUID

__all__ = [
    "json_default",
    "to_json",
    "is_valid_json",
    "safe_loads",
    "prettify_json",
    "minify_json",
    "read_json",
    "write_json",
    "read_jsonl",
    "write_jsonl",
    "append_jsonl",
    "get_by_path",
    "set_by_path",
    "flatten_json",
    "unflatten_json",
    "deep_merge",
    "diff_json",
    "pick_keys",
    "remove_keys",
    "convert_keys",
    "keys_to_snake_case",
    "keys_to_camel_case",
]

#: Anything accepted as a path: a string or a ``pathlib.Path`` (or other path-like object).
PathLike = Union[str, "os.PathLike[str]"]

_MISSING = object()


# ---------------------------------------------------------------- helpers
def _write_text(target: Path, chunks: Iterable[str], encoding: str, atomic: bool) -> None:
    """Write text to ``target``; with ``atomic`` the file is replaced only once fully written."""
    if not atomic:
        with open(target, "w", encoding=encoding, newline="\n") as handle:
            for chunk in chunks:
                handle.write(chunk)
        return

    temp = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    try:
        with open(temp, "w", encoding=encoding, newline="\n") as handle:
            for chunk in chunks:
                handle.write(chunk)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            shutil.copymode(target, temp)  # keep the permissions of the file being replaced
        except OSError:
            pass  # the target does not exist yet
        os.replace(temp, target)
    except BaseException:
        try:
            temp.unlink()
        except OSError:
            pass
        raise


def _prepare_target(path: PathLike, create_folders: bool) -> Path:
    target = Path(path)
    if create_folders:
        target.parent.mkdir(parents=True, exist_ok=True)
    return target


def _split_path(path: Union[str, Sequence[Any]], sep: str) -> List[Any]:
    if isinstance(path, str):
        return path.split(sep) if path else []
    return list(path)


def _step(current: Any, key: Any) -> Any:
    """Return the child of ``current`` stored under ``key``, or ``_MISSING``."""
    if isinstance(current, Mapping):
        if key in current:
            return current[key]
        if not isinstance(key, str) and str(key) in current:
            return current[str(key)]
        return _MISSING
    if isinstance(current, (list, tuple)):
        try:
            index = int(key)
        except (TypeError, ValueError):
            return _MISSING
        try:
            return current[index]
        except IndexError:
            return _MISSING
    return _MISSING


# ------------------------------------------------------------ serializing
def json_default(obj: Any) -> Any:
    """Convert common Python objects that ``json`` cannot handle on its own.

    Pass it as the ``default`` argument of ``json.dumps``. It is also what :func:`to_json`
    and :func:`write_json` use by default.

    ==========================  =====================================================
    Python object               JSON value
    ==========================  =====================================================
    ``datetime``, ``date``,     ISO 8601 string, e.g. ``"2026-10-31T13:22:36"``
    ``time``
    ``timedelta``               number of seconds (float)
    ``Decimal``                 string, so no precision is lost
    ``UUID``                    string
    ``Path`` / ``PurePath``     string with forward slashes
    ``Enum``                    the member's value
    ``set`` / ``frozenset``     list (sorted when the items can be compared)
    dataclass instance          dict of its fields
    ==========================  =====================================================

    Args:
        obj: The object to convert.

    Returns:
        A JSON-serializable value.

    Raises:
        TypeError: If the object type is not supported.
    """
    if isinstance(obj, (datetime, date, time)):
        return obj.isoformat()
    if isinstance(obj, timedelta):
        return obj.total_seconds()
    if isinstance(obj, PurePath):
        return obj.as_posix()
    if isinstance(obj, (Decimal, UUID)):
        return str(obj)
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (set, frozenset)):
        try:
            return sorted(obj)
        except TypeError:
            return list(obj)
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def to_json(
    data: Any,
    *,
    indent: Union[int, None] = None,
    sort_keys: bool = False,
    ensure_ascii: bool = False,
    default: Callable[[Any], Any] = json_default,
) -> str:
    """Convert data to a JSON string, handling dates, UUIDs, sets and more.

    Args:
        data: The data to convert.
        indent (int, optional): Indent size for pretty output. Default is None (one line).
        sort_keys (bool): Sort dictionary keys. Default is False.
        ensure_ascii (bool): Escape non-ASCII characters as ``\\uXXXX``. Default is False,
            so ``"é"`` stays ``"é"``.
        default (Callable): Converter for unsupported objects. Default is :func:`json_default`.

    Returns:
        str: The JSON text.

    Raises:
        TypeError: If ``data`` contains an object that ``default`` cannot convert.
    """
    return json.dumps(
        data, indent=indent, sort_keys=sort_keys, ensure_ascii=ensure_ascii, default=default
    )


# ---------------------------------------------------------------- strings
def is_valid_json(text: Union[str, bytes, bytearray]) -> bool:
    """Check whether a string is valid JSON.

    Args:
        text (str | bytes): The text to check.

    Returns:
        bool: True if ``text`` can be parsed. Anything that is not text gives False.
    """
    try:
        json.loads(text)
    except (ValueError, TypeError, RecursionError):
        return False
    return True


def safe_loads(text: Union[str, bytes, bytearray], default: Any = None) -> Any:
    """Parse JSON, returning ``default`` instead of raising when it is invalid.

    Args:
        text (str | bytes): The JSON text.
        default: Value returned when ``text`` is not valid JSON. Default is None.

    Returns:
        The parsed data, or ``default``.
    """
    try:
        return json.loads(text)
    except (ValueError, TypeError, RecursionError):
        return default


def prettify_json(
    text: Union[str, bytes, bytearray],
    *,
    indent: int = 2,
    sort_keys: bool = False,
    ensure_ascii: bool = False,
) -> str:
    """Re-format JSON text so it is easy to read.

    Args:
        text (str | bytes): The JSON text.
        indent (int): Indent size. Default is 2.
        sort_keys (bool): Sort dictionary keys. Default is False.
        ensure_ascii (bool): Escape non-ASCII characters. Default is False.

    Returns:
        str: The formatted JSON.

    Raises:
        ValueError: If ``text`` is not valid JSON (``json.JSONDecodeError`` is a ``ValueError``).
    """
    return to_json(json.loads(text), indent=indent, sort_keys=sort_keys, ensure_ascii=ensure_ascii)


def minify_json(text: Union[str, bytes, bytearray], *, ensure_ascii: bool = False) -> str:
    """Remove all unnecessary whitespace from JSON text.

    Args:
        text (str | bytes): The JSON text.
        ensure_ascii (bool): Escape non-ASCII characters. Default is False.

    Returns:
        str: The compact JSON.

    Raises:
        ValueError: If ``text`` is not valid JSON.
    """
    return json.dumps(json.loads(text), separators=(",", ":"), ensure_ascii=ensure_ascii)


# ------------------------------------------------------------------ files
def read_json(
    path: PathLike, *, encoding: str = "utf-8-sig", default: Any = _MISSING
) -> Any:
    """Read and parse a JSON file.

    Args:
        path (str | Path): The file to read.
        encoding (str): File encoding. Default is ``"utf-8-sig"``, which reads UTF-8 files
            with or without a byte order mark (BOM).
        default: If given, returned when the file does not exist. Invalid JSON still raises.

    Returns:
        The parsed data.

    Raises:
        FileNotFoundError: If the file does not exist and no ``default`` was given.
        ValueError: If the file does not contain valid JSON.
    """
    try:
        with open(path, "r", encoding=encoding) as handle:
            return json.load(handle)
    except FileNotFoundError:
        if default is _MISSING:
            raise
        return default


def write_json(
    path: PathLike,
    data: Any,
    *,
    indent: Union[int, None] = 2,
    sort_keys: bool = False,
    ensure_ascii: bool = False,
    encoding: str = "utf-8",
    default: Callable[[Any], Any] = json_default,
    create_folders: bool = True,
    atomic: bool = True,
) -> Path:
    """Write data to a JSON file.

    The data is converted before the file is touched, so data that cannot be serialized never
    damages an existing file. With ``atomic=True`` (the default) the new content is written to a
    temporary file first and then swapped in, so a crash or a full disk cannot leave a
    half-written file behind. The file ends with a newline and always uses ``\\n`` line endings.

    Args:
        path (str | Path): The file to write.
        data: The data to write.
        indent (int, optional): Indent size. Default is 2. Use None for a single line.
        sort_keys (bool): Sort dictionary keys. Default is False.
        ensure_ascii (bool): Escape non-ASCII characters. Default is False.
        encoding (str): File encoding. Default is ``"utf-8"``.
        default (Callable): Converter for unsupported objects. Default is :func:`json_default`.
        create_folders (bool): Create missing parent folders. Default is True.
        atomic (bool): Replace the file atomically. Default is True.

    Returns:
        Path: The file that was written.

    Raises:
        TypeError: If ``data`` contains an object that ``default`` cannot convert.
        FileNotFoundError: If a parent folder is missing and ``create_folders`` is False.
    """
    text = to_json(
        data, indent=indent, sort_keys=sort_keys, ensure_ascii=ensure_ascii, default=default
    )
    target = _prepare_target(path, create_folders)
    _write_text(target, [text, "\n"], encoding, atomic)
    return target


def read_jsonl(path: PathLike, *, encoding: str = "utf-8-sig") -> Iterator[Any]:
    """Read a JSON Lines file (one JSON value per line), one item at a time.

    Items are produced lazily, so large files do not have to fit in memory. Blank lines are
    skipped.

    Args:
        path (str | Path): The file to read.
        encoding (str): File encoding. Default is ``"utf-8-sig"``.

    Returns:
        Iterator: An iterator over the parsed items.

    Raises:
        FileNotFoundError: If the file does not exist (raised immediately, not on first use).
        ValueError: While iterating, if a line is not valid JSON. The message includes the
            line number.
    """
    file = Path(path)
    if not file.is_file():
        raise FileNotFoundError(f"File not found: {file}")
    return _iter_jsonl(file, encoding)


def _iter_jsonl(file: Path, encoding: str) -> Iterator[Any]:
    with open(file, "r", encoding=encoding) as handle:
        for number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON on line {number} of {file}: {error.msg}") from error


def write_jsonl(
    path: PathLike,
    items: Iterable[Any],
    *,
    sort_keys: bool = False,
    ensure_ascii: bool = False,
    encoding: str = "utf-8",
    default: Callable[[Any], Any] = json_default,
    create_folders: bool = True,
    atomic: bool = True,
) -> int:
    """Write items to a JSON Lines file, one JSON value per line.

    ``items`` can be any iterable, including a generator, and is written one item at a time.
    With ``atomic=True`` (the default) an existing file is only replaced once every item has
    been written successfully.

    Args:
        path (str | Path): The file to write.
        items (Iterable): The items to write.
        sort_keys (bool): Sort dictionary keys. Default is False.
        ensure_ascii (bool): Escape non-ASCII characters. Default is False.
        encoding (str): File encoding. Default is ``"utf-8"``.
        default (Callable): Converter for unsupported objects. Default is :func:`json_default`.
        create_folders (bool): Create missing parent folders. Default is True.
        atomic (bool): Replace the file atomically. Default is True.

    Returns:
        int: The number of items written.

    Raises:
        TypeError: If an item contains an object that ``default`` cannot convert.
    """
    target = _prepare_target(path, create_folders)
    count = 0

    def lines() -> Iterator[str]:
        nonlocal count
        for item in items:
            yield to_json(item, sort_keys=sort_keys, ensure_ascii=ensure_ascii, default=default)
            yield "\n"
            count += 1

    _write_text(target, lines(), encoding, atomic)
    return count


def append_jsonl(
    path: PathLike,
    item: Any,
    *,
    sort_keys: bool = False,
    ensure_ascii: bool = False,
    encoding: str = "utf-8",
    default: Callable[[Any], Any] = json_default,
    create_folders: bool = True,
) -> None:
    """Append one item as a new line to a JSON Lines file, creating the file if needed.

    Args:
        path (str | Path): The file to append to.
        item: The item to add.
        sort_keys (bool): Sort dictionary keys. Default is False.
        ensure_ascii (bool): Escape non-ASCII characters. Default is False.
        encoding (str): File encoding. Default is ``"utf-8"``.
        default (Callable): Converter for unsupported objects. Default is :func:`json_default`.
        create_folders (bool): Create missing parent folders. Default is True.

    Raises:
        TypeError: If ``item`` contains an object that ``default`` cannot convert.
    """
    line = to_json(item, sort_keys=sort_keys, ensure_ascii=ensure_ascii, default=default)
    target = _prepare_target(path, create_folders)
    with open(target, "a", encoding=encoding, newline="\n") as handle:
        handle.write(line + "\n")


# ------------------------------------------------------------ nested data
def get_by_path(
    data: Any, path: Union[str, Sequence[Any]], default: Any = None, *, sep: str = "."
) -> Any:
    """Get a value from nested dictionaries and lists using a path.

    Args:
        data: The nested data.
        path (str | Sequence): A path such as ``"user.addresses.0.city"``, or a list of keys
            such as ``["user", "addresses", 0, "city"]`` when keys contain the separator.
            An empty path returns ``data`` itself.
        default: Returned when any part of the path does not exist. Default is None.
        sep (str): Separator used in a string path. Default is ``"."``.

    Returns:
        The value found, or ``default``.
    """
    current = data
    for key in _split_path(path, sep):
        current = _step(current, key)
        if current is _MISSING:
            return default
    return current


def set_by_path(
    data: Any, path: Union[str, Sequence[Any]], value: Any, *, sep: str = "."
) -> Any:
    """Set a value in nested dictionaries and lists using a path, in place.

    Missing dictionary keys along the way are created as new dictionaries. Lists are never
    extended: a list index must already exist.

    Args:
        data: The nested data to change.
        path (str | Sequence): The path to set, in the same form as :func:`get_by_path`.
        value: The value to store.
        sep (str): Separator used in a string path. Default is ``"."``.

    Returns:
        ``data``, the same object that was passed in.

    Raises:
        ValueError: If ``path`` is empty.
        TypeError: If the path goes through a value that is not a dict or a list, or a list
            is addressed with a non-integer index.
        IndexError: If a list index is out of range.
    """
    keys = _split_path(path, sep)
    if not keys:
        raise ValueError("path must not be empty")

    current = data
    for key in keys[:-1]:
        child = _step(current, key)
        if child is _MISSING:
            if isinstance(current, MutableMapping):
                child = {}
                current[key] = child
            elif isinstance(current, list):
                raise IndexError(f"{key!r} is not a valid list index")
            else:
                raise TypeError(f"Cannot step into {type(current).__name__} at {key!r}")
        elif not isinstance(child, (MutableMapping, list)):
            raise TypeError(f"Cannot set a value inside {type(child).__name__} at {key!r}")
        current = child

    last = keys[-1]
    if isinstance(current, MutableMapping):
        current[last] = value
    elif isinstance(current, list):
        try:
            index = int(last)
        except (TypeError, ValueError):
            raise TypeError(f"List index must be an integer, got {last!r}") from None
        current[index] = value
    else:
        raise TypeError(f"Cannot set a value inside {type(current).__name__}")
    return data


def flatten_json(data: Union[Mapping, list, tuple], *, sep: str = ".") -> Dict[str, Any]:
    """Flatten nested dictionaries and lists into one level of ``path: value`` pairs.

    Empty dictionaries and lists are kept as values, so :func:`unflatten_json` can rebuild
    the original structure.

    Args:
        data (dict | list): The nested data.
        sep (str): Separator placed between path parts. Default is ``"."``.

    Returns:
        dict: Flat dictionary, e.g. ``{"a.b": 1, "a.c.0": 2}``. An empty ``data`` gives ``{}``.

    Raises:
        TypeError: If ``data`` is not a dict or a list.
    """
    if not isinstance(data, (Mapping, list, tuple)):
        raise TypeError("flatten_json expects a dict or a list")

    flat: Dict[str, Any] = {}

    def walk(value: Any, prefix: Union[str, None]) -> None:
        if isinstance(value, Mapping) and value:
            pairs = [(str(key), child) for key, child in value.items()]
        elif isinstance(value, (list, tuple)) and value:
            pairs = [(str(index), child) for index, child in enumerate(value)]
        else:
            flat[prefix] = value  # type: ignore[index]
            return
        for key, child in pairs:
            walk(child, key if prefix is None else f"{prefix}{sep}{key}")

    if data:
        walk(data, None)
    return flat


class _Node(dict):
    """Intermediate dictionary created while rebuilding data in :func:`unflatten_json`."""


def unflatten_json(flat: Mapping[str, Any], *, sep: str = ".") -> Any:
    """Rebuild nested data from the output of :func:`flatten_json`.

    Path parts that are the whole numbers ``0, 1, 2, ...`` (with none missing) become a list;
    everything else becomes a dictionary. A dictionary whose keys really are ``"0"``, ``"1"``
    therefore comes back as a list.

    Args:
        flat (dict): Flat dictionary of ``path: value`` pairs.
        sep (str): Separator used in the paths. Default is ``"."``.

    Returns:
        The nested data (a dict, or a list when the top-level paths are ``0, 1, 2, ...``).

    Raises:
        ValueError: If two paths conflict, such as ``"a"`` together with ``"a.b"``.
    """
    root = _Node()
    for key, value in flat.items():
        parts = key.split(sep)
        node = root
        for part in parts[:-1]:
            node = node.setdefault(part, _Node())
            if not isinstance(node, _Node):
                raise ValueError(f"Conflicting paths at {key!r}")
        if parts[-1] in node:
            raise ValueError(f"Conflicting paths at {key!r}")
        node[parts[-1]] = value

    def finalize(node: Any) -> Any:
        if not isinstance(node, _Node):
            return node
        items = {key: finalize(child) for key, child in node.items()}
        if items and set(items) == {str(i) for i in range(len(items))}:
            return [items[str(i)] for i in range(len(items))]
        return items

    return finalize(root)


def deep_merge(base: Mapping, *others: Mapping, lists: str = "replace") -> Dict[str, Any]:
    """Merge dictionaries recursively into a new dictionary.

    Later dictionaries win. Nested dictionaries are merged key by key instead of being
    replaced. None of the inputs is changed.

    Args:
        base (dict): The starting dictionary.
        *others (dict): Dictionaries merged on top, in order.
        lists (str): What to do when both sides have a list: ``"replace"`` (default) uses the
            later list, ``"extend"`` joins them.

    Returns:
        dict: The merged copy.

    Raises:
        ValueError: If ``lists`` is not ``"replace"`` or ``"extend"``.
    """
    if lists not in ("replace", "extend"):
        raise ValueError('lists must be "replace" or "extend"')

    def merge_into(target: MutableMapping, source: Mapping) -> None:
        for key, value in source.items():
            current = target.get(key)
            if isinstance(current, MutableMapping) and isinstance(value, Mapping):
                merge_into(current, value)
            elif lists == "extend" and isinstance(current, list) and isinstance(value, list):
                target[key] = current + copy.deepcopy(value)
            else:
                target[key] = copy.deepcopy(value)

    result = copy.deepcopy(dict(base))
    for other in others:
        merge_into(result, other)
    return result


def _differs(left: Any, right: Any) -> bool:
    if isinstance(left, bool) != isinstance(right, bool):
        return True  # JSON true is not the number 1
    return left != right


def diff_json(old: Union[Mapping, list, tuple], new: Union[Mapping, list, tuple], *, sep: str = ".") -> Dict[str, Dict[str, Any]]:
    """Compare two JSON documents and report what changed.

    Both documents are compared by their flattened paths (see :func:`flatten_json`).

    Args:
        old (dict | list): The original data.
        new (dict | list): The new data.
        sep (str): Separator used in the reported paths. Default is ``"."``.

    Returns:
        dict: ``{"added": {path: value}, "removed": {path: value}, "changed": {path: (old, new)}}``.
        All three keys are always present. Identical documents give three empty dicts.

    Raises:
        TypeError: If either document is not a dict or a list.
    """
    before = flatten_json(old, sep=sep)
    after = flatten_json(new, sep=sep)
    return {
        "added": {key: after[key] for key in after if key not in before},
        "removed": {key: before[key] for key in before if key not in after},
        "changed": {
            key: (before[key], after[key])
            for key in before
            if key in after and _differs(before[key], after[key])
        },
    }


# ------------------------------------------------------------------- keys
def pick_keys(data: Mapping, keys: Iterable[str]) -> Dict[str, Any]:
    """Keep only the listed keys of a dictionary.

    Args:
        data (dict): The source dictionary.
        keys (Iterable[str]): The keys to keep. Keys that are not in ``data`` are ignored.

    Returns:
        dict: A new dictionary (values are not copied) in the original key order.
    """
    wanted = set(keys)
    return {key: value for key, value in data.items() if key in wanted}


def remove_keys(data: Any, keys: Iterable[str], *, recursive: bool = True) -> Any:
    """Remove keys from a dictionary, for example secrets before logging.

    Args:
        data: A dictionary, or any nested data containing dictionaries.
        keys (Iterable[str]): The keys to remove.
        recursive (bool): Also remove the keys inside nested dictionaries and lists. Default
            is True. When False, only the top level of a dictionary is cleaned.

    Returns:
        A new structure without the keys. The input is not changed. Tuples become lists.
    """
    unwanted = set(keys)

    def clean(value: Any) -> Any:
        if isinstance(value, Mapping):
            return {k: clean(v) for k, v in value.items() if k not in unwanted}
        if isinstance(value, (list, tuple)):
            return [clean(item) for item in value]
        return value

    if recursive:
        return clean(data)
    if isinstance(data, Mapping):
        return {k: v for k, v in data.items() if k not in unwanted}
    return data


def convert_keys(data: Any, func: Callable[[str], str], *, recursive: bool = True) -> Any:
    """Rename every dictionary key with a function.

    Args:
        data: A dictionary, or any nested data containing dictionaries.
        func (Callable[[str], str]): Takes a key and returns the new key, e.g. ``str.lower``.
        recursive (bool): Also rename keys inside nested dictionaries and lists. Default is
            True. When False, only the top level of a dictionary is renamed.

    Returns:
        A new structure with renamed keys. The input is not changed. Tuples become lists.
        If two keys end up with the same name, the later one wins.
    """

    def convert(value: Any) -> Any:
        if isinstance(value, Mapping):
            return {
                (func(k) if isinstance(k, str) else k): (convert(v) if recursive else v)
                for k, v in value.items()
            }
        if recursive and isinstance(value, (list, tuple)):
            return [convert(item) for item in value]
        return value

    return convert(data)


_SNAKE_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def _to_snake(name: str) -> str:
    return _SNAKE_BOUNDARY.sub("_", name).lower()


def _to_camel(name: str) -> str:
    stripped = name.lstrip("_")
    prefix = name[: len(name) - len(stripped)]  # keep leading underscores such as "_id"
    first, *rest = stripped.split("_")
    return prefix + first + "".join(part[:1].upper() + part[1:] for part in rest)


def keys_to_snake_case(data: Any, *, recursive: bool = True) -> Any:
    """Rename every key from ``camelCase`` to ``snake_case``.

    ``userID`` becomes ``user_id`` and ``HTTPServer`` becomes ``http_server``. Keys that are
    already in snake case are left unchanged.

    Args:
        data: A dictionary, or any nested data containing dictionaries.
        recursive (bool): Also rename nested keys. Default is True.

    Returns:
        A new structure with renamed keys.
    """
    return convert_keys(data, _to_snake, recursive=recursive)


def keys_to_camel_case(data: Any, *, recursive: bool = True) -> Any:
    """Rename every key from ``snake_case`` to ``camelCase``.

    ``user_id`` becomes ``userId``. Leading underscores are kept, so ``_id`` stays ``_id``.

    Args:
        data: A dictionary, or any nested data containing dictionaries.
        recursive (bool): Also rename nested keys. Default is True.

    Returns:
        A new structure with renamed keys.
    """
    return convert_keys(data, _to_camel, recursive=recursive)