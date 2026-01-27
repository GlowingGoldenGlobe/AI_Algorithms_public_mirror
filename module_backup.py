# module_backup.py

import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Tuple

from module_tools import _load_config, safe_join


def _now_ts() -> str:
    """Return a timestamp string.

    - If deterministic mode is enabled, returns `config.json > determinism.fixed_timestamp`.
    - Otherwise returns current UTC Zulu timestamp.
    """
    try:
        cfg = _load_config() or {}
        det = cfg.get('determinism', {}) if isinstance(cfg, dict) else {}
        if det.get('deterministic_mode') and det.get('fixed_timestamp'):
            return str(det.get('fixed_timestamp'))
    except Exception:
        pass
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


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


def list_repo_files(repo_root: str, mode: str = 'committed') -> List[str]:
    """List repo file paths (relative, POSIX-ish) to back up.

    Modes:
    - committed: only files present in HEAD (i.e., what would be on remote after push)
    - tracked: all tracked files in working tree (may include uncommitted changes)

    Returns a sorted list of relative paths.
    """
    repo_root = os.path.abspath(repo_root)
    mode = str(mode or 'committed').lower().strip()

    if mode not in ('committed', 'tracked'):
        raise ValueError("mode must be 'committed' or 'tracked'")

    if mode == 'committed':
        rc, out, err = _run_git(repo_root, ['ls-tree', '-r', '--name-only', 'HEAD'])
        if rc != 0:
            raise RuntimeError(f"git ls-tree failed: {err.strip()}")
        files = [line.strip() for line in out.splitlines() if line.strip()]
    else:
        rc, out, err = _run_git(repo_root, ['ls-files'])
        if rc != 0:
            raise RuntimeError(f"git ls-files failed: {err.strip()}")
        files = [line.strip() for line in out.splitlines() if line.strip()]

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
) -> Dict[str, object]:
    """Copy repo files to an external archive, including only Git-listed files.

    Creates:
      <archive_root>/Archive_<N>/<project_dir_name>/... (mirrors repo paths)

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

    files = list_repo_files(repo_root, mode=mode)
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
        try:
            if os.path.exists(archive_dir):
                raise FileExistsError(f'Refusing to overwrite existing archive folder: {archive_dir}')
            os.replace(staging_dir, archive_dir)
        except Exception as e:
            manifest['ok'] = False
            manifest['finalize_error'] = str(e)
            # Best-effort: persist manifest into staging folder for troubleshooting.
            mpath = _write_manifest_json(staging_dest_root, manifest)
            if mpath:
                manifest['manifest_path'] = mpath
            return manifest

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
