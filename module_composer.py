import os
import datetime
from typing import Iterable, List, Optional, Tuple


SEPARATOR = "---\n"


def discover_modules(directory: Optional[str] = None) -> List[str]:
    """Return a sorted list of module file paths discovered in a directory.

    A "module" here is any Python file named like `module_*.py` excluding
    dunder files and test files. Returned items are absolute file paths.
    """
    directory = directory or os.getcwd()
    modules: List[str] = []
    for name in os.listdir(directory):
        if not name.startswith("module_"):
            continue
        if not name.endswith(".py"):
            continue
        if name.startswith("__"):
            continue
        modules.append(os.path.join(directory, name))
    modules.sort()
    return modules


def compose_module_list(output_path: str, modules: Iterable[str]) -> None:
    """Write a text file with full contents of each module file.

    For each module file path:
    ---\n
    [# module_name]
    <full file contents>
    """
    with open(output_path, "w", encoding="utf-8") as out:
        for path in modules:
            module_name = os.path.splitext(os.path.basename(path))[0]
            out.write(SEPARATOR)
            out.write(f"[# {module_name}]\n")
            with open(path, "r", encoding="utf-8") as src:
                out.write(src.read())
            # Ensure a trailing newline between modules
            if not module_name.endswith("\n"):
                out.write("\n")


def _walk_files(root: str) -> List[Tuple[str, int, float]]:
    """Return list of (path, size_bytes, mtime_epoch) for all files under root."""
    entries: List[Tuple[str, int, float]] = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            try:
                stat = os.stat(fpath)
            except OSError:
                # Skip files we cannot stat
                continue
            entries.append((fpath, stat.st_size, stat.st_mtime))
    entries.sort()
    return entries


def compose_filesystem_summary(output_path: str, root: str) -> None:
    """Write a human-readable summary of the current project filesystem.

    The output includes:
    - Overall directory and file counts
    - Per-directory listing (relative paths)
    - Per-file entry with size and last modified timestamp
    """
    root = os.path.abspath(root)
    files = _walk_files(root)

    # Build directory set and mapping
    dir_set = set()
    for fpath, _size, _mtime in files:
        dir_set.add(os.path.dirname(fpath))

    total_dirs = len(dir_set)
    total_files = len(files)
    now = datetime.datetime.now().isoformat(timespec="seconds")

    with open(output_path, "w", encoding="utf-8") as out:
        out.write(SEPARATOR)
        out.write("[# Filesystem Summary]\n")
        out.write(f"Root: {root}\n")
        out.write(f"Generated: {now}\n")
        out.write(f"Directories: {total_dirs}\n")
        out.write(f"Files: {total_files}\n")
        out.write("\n")

        # Per-directory listings
        for d in sorted(dir_set):
            rel_dir = os.path.relpath(d, root)
            out.write(SEPARATOR)
            out.write(f"[# dir {rel_dir}]\n")
            for fpath, size, mtime in files:
                if os.path.dirname(fpath) != d:
                    continue
                rel_file = os.path.relpath(fpath, root)
                mtime_str = datetime.datetime.fromtimestamp(mtime).isoformat(timespec="seconds")
                out.write(f"- {rel_file} | {size} bytes | modified {mtime_str}\n")
        # Ensure trailing newline
        out.write("\n")


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry.

    Usage:
            python -m module_composer [output_path] [directory] [mode]

        - output_path: where to write the list (default: ModulesList.txt)
        - directory: directory to summarize/discover (default: CWD)
        - mode: "fs" to write filesystem summary (default), "modules" to write
            the concatenated contents of module_*.py files.
    """
    import sys

    args = list(argv) if argv is not None else sys.argv[1:]
    # Flexible CLI parsing to allow omitting output_path while providing mode
    if len(args) >= 3:
        output_path = args[0]
        directory = args[1]
        mode = args[2]
    elif len(args) == 2:
        # Treat as [directory] [mode]
        directory = args[0]
        mode = args[1]
        # Default output path based on mode
        if mode == "modules":
            today = datetime.date.today().isoformat()
            output_path = os.path.join(os.getcwd(), f"ModulesList_{today}.txt")
        else:
            output_path = os.path.join(os.getcwd(), "ModulesList.txt")
    else:
        # 0 or 1 args: default mode fs, optional directory
        directory = args[0] if len(args) == 1 else os.getcwd()
        mode = "fs"
        output_path = os.path.join(os.getcwd(), "ModulesList.txt")

    if mode == "modules":
        modules = discover_modules(directory)
        compose_module_list(output_path, modules)
        print(f"Wrote {len(modules)} modules to: {output_path}")
    else:
        compose_filesystem_summary(output_path, directory)
        print(f"Wrote filesystem summary for: {directory} -> {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
