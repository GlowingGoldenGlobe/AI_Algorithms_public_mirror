"""Full-project backup wrapper for external archive copies.

This module differentiates the user-facing full-project backup flow from the
lower-level archive helpers in ``module_backup``. It preserves runtime and
project data such as ``ActiveSpace/`` while excluding environment, cache, and
third-party folders that should not be copied into the archive.
"""

import os
from typing import Dict, List, Optional, Sequence, Tuple

from module_backup import DEFAULT_FULL_EXCLUDES, backup_repo_to_archive


DEFAULT_PROJECT_BACKUP_EXCLUDES: Tuple[str, ...] = DEFAULT_FULL_EXCLUDES + (
    '.git',
    '.ruff_cache',
    '.coverage',
    'htmlcov',
    '.ipynb_checkpoints',
)


def _normalize_patterns(patterns: Optional[Sequence[str]]) -> List[str]:
    normalized: List[str] = []
    for pattern in patterns or ():
        value = str(pattern or '').replace('\\', '/').strip('/')
        if value:
            normalized.append(value)
    return normalized


def project_backup_excludes(extra_excludes: Optional[Sequence[str]] = None) -> List[str]:
    """Return the exclusion list for full-project backups."""
    excludes = list(DEFAULT_PROJECT_BACKUP_EXCLUDES)
    for pattern in _normalize_patterns(extra_excludes):
        if pattern not in excludes:
            excludes.append(pattern)
    return excludes


def backup_project_to_archive(
    repo_root: str,
    archive_root: str,
    project_dir_name: str = 'AI_Algorithms',
    dry_run: bool = False,
    exclude_patterns: Optional[Sequence[str]] = None,
) -> Dict[str, object]:
    """Create the default full-project archive copy.

    Unlike the legacy Git-only backup modes, this wrapper walks the project tree
    and keeps runtime/project folders that are not tracked by Git, while still
    excluding environment, cache, and third-party directories.
    """
    excludes = project_backup_excludes(exclude_patterns)
    manifest = backup_repo_to_archive(
        repo_root=repo_root,
        archive_root=archive_root,
        project_dir_name=project_dir_name,
        mode='full',
        dry_run=dry_run,
        exclude_patterns=excludes,
    )
    manifest['backup_scope'] = 'project'
    manifest['exclude_patterns'] = excludes
    return manifest