# JSON utilities

Helpers for reading, writing, converting and reshaping JSON, built on Python's standard `json`
module. Dates, UUIDs, sets and similar types are handled for you, files are written safely, and
nested data is easy to look up, merge and compare.

```python
from pyessential.json_utils import read_json, write_json
```

> The module is called `json_utils`, not `json`, so it can never shadow Python's own `json`
> module.

## Functions

**Files**

| Function | Description |
|---|---|
| [`read_json(path, ...)`](#read_json) | Read and parse a JSON file. |
| [`write_json(path, data, ...)`](#write_json) | Write data to a JSON file safely. |
| [`read_jsonl(path, ...)`](#read_jsonl) | Read a JSON Lines file one item at a time. |
| [`write_jsonl(path, items, ...)`](#write_jsonl) | Write items to a JSON Lines file. |
| [`append_jsonl(path, item, ...)`](#append_jsonl) | Add one item to a JSON Lines file. |

**Strings**

| Function | Description |
|---|---|
| [`to_json(data, ...)`](#to_json) | Convert data to a JSON string, including dates, UUIDs, sets and more. |
| [`json_default(obj)`](#json_default) | The converter used by `to_json`; also usable with `json.dumps`. |
| [`is_valid_json(text)`](#is_valid_json) | Check whether text is valid JSON. |
| [`safe_loads(text, default=None)`](#safe_loads) | Parse JSON without raising on bad input. |
| [`prettify_json(text, ...)`](#prettify_json) | Re-format JSON text so it is readable. |
| [`minify_json(text, ...)`](#minify_json) | Remove all unnecessary whitespace. |

**Nested data**

| Function | Description |
|---|---|
| [`get_by_path(data, path, default=None)`](#get_by_path) | Read a value with a path like `"user.addresses.0.city"`. |
| [`set_by_path(data, path, value)`](#set_by_path) | Set a value with a path, creating dictionaries as needed. |
| [`flatten_json(data)`](#flatten_json) | Turn nested data into flat `path: value` pairs. |
| [`unflatten_json(flat)`](#unflatten_json) | Rebuild nested data from flat pairs. |
| [`deep_merge(base, *others)`](#deep_merge) | Merge dictionaries recursively into a new one. |
| [`diff_json(old, new)`](#diff_json) | Report what was added, removed or changed. |

**Keys**

| Function | Description |
|---|---|
| [`pick_keys(data, keys)`](#pick_keys) | Keep only the listed keys. |
| [`remove_keys(data, keys)`](#remove_keys) | Remove keys at any depth, such as secrets. |
| [`convert_keys(data, func)`](#convert_keys) | Rename every key with a function. |
| [`keys_to_snake_case(data)`](#keys_to_snake_case) | `userName` to `user_name`. |
| [`keys_to_camel_case(data)`](#keys_to_camel_case) | `user_name` to `userName`. |

---

## Files

### `read_json`

```python
read_json(path, *, encoding="utf-8-sig", default=<not set>) -> Any
```

Reads and parses a JSON file. The default encoding reads UTF-8 files with or without a byte
order mark (BOM), which Windows editors often add.

| Parameter | Description |
|---|---|
| `path` | The file to read (`str` or `Path`). |
| `encoding` | File encoding. Default `"utf-8-sig"`. |
| `default` | If given, returned when the file does not exist. Invalid JSON still raises. |

**Raises** `FileNotFoundError` if the file is missing and no `default` was given, and
`ValueError` if the file is not valid JSON.

```python
config = read_json("config.json")
config = read_json("config.json", default={})   # {} if the file is missing
```

### `write_json`

```python
write_json(path, data, *, indent=2, sort_keys=False, ensure_ascii=False, encoding="utf-8",
           default=json_default, create_folders=True, atomic=True) -> Path
```

Writes data to a JSON file and returns the file's `Path`.

- **Safe.** The data is converted first, so data that can't be serialized never damages an
  existing file. With `atomic=True` the content goes to a temporary file that is swapped in once
  complete, so a crash or full disk can't leave a half-written file. The permissions of an
  existing file are kept.
- **Readable.** Output is indented, ends with a newline, always uses `\n` line endings, and keeps
  non-ASCII characters as they are (`"café"`, not `"caf\u00e9"`).
- **Convenient.** Missing parent folders are created, and dates, UUIDs, sets and similar types
  are converted (see [`json_default`](#json_default)).

| Parameter | Description |
|---|---|
| `indent` | Indent size. Default `2`. Use `None` for a single line. |
| `sort_keys` | Sort dictionary keys. Default `False`. |
| `ensure_ascii` | Escape non-ASCII characters. Default `False`. |
| `default` | Converter for unsupported objects. Default `json_default`. |
| `create_folders` | Create missing parent folders. Default `True`. |
| `atomic` | Replace the file atomically. Default `True`. |

**Raises** `TypeError` if the data contains an object that can't be converted, and
`FileNotFoundError` if a parent folder is missing and `create_folders` is `False`.

```python
from datetime import datetime

write_json("data/config.json", {"name": "café", "created": datetime(2026, 10, 31, 13, 22)})
read_json("data/config.json")
# {'name': 'café', 'created': '2026-10-31T13:22:00'}
```

### `read_jsonl`

```python
read_jsonl(path, *, encoding="utf-8-sig") -> Iterator[Any]
```

Reads a [JSON Lines](https://jsonlines.org/) file, which holds one JSON value per line. Items are
produced one at a time, so large files don't have to fit in memory. Blank lines are skipped.

**Raises** `FileNotFoundError` immediately if the file is missing (you don't have to start
iterating first), and `ValueError` while iterating if a line is not valid JSON. The message
includes the line number.

```python
for event in read_jsonl("events.jsonl"):
    print(event["id"])
```

```python
list(read_jsonl("bad.jsonl"))
# ValueError: Invalid JSON on line 2 of bad.jsonl: Expecting property name enclosed in double quotes
```

### `write_jsonl`

```python
write_jsonl(path, items, *, sort_keys=False, ensure_ascii=False, encoding="utf-8",
            default=json_default, create_folders=True, atomic=True) -> int
```

Writes any iterable, including a generator, to a JSON Lines file, one item per line, and returns
the number of items written. With `atomic=True` an existing file is only replaced once every item
has been written successfully.

```python
write_jsonl("events.jsonl", [{"id": 1}, {"id": 2}])   # 2
write_jsonl("squares.jsonl", ({"n": n, "square": n * n} for n in range(1000)))
```

### `append_jsonl`

```python
append_jsonl(path, item, *, sort_keys=False, ensure_ascii=False, encoding="utf-8",
             default=json_default, create_folders=True) -> None
```

Adds one item as a new line, creating the file (and folders) if needed. An item that can't be
serialized is not written. Useful for event logs.

```python
append_jsonl("events.jsonl", {"id": 3})
list(read_jsonl("events.jsonl"))
# [{'id': 1}, {'id': 2}, {'id': 3}]
```

---

## Strings

### `to_json`

```python
to_json(data, *, indent=None, sort_keys=False, ensure_ascii=False, default=json_default) -> str
```

Like `json.dumps`, but handles dates, UUIDs, sets and more, and keeps non-ASCII characters
readable.

```python
from datetime import date
from decimal import Decimal

to_json({"when": date(2026, 10, 31), "price": Decimal("19.99"), "tags": {"b", "a"}})
# '{"when": "2026-10-31", "price": "19.99", "tags": ["a", "b"]}'
```

**Raises** `TypeError` if an object can't be converted.

### `json_default`

```python
json_default(obj) -> Any
```

Converts common Python objects that `json` can't handle. Pass it as `default=` to `json.dumps`,
or let `to_json`, `write_json` and the JSONL writers use it for you.

| Python object | JSON value |
|---|---|
| `datetime`, `date`, `time` | ISO 8601 string, e.g. `"2026-10-31T13:22:36"` |
| `timedelta` | number of seconds (float) |
| `Decimal` | string, so no precision is lost |
| `UUID` | string |
| `Path` / `PurePath` | string with forward slashes |
| `Enum` | the member's value |
| `set` / `frozenset` | list (sorted when the items can be compared) |
| dataclass instance | dictionary of its fields |

Anything else raises `TypeError`.

```python
import json
json.dumps({"id": uuid.uuid4()}, default=json_default)
```

### `is_valid_json`

```python
is_valid_json(text) -> bool
```

True if `text` (a `str` or `bytes`) parses as JSON. Anything that isn't text gives `False`.

```python
is_valid_json('{"a": 1}')   # True
is_valid_json("{oops")      # False
```

### `safe_loads`

```python
safe_loads(text, default=None) -> Any
```

Parses JSON and returns `default` instead of raising when the input is invalid.

```python
safe_loads("{oops")                # None
safe_loads("{oops", default={})    # {}
```

### `prettify_json`

```python
prettify_json(text, *, indent=2, sort_keys=False, ensure_ascii=False) -> str
```

Re-formats JSON text. Raises `ValueError` if the text isn't valid JSON.

```python
print(prettify_json('{"b":1,"a":[1,2]}', sort_keys=True))
# {
#   "a": [
#     1,
#     2
#   ],
#   "b": 1
# }
```

### `minify_json`

```python
minify_json(text, *, ensure_ascii=False) -> str
```

Removes all unnecessary whitespace. Raises `ValueError` if the text isn't valid JSON.

```python
minify_json('{ "a" : 1, "b" : [1, 2] }')
# '{"a":1,"b":[1,2]}'
```

---

## Nested data

Paths are written like `"user.addresses.0.city"`. Numbers address list positions, including
negative ones (`-1` is the last item). If a key contains the separator, pass the path as a list
(`["a.b", "c"]`) or choose another `sep`.

### `get_by_path`

```python
get_by_path(data, path, default=None, *, sep=".") -> Any
```

Returns the value at `path`, or `default` if any part of the path doesn't exist. Values such as
`0`, `""` and `None` that are really there are returned, not replaced by `default`. An empty path
returns `data` itself.

```python
data = {"user": {"name": "Ada", "addresses": [{"city": "London"}, {"city": "Paris"}]}}

get_by_path(data, "user.addresses.1.city")   # 'Paris'
get_by_path(data, "user.age", default=0)     # 0
```

### `set_by_path`

```python
set_by_path(data, path, value, *, sep=".") -> Any
```

Sets the value at `path` **in place** and returns `data`. Missing dictionary keys along the way
are created. Lists are never extended, so a list index must already exist.

```python
set_by_path(data, "user.settings.theme", "dark")
data["user"]["settings"]
# {'theme': 'dark'}
```

**Raises** `ValueError` for an empty path, `TypeError` if the path goes through a value that is
not a dict or list (or uses a non-integer list index), and `IndexError` for a list index out of
range.

### `flatten_json`

```python
flatten_json(data, *, sep=".") -> dict
```

Turns nested dictionaries and lists into one level of `path: value` pairs. Empty dictionaries and
lists are kept as values, so the result can be turned back with `unflatten_json`. Raises
`TypeError` if `data` is not a dict or list.

```python
flat = flatten_json({"a": 1, "b": {"c": 2, "d": [3, 4]}})
# {'a': 1, 'b.c': 2, 'b.d.0': 3, 'b.d.1': 4}
```

### `unflatten_json`

```python
unflatten_json(flat, *, sep=".") -> Any
```

Rebuilds nested data. Path parts that are the numbers `0, 1, 2, ...` with none missing become a
list; everything else becomes a dictionary.

```python
unflatten_json(flat)
# {'a': 1, 'b': {'c': 2, 'd': [3, 4]}}
```

Because of that rule, a dictionary whose keys are really `"0"` and `"1"` comes back as a list.
Raises `ValueError` if paths conflict, such as `"a"` together with `"a.b"`.

### `deep_merge`

```python
deep_merge(base, *others, lists="replace") -> dict
```

Merges dictionaries recursively into a **new** dictionary; none of the inputs is changed. Later
dictionaries win, and nested dictionaries are merged key by key instead of being replaced.

| `lists` | When both sides have a list |
|---|---|
| `"replace"` (default) | the later list is used |
| `"extend"` | the lists are joined |

```python
defaults = {"db": {"host": "localhost", "port": 5432}, "tags": ["a"]}
overrides = {"db": {"port": 5433}, "tags": ["b"]}

deep_merge(defaults, overrides)
# {'db': {'host': 'localhost', 'port': 5433}, 'tags': ['b']}

deep_merge(defaults, overrides, lists="extend")["tags"]
# ['a', 'b']
```

Raises `ValueError` for any other `lists` value.

### `diff_json`

```python
diff_json(old, new, *, sep=".") -> dict
```

Compares two documents by their flattened paths and reports what changed. All three keys are
always present. Lists are compared by position, and JSON `true` is treated as different from the
number `1`.

```python
diff_json({"a": 1, "b": 2, "c": 3}, {"a": 1, "b": 20, "d": 4})
# {'added': {'d': 4}, 'removed': {'c': 3}, 'changed': {'b': (2, 20)}}
```

---

## Keys

### `pick_keys`

```python
pick_keys(data, keys) -> dict
```

Keeps only the listed keys, in the dictionary's original order. Keys that don't exist are ignored.

```python
pick_keys({"a": 1, "b": 2, "c": 3}, ["a", "c"])
# {'a': 1, 'c': 3}
```

### `remove_keys`

```python
remove_keys(data, keys, *, recursive=True) -> Any
```

Returns a copy without the listed keys, at any depth and inside lists. Handy for hiding secrets
before logging. With `recursive=False` only the top level of a dictionary is cleaned. The input
is not changed, and tuples come back as lists.

```python
remove_keys({"user": "ada", "password": "x", "items": [{"id": 1, "token": "t"}]},
            ["password", "token"])
# {'user': 'ada', 'items': [{'id': 1}]}
```

### `convert_keys`

```python
convert_keys(data, func, *, recursive=True) -> Any
```

Renames every dictionary key with `func`, which takes a key and returns the new one. Values and
non-string keys are left alone. The input is not changed. If two keys end up with the same name,
the later one wins.

```python
convert_keys({"A": {"B": 1}}, str.lower)
# {'a': {'b': 1}}
```

### `keys_to_snake_case`

```python
keys_to_snake_case(data, *, recursive=True) -> Any
```

Renames keys from `camelCase` to `snake_case`. Acronyms are handled sensibly (`userID` becomes
`user_id`, `HTTPServer` becomes `http_server`), and keys already in snake case are unchanged.

```python
keys_to_snake_case({"userName": "ada", "userID": 7, "address": {"zipCode": "N1"}})
# {'user_name': 'ada', 'user_id': 7, 'address': {'zip_code': 'N1'}}
```

### `keys_to_camel_case`

```python
keys_to_camel_case(data, *, recursive=True) -> Any
```

Renames keys from `snake_case` to `camelCase`. Leading underscores are kept, so `_id` stays `_id`.

```python
keys_to_camel_case({"user_name": "ada", "_id": 7})
# {'userName': 'ada', '_id': 7}
```

---

## Notes

- **Large files.** `read_json` and `write_json` load the whole document into memory. The JSONL
  functions stream, so prefer JSON Lines for very large data sets.
- **Python's JSON rules apply.** `json` accepts `NaN` and `Infinity` and `is_valid_json` follows
  it, so those count as valid.
- **Multiple processes.** Atomic writes make each file replacement safe, but if two processes
  write the same file at the same time, the last one wins. Use separate files or your own lock if
  that matters.