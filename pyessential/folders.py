"""
    Name: pyessential.folders
    Description: A module providing utility functions for working with folders.
"""

import fnmatch
import os
import shutil
import stat
import sys
import time
from datetime import timedelta
from pathlib import Path
from typing import Callable, List, Optional, Union

__all__ = [
    "ensure_folder",
    "list_files",
    "list_folders",
    "is_folder_empty",
    "get_folder_size",
    "clear_folder",
    "delete_folder",
    "delete_old_files",
    "remove_empty_folders",
]

#: Anything accepted as a path: a string or a ``pathlib.Path`` (or other path-like object).
PathLike = Union[str, "os.PathLike[str]"]


# ---------------------------------------------------------------- helpers
def _require_folder(folder: PathLike) -> Path:
    """Return ``folder`` as a Path, making sure it exists and is a folder."""
    path = Path(folder)
    if not path.exists():
        raise FileNotFoundError(f"Folder not found: {path}")
    if not path.is_dir():
        raise NotADirectoryError(f"Not a folder: {path}")
    return path


def _refuse_dangerous(folder: PathLike) -> None:
    """Raise ValueError if ``folder`` is a filesystem root or the user's home folder."""
    try:
        resolved = Path(folder).resolve()
    except (OSError, RuntimeError):
        return
    if resolved == Path(resolved.anchor):
        raise ValueError(f"Refusing to modify a filesystem root: {folder}")
    try:
        home = Path.home().resolve()
    except (OSError, RuntimeError):
        return
    if resolved == home:
        raise ValueError(f"Refusing to modify the home folder: {folder}")


def _unlink(path: Path) -> None:
    """Delete a file or link, clearing the Windows read-only flag if needed."""
    try:
        path.unlink()
    except PermissionError:
        os.chmod(path, stat.S_IWRITE)
        path.unlink()


def _rmtree(path: Path) -> None:
    """``shutil.rmtree`` that also removes read-only files (a common problem on Windows)."""

    def _retry(func, failed_path, _exc):
        os.chmod(failed_path, stat.S_IWRITE)
        func(failed_path)

    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=_retry)
    else:
        shutil.rmtree(path, onerror=_retry)


def _remove_entry(path: Path) -> None:
    """Remove a file, a link (never what it points to), or a whole folder."""
    if path.is_symlink() or not path.is_dir():
        _unlink(path)
    else:
        _rmtree(path)


# ------------------------------------------------------------- public API
def ensure_folder(path: PathLike, *, parents: bool = True) -> Path:
    """Create a folder if it does not exist yet and return it.

    Safe to call repeatedly: an existing folder is left untouched.

    Args:
        path (str | Path): The folder to create.
        parents (bool): Also create missing parent folders. Default is True.

    Returns:
        Path: The folder.

    Raises:
        FileExistsError: If a file (not a folder) already exists at ``path``.
        FileNotFoundError: If ``parents`` is False and a parent folder is missing.
    """
    folder = Path(path)
    folder.mkdir(parents=parents, exist_ok=True)
    return folder


def list_files(
    folder: PathLike, pattern: str = "*", *, recursive: bool = False
) -> List[Path]:
    """List the files in a folder.

    Args:
        folder (str | Path): The folder to look in.
        pattern (str): A glob pattern the file names must match, such as ``"*.txt"``.
            Default is ``"*"`` (all files).
        recursive (bool): Also look inside sub-folders. Default is False. Symbolic links
            to folders are not followed.

    Returns:
        List[Path]: The matching files, sorted. Folders are not included.

    Raises:
        FileNotFoundError: If ``folder`` does not exist.
        NotADirectoryError: If ``folder`` is not a folder.
    """
    path = _require_folder(folder)
    if not recursive:
        return sorted(p for p in path.glob(pattern) if p.is_file())

    results: List[Path] = []
    for dirpath, _dirnames, filenames in os.walk(path, followlinks=False):
        current = Path(dirpath)
        for name in filenames:
            if fnmatch.fnmatchcase(name, pattern):
                candidate = current / name
                if candidate.is_file():
                    results.append(candidate)
    return sorted(results)


def list_folders(folder: PathLike, *, recursive: bool = False) -> List[Path]:
    """List the sub-folders of a folder.

    Args:
        folder (str | Path): The folder to look in.
        recursive (bool): Also include folders nested deeper down. Default is False.
            Symbolic links to folders are neither listed nor followed.

    Returns:
        List[Path]: The sub-folders, sorted. Files are not included.

    Raises:
        FileNotFoundError: If ``folder`` does not exist.
        NotADirectoryError: If ``folder`` is not a folder.
    """
    path = _require_folder(folder)
    if not recursive:
        return sorted(p for p in path.iterdir() if p.is_dir() and not p.is_symlink())

    results: List[Path] = []
    for dirpath, dirnames, _filenames in os.walk(path, followlinks=False):
        current = Path(dirpath)
        for name in dirnames:
            sub = current / name
            if not sub.is_symlink():
                results.append(sub)
    return sorted(results)


def is_folder_empty(folder: PathLike) -> bool:
    """Check whether a folder has nothing inside it.

    Args:
        folder (str | Path): The folder to check.

    Returns:
        bool: True if the folder contains no files and no sub-folders.

    Raises:
        FileNotFoundError: If ``folder`` does not exist.
        NotADirectoryError: If ``folder`` is not a folder.
    """
    path = _require_folder(folder)
    return next(path.iterdir(), None) is None


def get_folder_size(folder: PathLike) -> int:
    """Get the total size of all files in a folder, including sub-folders.

    This is the sum of the file sizes, not the space used on disk. Symbolic links are not
    followed: a link counts as the size of the link itself, never the size of what it
    points to.

    Args:
        folder (str | Path): The folder to measure.

    Returns:
        int: The size in bytes.

    Raises:
        FileNotFoundError: If ``folder`` does not exist.
        NotADirectoryError: If ``folder`` is not a folder.
    """
    path = _require_folder(folder)
    total = 0
    for dirpath, _dirnames, filenames in os.walk(path, followlinks=False):
        for name in filenames:
            try:
                total += os.lstat(os.path.join(dirpath, name)).st_size
            except OSError:
                continue  # removed or unreadable while measuring
    return total


def clear_folder(folder: PathLike, *, dry_run: bool = False) -> List[Path]:
    """Delete everything inside a folder but keep the folder itself.

    Symbolic links are removed as links; whatever they point to is left alone. Read-only
    files are removed too.

    Args:
        folder (str | Path): The folder to empty.
        dry_run (bool): If True, delete nothing and only report what would be deleted.

    Returns:
        List[Path]: The files and folders directly inside ``folder`` that were deleted
        (or would be, in a dry run).

    Raises:
        FileNotFoundError: If ``folder`` does not exist.
        NotADirectoryError: If ``folder`` is not a folder.
        ValueError: If ``folder`` is a filesystem root or the user's home folder.
    """
    _refuse_dangerous(folder)
    path = _require_folder(folder)
    entries = sorted(path.iterdir())
    if not dry_run:
        for entry in entries:
            _remove_entry(entry)
    return entries


def delete_folder(folder: PathLike, *, missing_ok: bool = False) -> None:
    """Delete a folder and everything inside it.

    If ``folder`` is a symbolic link to a folder, only the link is removed; the folder it
    points to is left alone. Read-only files are removed too.

    Args:
        folder (str | Path): The folder to delete.
        missing_ok (bool): Do nothing if the folder does not exist, instead of raising.
            Default is False.

    Raises:
        FileNotFoundError: If ``folder`` does not exist and ``missing_ok`` is False.
        NotADirectoryError: If ``folder`` is a file.
        ValueError: If ``folder`` is a filesystem root or the user's home folder.
    """
    _refuse_dangerous(folder)
    path = Path(folder)
    if path.is_symlink():
        _unlink(path)
        return
    if not path.exists():
        if missing_ok:
            return
        raise FileNotFoundError(f"Folder not found: {path}")
    if not path.is_dir():
        raise NotADirectoryError(f"Not a folder: {path}")
    _rmtree(path)


def delete_old_files(
    folder: PathLike,
    max_age: timedelta,
    *,
    recursive: bool = False,
    dry_run: bool = False,
    on_error: Optional[Callable[[Path, OSError], None]] = None,
) -> List[Path]:
    """Delete the files in a folder that were last modified more than ``max_age`` ago.

    Only files are deleted; folders are left in place (see :func:`remove_empty_folders`).

    Args:
        folder (str | Path): The folder to clean.
        max_age (timedelta): Files whose last modification is older than this are deleted.
        recursive (bool): Also clean sub-folders. Default is False.
        dry_run (bool): If True, delete nothing and only report what would be deleted.
        on_error (Callable[[Path, OSError], None], optional): Called as
            ``on_error(path, error)`` when a file cannot be deleted (for example because it
            is in use). The file is skipped and cleaning continues. If not given, the
            error is raised.

    Returns:
        List[Path]: The files that were deleted (or would be, in a dry run).

    Raises:
        TypeError: If ``max_age`` is not a ``timedelta``.
        ValueError: If ``max_age`` is negative, or ``folder`` is a filesystem root or the
            user's home folder.
        FileNotFoundError: If ``folder`` does not exist.
        NotADirectoryError: If ``folder`` is not a folder.
    """
    if not isinstance(max_age, timedelta):
        raise TypeError("max_age must be a datetime.timedelta")
    if max_age < timedelta(0):
        raise ValueError("max_age must not be negative")
    _refuse_dangerous(folder)
    path = _require_folder(folder)

    cutoff = time.time() - max_age.total_seconds()
    deleted: List[Path] = []
    for file in list_files(path, recursive=recursive):
        try:
            if file.lstat().st_mtime >= cutoff:
                continue
            if not dry_run:
                _unlink(file)
        except FileNotFoundError:
            continue  # already removed by someone else
        except OSError as error:
            if on_error is None:
                raise
            on_error(file, error)
            continue
        deleted.append(file)
    return deleted


def remove_empty_folders(root: PathLike, *, dry_run: bool = False) -> List[Path]:
    """Delete the empty folders inside ``root``.

    Folders that only contain other empty folders are removed as well, deepest first.
    ``root`` itself is never removed. A symbolic link to a folder counts as content, so
    a folder holding one is not empty.

    Args:
        root (str | Path): The folder to tidy.
        dry_run (bool): If True, delete nothing and only report what would be deleted.

    Returns:
        List[Path]: The folders that were deleted (or would be, in a dry run), deepest first.

    Raises:
        FileNotFoundError: If ``root`` does not exist.
        NotADirectoryError: If ``root`` is not a folder.
        ValueError: If ``root`` is a filesystem root or the user's home folder.
    """
    _refuse_dangerous(root)
    top = _require_folder(root)

    removed: List[Path] = []
    removed_set = set()
    for dirpath, _dirnames, _filenames in os.walk(top, topdown=False):
        current = Path(dirpath)
        if current == top:
            continue
        remaining = [name for name in os.listdir(current) if (current / name) not in removed_set]
        if remaining:
            continue
        if not dry_run:
            os.rmdir(current)
        removed.append(current)
        removed_set.add(current)
    return removed