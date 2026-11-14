import dataclasses
import json
import os
import stat
import uuid
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path

import pytest

import pyessential.json_utils as json_utils
from pyessential.json_utils import (
    append_jsonl,
    convert_keys,
    deep_merge,
    diff_json,
    flatten_json,
    get_by_path,
    is_valid_json,
    json_default,
    keys_to_camel_case,
    keys_to_snake_case,
    minify_json,
    pick_keys,
    prettify_json,
    read_json,
    read_jsonl,
    remove_keys,
    safe_loads,
    set_by_path,
    to_json,
    unflatten_json,
    write_json,
    write_jsonl,
)


class Color(Enum):
    RED = "red"


@dataclasses.dataclass
class Point:
    x: int
    y: int


def leftovers(folder):
    """Temporary files left behind next to the real ones."""
    return [p.name for p in Path(folder).iterdir() if p.name.endswith(".tmp")]


# ------------------------------------------------------------ serializing
class TestSerializing:
    def test_json_default_converts_common_types(self):
        assert json_default(datetime(2026, 10, 31, 13, 22, 36)) == "2026-10-31T13:22:36"
        assert json_default(date(2026, 10, 31)) == "2026-10-31"
        assert json_default(time(13, 22)) == "13:22:00"
        assert json_default(timedelta(minutes=2)) == 120.0
        assert json_default(Decimal("1.10")) == "1.10"
        u = uuid.uuid4()
        assert json_default(u) == str(u)
        assert json_default(Path("a") / "b") == "a/b"
        assert json_default(Color.RED) == "red"
        assert json_default({3, 1, 2}) == [1, 2, 3]
        assert json_default(Point(1, 2)) == {"x": 1, "y": 2}

    def test_json_default_set_with_mixed_types_still_works(self):
        assert sorted(json_default({1, "a"}), key=str) == [1, "a"]

    def test_json_default_rejects_unknown_objects(self):
        with pytest.raises(TypeError):
            json_default(object())

    def test_to_json_handles_nested_special_types(self):
        text = to_json({"when": date(2026, 1, 2), "id": Decimal("2.5"), "tags": {"b", "a"}})
        assert json.loads(text) == {"when": "2026-01-02", "id": "2.5", "tags": ["a", "b"]}

    def test_to_json_keeps_non_ascii_by_default(self):
        assert to_json({"name": "café"}) == '{"name": "café"}'
        assert "\\u00e9" in to_json({"name": "café"}, ensure_ascii=True)

    def test_to_json_options(self):
        assert to_json({"b": 1, "a": 2}, sort_keys=True) == '{"a": 2, "b": 1}'
        assert to_json({"a": 1}, indent=2) == '{\n  "a": 1\n}'

    def test_to_json_unsupported_object_raises(self):
        with pytest.raises(TypeError):
            to_json({"x": object()})


# ---------------------------------------------------------------- strings
class TestStrings:
    def test_is_valid_json(self):
        assert is_valid_json('{"a": 1}')
        assert is_valid_json(b"[1, 2]")
        assert is_valid_json("null")
        assert not is_valid_json("{bad json}")
        assert not is_valid_json("")
        assert not is_valid_json(None)
        assert not is_valid_json(123)

    def test_safe_loads(self):
        assert safe_loads('{"a": 1}') == {"a": 1}
        assert safe_loads("nope") is None
        assert safe_loads("nope", default={}) == {}
        assert safe_loads(None, default="x") == "x"

    def test_prettify_json(self):
        assert prettify_json('{"b":1,"a":[1,2]}') == '{\n  "b": 1,\n  "a": [\n    1,\n    2\n  ]\n}'
        assert prettify_json('{"b":1,"a":2}', sort_keys=True, indent=1) == '{\n "a": 2,\n "b": 1\n}'

    def test_prettify_invalid_raises_value_error(self):
        with pytest.raises(ValueError):
            prettify_json("{bad")

    def test_minify_json(self):
        assert minify_json('{ "a" : 1 ,\n "b" : [ 1, 2 ] }') == '{"a":1,"b":[1,2]}'
        assert minify_json('{"n": "é"}') == '{"n":"é"}'
        assert minify_json('{"n": "é"}', ensure_ascii=True) == '{"n":"\\u00e9"}'

    def test_minify_invalid_raises_value_error(self):
        with pytest.raises(ValueError):
            minify_json("{bad")


# ------------------------------------------------------------------ files
class TestReadWriteJson:
    def test_round_trip(self, tmp_path):
        data = {"name": "café", "items": [1, 2, {"ok": True}], "none": None}
        file = write_json(tmp_path / "data.json", data)
        assert file == tmp_path / "data.json"
        assert read_json(file) == data

    def test_format_is_indented_with_trailing_newline_and_unescaped_unicode(self, tmp_path):
        file = write_json(tmp_path / "d.json", {"a": "é"})
        raw = file.read_bytes()
        assert raw == '{\n  "a": "é"\n}\n'.encode("utf-8")  # LF only, no escaping

    def test_options(self, tmp_path):
        file = write_json(tmp_path / "d.json", {"b": 1, "a": 2}, indent=None, sort_keys=True)
        assert file.read_text() == '{"a": 2, "b": 1}\n'

    def test_writes_special_types(self, tmp_path):
        file = write_json(tmp_path / "d.json", {"when": date(2026, 1, 2), "p": Point(1, 2)})
        assert read_json(file) == {"when": "2026-01-02", "p": {"x": 1, "y": 2}}

    def test_creates_missing_folders(self, tmp_path):
        file = write_json(tmp_path / "a" / "b" / "d.json", [1])
        assert read_json(file) == [1]

    def test_create_folders_false_raises_when_folder_missing(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            write_json(tmp_path / "missing" / "d.json", [1], create_folders=False)

    def test_atomic_write_leaves_no_temp_files(self, tmp_path):
        write_json(tmp_path / "d.json", {"a": 1})
        write_json(tmp_path / "d.json", {"a": 2})
        assert leftovers(tmp_path) == []
        assert read_json(tmp_path / "d.json") == {"a": 2}

    def test_non_atomic_write(self, tmp_path):
        write_json(tmp_path / "d.json", {"a": 1}, atomic=False)
        assert read_json(tmp_path / "d.json") == {"a": 1}

    def test_unserializable_data_keeps_existing_file(self, tmp_path):
        file = write_json(tmp_path / "d.json", {"good": True})
        for atomic in (True, False):
            with pytest.raises(TypeError):
                write_json(file, {"bad": object()}, atomic=atomic)
            assert read_json(file) == {"good": True}
        assert leftovers(tmp_path) == []

    def test_rewrite_keeps_file_permissions(self, tmp_path):
        if os.name == "nt":
            pytest.skip("POSIX permissions only")
        file = write_json(tmp_path / "d.json", {"a": 1})
        os.chmod(file, 0o640)
        write_json(file, {"a": 2})
        assert stat.S_IMODE(os.stat(file).st_mode) == 0o640

    def test_read_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            read_json(tmp_path / "nope.json")

    def test_read_missing_file_returns_default(self, tmp_path):
        assert read_json(tmp_path / "nope.json", default={}) == {}
        assert read_json(tmp_path / "nope.json", default=None) is None

    def test_read_invalid_json_raises_even_with_default(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{not json")
        with pytest.raises(ValueError):
            read_json(bad, default={})

    def test_read_file_with_bom(self, tmp_path):
        file = tmp_path / "bom.json"
        file.write_bytes(b"\xef\xbb\xbf" + b'{"a": 1}')
        assert read_json(file) == {"a": 1}

    def test_accepts_str_paths(self, tmp_path):
        write_json(str(tmp_path / "d.json"), {"a": 1})
        assert read_json(str(tmp_path / "d.json")) == {"a": 1}


class TestJsonLines:
    def test_round_trip_and_count(self, tmp_path):
        items = [{"id": 1}, {"id": 2, "name": "café"}, [1, 2], "text", None]
        assert write_jsonl(tmp_path / "d.jsonl", items) == 5
        assert list(read_jsonl(tmp_path / "d.jsonl")) == items

    def test_one_line_per_item(self, tmp_path):
        write_jsonl(tmp_path / "d.jsonl", [{"a": 1}, {"a": 2}])
        assert (tmp_path / "d.jsonl").read_text() == '{"a": 1}\n{"a": 2}\n'

    def test_accepts_generators(self, tmp_path):
        assert write_jsonl(tmp_path / "d.jsonl", ({"n": n} for n in range(3))) == 3
        assert [row["n"] for row in read_jsonl(tmp_path / "d.jsonl")] == [0, 1, 2]

    def test_empty_iterable_writes_empty_file(self, tmp_path):
        assert write_jsonl(tmp_path / "d.jsonl", []) == 0
        assert list(read_jsonl(tmp_path / "d.jsonl")) == []

    def test_blank_lines_are_skipped(self, tmp_path):
        file = tmp_path / "d.jsonl"
        file.write_text('{"a": 1}\n\n   \n{"a": 2}\n')
        assert list(read_jsonl(file)) == [{"a": 1}, {"a": 2}]

    def test_invalid_line_reports_line_number(self, tmp_path):
        file = tmp_path / "d.jsonl"
        file.write_text('{"a": 1}\n{bad}\n{"a": 3}\n')
        rows = read_jsonl(file)
        assert next(rows) == {"a": 1}
        with pytest.raises(ValueError):
            next(rows)
        try:
            list(read_jsonl(file))
        except ValueError as error:
            assert "line 2" in str(error)

    def test_missing_file_raises_immediately(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            read_jsonl(tmp_path / "nope.jsonl")  # no iteration needed

    def test_failed_write_keeps_existing_file(self, tmp_path):
        file = tmp_path / "d.jsonl"
        write_jsonl(file, [{"good": 1}])
        with pytest.raises(TypeError):
            write_jsonl(file, [{"ok": 1}, {"bad": object()}])
        assert list(read_jsonl(file)) == [{"good": 1}]
        assert leftovers(tmp_path) == []

    def test_append_creates_and_extends(self, tmp_path):
        file = tmp_path / "sub" / "log.jsonl"
        append_jsonl(file, {"n": 1})
        append_jsonl(file, {"n": 2, "when": date(2026, 1, 2)})
        assert list(read_jsonl(file)) == [{"n": 1}, {"n": 2, "when": "2026-01-02"}]

    def test_append_unserializable_does_not_write(self, tmp_path):
        file = tmp_path / "log.jsonl"
        append_jsonl(file, {"n": 1})
        with pytest.raises(TypeError):
            append_jsonl(file, {"bad": object()})
        assert list(read_jsonl(file)) == [{"n": 1}]


# ------------------------------------------------------------ nested data
class TestPaths:
    DATA = {"user": {"name": "Ada", "addresses": [{"city": "London"}, {"city": "Paris"}]}, "a.b": 1}

    def test_get_nested_values(self):
        assert get_by_path(self.DATA, "user.name") == "Ada"
        assert get_by_path(self.DATA, "user.addresses.1.city") == "Paris"
        assert get_by_path(self.DATA, "user.addresses.-1.city") == "Paris"

    def test_get_missing_returns_default(self):
        assert get_by_path(self.DATA, "user.age") is None
        assert get_by_path(self.DATA, "user.age", 0) == 0
        assert get_by_path(self.DATA, "user.addresses.5.city", "?") == "?"
        assert get_by_path(self.DATA, "user.addresses.x.city", "?") == "?"
        assert get_by_path(self.DATA, "user.name.first", "?") == "?"

    def test_get_returns_falsy_values_not_default(self):
        assert get_by_path({"a": 0, "b": None, "c": ""}, "a", "d") == 0
        assert get_by_path({"a": 0, "b": None, "c": ""}, "b", "d") is None
        assert get_by_path({"a": 0, "b": None, "c": ""}, "c", "d") == ""

    def test_get_with_sequence_path_and_custom_separator(self):
        assert get_by_path(self.DATA, ["a.b"]) == 1
        assert get_by_path(self.DATA, ["user", "addresses", 0, "city"]) == "London"
        assert get_by_path(self.DATA, "user/name", sep="/") == "Ada"

    def test_get_empty_path_returns_data(self):
        assert get_by_path(self.DATA, "") is self.DATA

    def test_set_creates_missing_dicts_and_returns_same_object(self):
        data = {}
        assert set_by_path(data, "a.b.c", 1) is data
        assert data == {"a": {"b": {"c": 1}}}

    def test_set_overwrites_existing_values(self):
        data = {"a": {"b": 1}}
        set_by_path(data, "a.b", 2)
        assert data == {"a": {"b": 2}}

    def test_set_inside_lists(self):
        data = {"items": [{"n": 1}, {"n": 2}]}
        set_by_path(data, "items.1.n", 20)
        set_by_path(data, "items.0", "replaced")
        assert data == {"items": ["replaced", {"n": 20}]}

    def test_set_list_index_out_of_range(self):
        with pytest.raises(IndexError):
            set_by_path({"items": [1]}, "items.5", 0)
        with pytest.raises(IndexError):
            set_by_path({"items": [1]}, "items.5.x", 0)

    def test_set_bad_list_index(self):
        with pytest.raises(TypeError):
            set_by_path({"items": [1]}, "items.first", 0)

    def test_set_through_scalar_raises(self):
        with pytest.raises(TypeError):
            set_by_path({"a": 1}, "a.b", 2)
        with pytest.raises(TypeError):
            set_by_path({"a": None}, "a.b", 2)

    def test_set_empty_path_raises(self):
        with pytest.raises(ValueError):
            set_by_path({}, "", 1)

    def test_set_with_sequence_path(self):
        data = {}
        set_by_path(data, ["a.b", "c"], 1)
        assert data == {"a.b": {"c": 1}}


class TestFlatten:
    NESTED = {"a": 1, "b": {"c": 2, "d": [3, {"e": 4}]}, "f": {}, "g": []}

    def test_flatten(self):
        assert flatten_json(self.NESTED) == {
            "a": 1, "b.c": 2, "b.d.0": 3, "b.d.1.e": 4, "f": {}, "g": [],
        }

    def test_flatten_custom_separator(self):
        assert flatten_json({"a": {"b": 1}}, sep="/") == {"a/b": 1}

    def test_flatten_top_level_list(self):
        assert flatten_json([{"a": 1}, 2]) == {"0.a": 1, "1": 2}

    def test_flatten_empty_containers(self):
        assert flatten_json({}) == {}
        assert flatten_json([]) == {}

    def test_flatten_rejects_scalars(self):
        with pytest.raises(TypeError):
            flatten_json("text")
        with pytest.raises(TypeError):
            flatten_json(5)

    def test_round_trip(self):
        assert unflatten_json(flatten_json(self.NESTED)) == self.NESTED

    def test_round_trip_top_level_list(self):
        data = [{"a": 1}, [2, 3], "x"]
        assert unflatten_json(flatten_json(data)) == data

    def test_round_trip_custom_separator(self):
        data = {"a": {"b": [1, 2]}}
        assert unflatten_json(flatten_json(data, sep="/"), sep="/") == data

    def test_unflatten_builds_lists_only_for_complete_index_runs(self):
        assert unflatten_json({"a.0": "x", "a.1": "y"}) == {"a": ["x", "y"]}
        assert unflatten_json({"a.0": "x", "a.2": "y"}) == {"a": {"0": "x", "2": "y"}}
        assert unflatten_json({"a.01": "x"}) == {"a": {"01": "x"}}

    def test_unflatten_empty(self):
        assert unflatten_json({}) == {}

    def test_unflatten_conflicts_raise(self):
        with pytest.raises(ValueError):
            unflatten_json({"a": 1, "a.b": 2})
        with pytest.raises(ValueError):
            unflatten_json({"a.b": 2, "a": 1})

    def test_unflatten_does_not_modify_leaf_values(self):
        leaf = {"keep": "me"}
        result = unflatten_json({"a": leaf})
        assert result == {"a": {"keep": "me"}}
        assert leaf == {"keep": "me"}


class TestMerge:
    def test_nested_dicts_merge_key_by_key(self):
        base = {"a": 1, "b": {"x": 1, "y": 2}}
        assert deep_merge(base, {"b": {"y": 20, "z": 30}, "c": 3}) == {
            "a": 1, "b": {"x": 1, "y": 20, "z": 30}, "c": 3,
        }

    def test_inputs_are_not_modified(self):
        base = {"b": {"x": [1]}}
        other = {"b": {"y": {"z": 1}}}
        result = deep_merge(base, other)
        result["b"]["x"].append(2)
        result["b"]["y"]["z"] = 99
        assert base == {"b": {"x": [1]}}
        assert other == {"b": {"y": {"z": 1}}}

    def test_multiple_dicts_later_wins(self):
        assert deep_merge({"a": 1}, {"a": 2}, {"a": 3}) == {"a": 3}

    def test_lists_replace_by_default_and_extend_on_request(self):
        assert deep_merge({"l": [1, 2]}, {"l": [3]}) == {"l": [3]}
        assert deep_merge({"l": [1, 2]}, {"l": [3]}, lists="extend") == {"l": [1, 2, 3]}

    def test_type_conflicts_take_the_later_value(self):
        assert deep_merge({"a": {"x": 1}}, {"a": 5}) == {"a": 5}
        assert deep_merge({"a": 5}, {"a": {"x": 1}}) == {"a": {"x": 1}}

    def test_invalid_list_strategy(self):
        with pytest.raises(ValueError):
            deep_merge({}, {}, lists="union")

    def test_only_base(self):
        base = {"a": {"b": 1}}
        result = deep_merge(base)
        assert result == base and result is not base and result["a"] is not base["a"]


class TestDiff:
    def test_added_removed_changed(self):
        old = {"a": 1, "b": {"c": 2, "d": 3}, "gone": True}
        new = {"a": 1, "b": {"c": 20, "e": 5}, "new": "x"}
        assert diff_json(old, new) == {
            "added": {"b.e": 5, "new": "x"},
            "removed": {"b.d": 3, "gone": True},
            "changed": {"b.c": (2, 20)},
        }

    def test_identical_documents(self):
        assert diff_json({"a": [1, 2]}, {"a": [1, 2]}) == {"added": {}, "removed": {}, "changed": {}}

    def test_lists_are_compared_by_position(self):
        assert diff_json({"l": [1, 2]}, {"l": [1, 3, 4]}) == {
            "added": {"l.2": 4}, "removed": {}, "changed": {"l.1": (2, 3)},
        }

    def test_true_is_not_one(self):
        assert diff_json({"a": True}, {"a": 1})["changed"] == {"a": (True, 1)}
        assert diff_json({"a": 0}, {"a": False})["changed"] == {"a": (0, False)}

    def test_custom_separator(self):
        assert diff_json({"a": {"b": 1}}, {"a": {"b": 2}}, sep="/")["changed"] == {"a/b": (1, 2)}

    def test_rejects_scalars(self):
        with pytest.raises(TypeError):
            diff_json(1, {"a": 1})


# ------------------------------------------------------------------- keys
class TestKeys:
    def test_pick_keys(self):
        data = {"a": 1, "b": 2, "c": 3}
        assert pick_keys(data, ["c", "a", "missing"]) == {"a": 1, "c": 3}
        assert list(pick_keys(data, ["c", "a"])) == ["a", "c"]  # original order
        assert pick_keys(data, []) == {}

    def test_remove_keys_recursively(self):
        data = {"user": "ada", "password": "x", "items": [{"id": 1, "token": "t"}], "nested": {"password": "y", "ok": 1}}
        assert remove_keys(data, ["password", "token"]) == {
            "user": "ada", "items": [{"id": 1}], "nested": {"ok": 1},
        }

    def test_remove_keys_does_not_modify_input(self):
        data = {"password": "x", "nested": {"password": "y"}}
        remove_keys(data, ["password"])
        assert data == {"password": "x", "nested": {"password": "y"}}

    def test_remove_keys_top_level_only(self):
        data = {"password": "x", "nested": {"password": "y"}}
        assert remove_keys(data, ["password"], recursive=False) == {"nested": {"password": "y"}}

    def test_remove_keys_from_a_list_and_scalars(self):
        assert remove_keys([{"a": 1, "b": 2}], ["a"]) == [{"b": 2}]
        assert remove_keys([{"a": 1}], ["a"], recursive=False) == [{"a": 1}]
        assert remove_keys("text", ["a"]) == "text"

    def test_convert_keys_recursively(self):
        data = {"A": {"B": 1}, "L": [{"C": 2}]}
        assert convert_keys(data, str.lower) == {"a": {"b": 1}, "l": [{"c": 2}]}

    def test_convert_keys_top_level_only(self):
        assert convert_keys({"A": {"B": 1}}, str.lower, recursive=False) == {"a": {"B": 1}}

    def test_convert_keys_leaves_values_and_non_string_keys_alone(self):
        assert convert_keys({"A": "Value", 1: "x"}, str.lower) == {"a": "Value", 1: "x"}

    def test_convert_keys_does_not_modify_input(self):
        data = {"A": {"B": 1}}
        convert_keys(data, str.lower)
        assert data == {"A": {"B": 1}}

    def test_keys_to_snake_case(self):
        data = {"userName": 1, "userID": 2, "HTTPServer": 3, "already_snake": 4, "getHTTPResponseCode": 5, "nested": {"someKey": [{"innerKey": 6}]}}
        assert keys_to_snake_case(data) == {
            "user_name": 1, "user_id": 2, "http_server": 3, "already_snake": 4,
            "get_http_response_code": 5, "nested": {"some_key": [{"inner_key": 6}]},
        }

    def test_keys_to_camel_case(self):
        data = {"user_name": 1, "user_id": 2, "_id": 3, "__private_key": 4, "alreadyCamel": 5, "nested": {"some_key": [{"inner_key": 6}]}}
        assert keys_to_camel_case(data) == {
            "userName": 1, "userId": 2, "_id": 3, "__privateKey": 4, "alreadyCamel": 5,
            "nested": {"someKey": [{"innerKey": 6}]},
        }

    def test_case_conversion_non_recursive(self):
        assert keys_to_snake_case({"aB": {"cD": 1}}, recursive=False) == {"a_b": {"cD": 1}}
        assert keys_to_camel_case({"a_b": {"c_d": 1}}, recursive=False) == {"aB": {"c_d": 1}}