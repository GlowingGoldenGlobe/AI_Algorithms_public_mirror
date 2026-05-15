"""General archive-copy helpers for repository backups.

This module owns the low-level archive writer and file-selection logic. It still
supports the legacy Git-oriented backup modes used to copy only committed or
tracked repository content, and it also provides the generic "full" tree walk
used by higher-level wrappers.
"""

import json
import os
import re
import shutil
import subprocess
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from module_tools import safe_join, _ts

# Directories/files to skip when creating "full" backups (extend/override via arguments).
DEFAULT_FULL_EXCLUDES: Tuple[str, ...] = (
    '.venv',
    'venv',
    'env',
    '.tox',
    '.nox',
    'node_modules',
    'build',
    'dist',
    '__pycache__',
    '.mypy_cache',
    '.pytest_cache',
)


def _now_ts() -> str:
    """Return a timestamp string (deterministic when enabled)."""
    return _ts()


def _run_git(repo_root: str, args: List[str]) -> Tuple[int, str, str]:
    """Run a git command in `repo_root`.

    Returns: (returncode, stdout, stderr)
    """
    try:
        proc = subprocess.run(
            ['git'] + args,
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        return proc.returncode, proc.stdout or '', proc.stderr or ''
    except Exception as e:
        return 1, '', str(e)


def _normalize_patterns(patterns: Optional[Sequence[str]]) -> List[str]:
    normed: List[str] = []
    if not patterns:
        return normed
    for pat in patterns:
        if not pat:
            continue
        pat = pat.replace('\\', '/').strip('/')
        if pat:
            normed.append(pat)
    return normed


def _should_exclude(rel_path: str, patterns: Sequence[str]) -> bool:
    if not patterns:
        return False
    rel_path = rel_path.replace('\\', '/').lstrip('./')
    for pat in patterns:
        if rel_path == pat or rel_path.startswith(pat + '/'):
            return True
    return False


def list_repo_files(
    repo_root: str,
    mode: str = 'committed',
    exclude_patterns: Optional[Sequence[str]] = None,
) -> List[str]:
    """List repo file paths (relative, POSIX-ish) to back up.

    Modes:
    - committed: only files present in HEAD (i.e., what would be on remote after push)
    - tracked: all tracked files in working tree (may include uncommitted changes)
    - full: entire repo folder tree (subject to optional exclude patterns)

    Returns a sorted list of relative paths.
    """
    repo_root = os.path.abspath(repo_root)
    mode = str(mode or 'committed').lower().strip()

    if mode not in ('committed', 'tracked', 'full'):
        raise ValueError("mode must be 'committed', 'tracked', or 'full'")

    if mode == 'committed':
        rc, out, err = _run_git(repo_root, ['ls-tree', '-r', '--name-only', 'HEAD'])
        if rc != 0:
            raise RuntimeError(f"git ls-tree failed: {err.strip()}")
        files = [line.strip() for line in out.splitlines() if line.strip()]
    elif mode == 'tracked':
        rc, out, err = _run_git(repo_root, ['ls-files'])
        if rc != 0:
            raise RuntimeError(f"git ls-files failed: {err.strip()}")
        files = [line.strip() for line in out.splitlines() if line.strip()]
    else:
        patterns = list(DEFAULT_FULL_EXCLUDES)
        user_patterns = _normalize_patterns(exclude_patterns)
        if user_patterns:
            patterns.extend(user_patterns)
        files = []
        for dirpath, dirnames, filenames in os.walk(repo_root):
            rel_dir = os.path.relpath(dirpath, repo_root)
            if rel_dir == '.':
                rel_dir = ''

            # Prune directories in-place to avoid descending into excluded trees.
            pruned_dirs = []
            for dirname in dirnames:
                rel_dirname = os.path.join(rel_dir, dirname) if rel_dir else dirname
                rel_dirname = rel_dirname.replace('\\', '/')
                if _should_exclude(rel_dirname, patterns):
                    continue
                pruned_dirs.append(dirname)
            dirnames[:] = pruned_dirs

            for filename in filenames:
                rel_file = os.path.join(rel_dir, filename) if rel_dir else filename
                rel_file = rel_file.replace('\\', '/')
                if _should_exclude(rel_file, patterns):
                    continue
                files.append(rel_file)

    # Normalize to forward slashes, drop empties.
    normed = []
    for p in files:
        p = p.replace('\\', '/')
        if not p or p.startswith('.git/'):
            continue
        normed.append(p)
    return sorted(set(normed))


def _next_archive_number(archive_root: str, prefix: str = 'Archive_') -> int:
    """Return next N for Archive_N under archive_root."""
    archive_root = os.path.abspath(archive_root)
    try:
        names = os.listdir(archive_root)
    except Exception:
        names = []
    pat = re.compile(r'^' + re.escape(prefix) + r'(\d+)$')
    max_n = 0
    for name in names:
        m = pat.match(name)
        if not m:
            continue
        try:
            max_n = max(max_n, int(m.group(1)))
        except Exception:
            continue
    return max_n + 1


def _allocate_new_archive_dir(archive_root: str, prefix: str = 'Archive_', max_tries: int = 10000) -> Tuple[int, str]:
    """Allocate a brand-new Archive_N directory path.

    Guarantees the returned directory does not already exist at time of check.
    """
    archive_root = os.path.abspath(archive_root)
    start_n = _next_archive_number(archive_root, prefix=prefix)
    n = start_n
    tries = 0
    while tries < int(max_tries):
        archive_dir = os.path.join(archive_root, f'{prefix}{n}')
        if not os.path.exists(archive_dir):
            return n, archive_dir
        n += 1
        tries += 1
    raise RuntimeError('Could not allocate a non-existing Archive_N directory (too many conflicts)')


def _allocate_staging_dir(archive_root: str, n: int, base_prefix: str = 'Archive_', max_tries: int = 1000) -> str:
    """Allocate a non-existing staging directory next to the final Archive_N.

    Example: Archive_12.__staging__ or Archive_12.__staging__2
    """
    archive_root = os.path.abspath(archive_root)
    base = os.path.join(archive_root, f'{base_prefix}{n}.__staging__')
    if not os.path.exists(base):
        return base
    for k in range(2, 2 + int(max_tries)):
        cand = base + str(k)
        if not os.path.exists(cand):
            return cand
    raise RuntimeError('Could not allocate a non-existing staging directory (too many conflicts)')


def _repo_head_sha(repo_root: str) -> Optional[str]:
    rc, out, _ = _run_git(repo_root, ['rev-parse', 'HEAD'])
    if rc != 0:
        return None
    sha = (out or '').strip()
    return sha or None


def _repo_is_dirty(repo_root: str) -> Optional[bool]:
    rc, out, _ = _run_git(repo_root, ['status', '--porcelain'])
    if rc != 0:
        return None
    return bool((out or '').strip())


def _write_manifest_json(dest_root: str, manifest: Dict[str, object]) -> Optional[str]:
    """Best-effort manifest writer. Returns path if written."""
    try:
        os.makedirs(dest_root, exist_ok=True)
        mpath = os.path.join(dest_root, 'archive_manifest.json')
        with open(mpath, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        return mpath
    except Exception:
        return None


def backup_repo_to_archive(
    repo_root: str,
    archive_root: str,
    project_dir_name: str = 'AI_Algorithms',
    mode: str = 'committed',
    dry_run: bool = False,
    exclude_patterns: Optional[Sequence[str]] = None,
) -> Dict[str, object]:
    """Copy a selected repository file set to an external archive.

    Mode controls the source set:
        - committed (default): files present in Git HEAD
        - tracked: all tracked files in the working tree
        - full: every file in the repo folder except patterns listed in
          DEFAULT_FULL_EXCLUDES plus any provided exclude_patterns

    This is the general-purpose archive engine. The higher-level
    ``module_project_backup`` wrapper uses this function with ``mode='full'``
    and a stricter exclusion list to create the default full-project backup.

    Creates: <archive_root>/Archive_<N>/<project_dir_name>/**

    Returns a JSON-friendly dict.
    """
    repo_root = os.path.abspath(repo_root)
    if not os.path.isdir(repo_root):
        raise ValueError(f"repo_root not found: {repo_root}")

    archive_root = os.path.abspath(archive_root)
    if not archive_root:
        raise ValueError('archive_root is required')

    # Ensure the archive root exists; this is safe and does not overwrite prior archives.
    if not dry_run:
        os.makedirs(archive_root, exist_ok=True)

    n, archive_dir = _allocate_new_archive_dir(archive_root, prefix='Archive_', max_tries=10000)
    staging_dir = _allocate_staging_dir(archive_root, n, base_prefix='Archive_', max_tries=1000)
    dest_root = os.path.join(archive_dir, project_dir_name)
    staging_dest_root = os.path.join(staging_dir, project_dir_name)

    files = list_repo_files(repo_root, mode=mode, exclude_patterns=exclude_patterns)
    copied = 0
    skipped = 0
    error_count = 0
    errors: List[Dict[str, str]] = []

    # Create directories (staging first; Archive_N appears only after successful completion)
    if not dry_run:
        if os.path.exists(archive_dir):
            raise FileExistsError(f'Refusing to overwrite existing archive folder: {archive_dir}')
        if os.path.exists(staging_dir):
            raise FileExistsError(f'Refusing to overwrite existing staging folder: {staging_dir}')
        os.makedirs(staging_dest_root, exist_ok=False)

    for rel in files:
        # Safe source/dest joins
        src = safe_join(repo_root, rel)
        dst_root = staging_dest_root if not dry_run else dest_root
        dst = safe_join(dst_root, rel)
        if not os.path.exists(src):
            skipped += 1
            continue
        if os.path.isdir(src):
            # Shouldn't happen for git file list, but guard anyway
            continue
        if not dry_run:
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                if os.path.exists(dst):
                    raise FileExistsError(f'Refusing to overwrite existing file in archive: {dst}')
                shutil.copy2(src, dst)
            except Exception as e:
                error_count += 1
                # Keep the payload small/deterministic: cap the number of stored error entries.
                if len(errors) < 50:
                    errors.append({'path': rel, 'error': str(e)})
                break
        copied += 1

    manifest = {
        'ok': True,
        'dry_run': bool(dry_run),
        'repo_root': repo_root,
        'archive_root': archive_root,
        'archive_dir': archive_dir,
        'project_dir': dest_root,
        'staging_dir': staging_dir,
        'archive_number': n,
        'mode': mode,
        'file_count': len(files),
        'copied': copied,
        'skipped_missing': skipped,
        'error_count': error_count,
        'git_head': _repo_head_sha(repo_root),
        'git_dirty': _repo_is_dirty(repo_root),
        'created_ts': _now_ts(),
    }
    if errors:
        manifest['errors'] = errors
        manifest['ok'] = False

    if not dry_run:
        # If copy failed, write manifest into staging and return without finalizing.
        if not manifest.get('ok'):
            mpath = _write_manifest_json(staging_dest_root, manifest)
            if mpath:
                manifest['manifest_path'] = mpath
            return manifest

        # Finalize: rename staging -> Archive_N. This ensures Archive_N never contains partial results.
        conflict_resolutions = 0
        target_archive_dir = archive_dir
        target_dest_root = dest_root
        target_archive_number = n

        while os.path.exists(target_archive_dir):
            conflict_resolutions += 1
            target_archive_number, target_archive_dir = _allocate_new_archive_dir(
                archive_root,
                prefix='Archive_',
                max_tries=10000,
            )
            target_dest_root = os.path.join(target_archive_dir, project_dir_name)

        try:
            os.replace(staging_dir, target_archive_dir)
        except Exception as e:
            manifest['ok'] = False
            manifest['finalize_error'] = str(e)
            if conflict_resolutions:
                manifest['finalize_conflicts'] = conflict_resolutions
                manifest['archive_dir'] = target_archive_dir
                manifest['project_dir'] = target_dest_root
                manifest['archive_number'] = target_archive_number
            # Best-effort: persist manifest into staging folder for troubleshooting.
            mpath = _write_manifest_json(staging_dest_root, manifest)
            if mpath:
                manifest['manifest_path'] = mpath
            return manifest

        if conflict_resolutions:
            manifest['finalize_conflicts'] = conflict_resolutions
            manifest['archive_dir'] = target_archive_dir
            manifest['project_dir'] = target_dest_root
            manifest['archive_number'] = target_archive_number
            archive_dir = target_archive_dir
            dest_root = target_dest_root
            n = target_archive_number

        # Write manifest only after successful finalize so paths point at the final location.
        mpath = _write_manifest_json(dest_root, manifest)
        if mpath:
            manifest['manifest_path'] = mpath
        else:
            manifest['manifest_error'] = 'could_not_write_manifest'

    return manifest


def resolve_archive_root(archive_root: Optional[str] = None) -> Optional[str]:
    """Resolve archive root from explicit arg or env var.

    Env var: AI_ALGORITHMS_ARCHIVE_ROOT
    """
    if archive_root:
        return archive_root
    env = os.getenv('AI_ALGORITHMS_ARCHIVE_ROOT')
    if env:
        return env
    return None


def describe_archive_slots(
    archive_root: Optional[str] = None,
    prefix: str = 'Archive_',
) -> Dict[str, object]:
    """Inspect archive_root and report existing Archive_N folders and next slot.

    Returns a JSON-friendly dict with the resolved archive_root, the sorted list of
    matching directory names, the highest discovered N, and the next archive dir
    candidate ( Archive_<N+1> ).
    """
    root = resolve_archive_root(archive_root)
    if not root:
        raise ValueError('archive_root is required (argument or AI_ALGORITHMS_ARCHIVE_ROOT env)')

    root = os.path.abspath(root)
    try:
        names = os.listdir(root)
    except FileNotFoundError:
        names = []

    pattern = re.compile(r'^' + re.escape(prefix) + r'(\d+)$')
    slots: List[Tuple[int, str]] = []
    for name in names:
        match = pattern.match(name)
        if not match:
            continue
        try:
            slots.append((int(match.group(1)), name))
        except Exception:
            continue

    slots.sort(key=lambda item: item[0])
    highest = slots[-1][0] if slots else 0
    next_number = highest + 1
    next_dir = os.path.join(root, f'{prefix}{next_number}')

    return {
        'archive_root': root,
        'existing': [name for _, name in slots],
        'highest_number': highest,
        'next_number': next_number,
        'next_dir': next_dir,
    }


def next_archive_path(
    archive_root: Optional[str] = None,
    prefix: str = 'Archive_',
) -> Tuple[int, str]:
    """Return the next Archive_N number and path without creating it."""
    info = describe_archive_slots(archive_root=archive_root, prefix=prefix)
    return int(info['next_number']), str(info['next_dir'])
