import os
import stat
import time
from datetime import timedelta
from pathlib import Path
import pytest

from pyessential.folders import (
    clear_folder,
    delete_folder,
    delete_old_files,
    ensure_folder,
    get_folder_size,
    is_folder_empty,
    list_files,
    list_folders,
    remove_empty_folders,
)


def _can_symlink(tmp_path: Path) -> bool:
    """Check whether the current OS/user environment allows creating symlinks."""
    target = tmp_path / "_symlink_target"
    link = tmp_path / "_symlink_test"
    target.mkdir()
    try:
        link.symlink_to(target, target_is_directory=True)
        link.unlink()
        target.rmdir()
        return True
    except (OSError, NotImplementedError):
        return False


# -------------------------------------------------------------- ensure_folder
def test_ensure_folder_creates_and_is_idempotent(tmp_path: Path):
    target = tmp_path / "a" / "b" / "c"
    result = ensure_folder(str(target))
    assert result == target
    assert target.is_dir()

    # Calling again succeeds without error
    assert ensure_folder(target) == target


def test_ensure_folder_parents_false_raises(tmp_path: Path):
    target = tmp_path / "missing_parent" / "child"
    with pytest.raises(FileNotFoundError):
        ensure_folder(target, parents=False)


def test_ensure_folder_raises_if_file_exists(tmp_path: Path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("hello")
    with pytest.raises(FileExistsError):
        ensure_folder(file_path)


# ----------------------------------------------------------------- list_files
def test_list_files_basic_and_pattern(tmp_path: Path):
    (tmp_path / "b.txt").write_text("b")
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "c.log").write_text("c")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "d.txt").write_text("d")

    assert list_files(tmp_path) == [tmp_path / "a.txt", tmp_path / "b.txt", tmp_path / "c.log"]
    assert list_files(tmp_path, "*.txt") == [tmp_path / "a.txt", tmp_path / "b.txt"]
    assert list_files(tmp_path, "*.txt", recursive=True) == [
        tmp_path / "a.txt",
        tmp_path / "b.txt",
        sub / "d.txt",
    ]


def test_list_files_errors(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        list_files(tmp_path / "nope")

    f = tmp_path / "file.txt"
    f.write_text("x")
    with pytest.raises(NotADirectoryError):
        list_files(f)


# --------------------------------------------------------------- list_folders
def test_list_folders_flat_and_recursive(tmp_path: Path):
    (tmp_path / "file.txt").write_text("x")
    sub1 = tmp_path / "sub1"
    sub2 = tmp_path / "sub2"
    nested = sub1 / "nested"
    nested.mkdir(parents=True)
    sub2.mkdir()

    assert list_folders(tmp_path) == [sub1, sub2]
    assert list_folders(tmp_path, recursive=True) == [sub1, nested, sub2]


def test_list_folders_ignores_symlinks(tmp_path: Path):
    if not _can_symlink(tmp_path):
        pytest.skip("Symlinks not supported in this environment")

    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("secret")

    root = tmp_path / "root"
    root.mkdir()
    link = root / "link_to_outside"
    link.symlink_to(outside, target_is_directory=True)

    assert list_folders(root) == []
    assert list_folders(root, recursive=True) == []
    assert list_files(root, recursive=True) == []


# ------------------------------------------------------------ is_folder_empty
def test_is_folder_empty(tmp_path: Path):
    assert is_folder_empty(tmp_path) is True
    f = tmp_path / "a.txt"
    f.write_text("x")
    assert is_folder_empty(tmp_path) is False


# ------------------------------------------------------------ get_folder_size
def test_get_folder_size(tmp_path: Path):
    (tmp_path / "a.bin").write_bytes(b"12345")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.bin").write_bytes(b"1234567890")

    assert get_folder_size(tmp_path) == 15


# --------------------------------------------------------------- clear_folder
def test_clear_folder_and_dry_run(tmp_path: Path):
    f = tmp_path / "a.txt"
    f.write_text("hello")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "nested.txt").write_text("world")

    # Dry run keeps everything intact
    would_delete = clear_folder(tmp_path, dry_run=True)
    assert would_delete == [f, sub]
    assert f.exists() and sub.exists()

    # Real run deletes contents but keeps tmp_path
    deleted = clear_folder(tmp_path)
    assert deleted == [f, sub]
    assert tmp_path.exists()
    assert is_folder_empty(tmp_path)


def test_clear_folder_handles_readonly_files(tmp_path: Path):
    ro_file = tmp_path / "readonly.txt"
    ro_file.write_text("locked")
    os.chmod(ro_file, stat.S_IREAD)

    clear_folder(tmp_path)
    assert is_folder_empty(tmp_path)


# -------------------------------------------------------------- delete_folder
def test_delete_folder_and_missing_ok(tmp_path: Path):
    target = tmp_path / "to_delete"
    target.mkdir()
    ro = target / "ro.txt"
    ro.write_text("data")
    os.chmod(ro, stat.S_IREAD)

    delete_folder(target)
    assert not target.exists()

    # missing_ok=True does not raise
    delete_folder(target, missing_ok=True)

    # missing_ok=False raises FileNotFoundError
    with pytest.raises(FileNotFoundError):
        delete_folder(target, missing_ok=False)


def test_delete_folder_symlink_keeps_target(tmp_path: Path):
    if not _can_symlink(tmp_path):
        pytest.skip("Symlinks not supported in this environment")

    real = tmp_path / "real"
    real.mkdir()
    keep_file = real / "keep.txt"
    keep_file.write_text("important")

    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)

    delete_folder(link)
    assert not link.exists()
    assert keep_file.exists()


# ----------------------------------------------------------- delete_old_files
def test_delete_old_files(tmp_path: Path):
    old_file = tmp_path / "old.txt"
    new_file = tmp_path / "new.txt"
    old_file.write_text("old")
    new_file.write_text("new")

    past = time.time() - 7200  # 2 hours ago
    os.utime(old_file, (past, past))

    # Dry run
    preview = delete_old_files(tmp_path, timedelta(hours=1), dry_run=True)
    assert preview == [old_file]
    assert old_file.exists()

    # Actual deletion
    deleted = delete_old_files(tmp_path, timedelta(hours=1))
    assert deleted == [old_file]
    assert not old_file.exists()
    assert new_file.exists()


def test_delete_old_files_validation_and_on_error(tmp_path: Path):
    with pytest.raises(TypeError):
        delete_old_files(tmp_path, 3600)  # type: ignore[arg-type]

    with pytest.raises(ValueError):
        delete_old_files(tmp_path, timedelta(seconds=-10))

    f = tmp_path / "old.txt"
    f.write_text("x")
    past = time.time() - 3600
    os.utime(f, (past, past))

    errors = []
    # Test on_error callback when unlink fails
    def fake_error_handler(path: Path, exc: OSError):
        errors.append((path, exc))

    # Normal run succeeds with no errors
    deleted = delete_old_files(tmp_path, timedelta(minutes=5), on_error=fake_error_handler)
    assert deleted == [f]
    assert errors == []


# ------------------------------------------------------- remove_empty_folders
def test_remove_empty_folders(tmp_path: Path):
    empty_chain = tmp_path / "a" / "b" / "c"
    empty_chain.mkdir(parents=True)
    non_empty = tmp_path / "keep"
    non_empty.mkdir()
    (non_empty / "file.txt").write_text("stay")

    # Dry run reports deepest first without deleting
    preview = remove_empty_folders(tmp_path, dry_run=True)
    assert preview == [
        tmp_path / "a" / "b" / "c",
        tmp_path / "a" / "b",
        tmp_path / "a",
    ]
    assert empty_chain.exists()

    # Real run removes empty hierarchy but keeps root and non_empty
    removed = remove_empty_folders(tmp_path)
    assert removed == preview
    assert not (tmp_path / "a").exists()
    assert non_empty.exists()
    assert tmp_path.exists()


# --------------------------------------------------------------- safety rules
@pytest.mark.parametrize(
    "func,args",
    [
        (clear_folder, ()),
        (delete_folder, ()),
        (delete_old_files, (timedelta(days=1),)),
        (remove_empty_folders, ()),
    ],
)
def test_refuse_dangerous_paths(func, args):
    root = Path(Path.cwd().anchor)
    home = Path.home()

    with pytest.raises(ValueError, match="filesystem root"):
        func(root, *args)

    with pytest.raises(ValueError, match="home folder"):
        func(home, *args)