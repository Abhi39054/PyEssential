# Folders (`pyessential.folders`)

Utility functions for creating, inspecting, and cleaning folders safely across Windows, macOS, and Linux.

All functions accept either a `str` or a `pathlib.Path` and return `Path` objects. Destructive functions refuse to operate on a filesystem root (such as `/` or `C:\`) or the user's home folder, handle Windows read-only files automatically, and never follow symbolic links outside the target folder.

## Usage

```python
from datetime import timedelta
from pyessential.folders import (
    ensure_folder,
    list_files,
    list_folders,
    is_folder_empty,
    get_folder_size,
    clear_folder,
    delete_folder,
    delete_old_files,
    remove_empty_folders,
)

# 1. Create a folder (and parents) if missing
uploads = ensure_folder("data/uploads")

# 2. Inspect files and sub-folders
txt_files = list_files(uploads, pattern="*.txt", recursive=True)
subfolders = list_folders(uploads, recursive=True)
empty = is_folder_empty(uploads)
size_in_bytes = get_folder_size(uploads)

# 3. Clean up old files and prune empty sub-folders
deleted_files = delete_old_files(uploads, timedelta(days=7), recursive=True)
pruned_folders = remove_empty_folders(uploads)