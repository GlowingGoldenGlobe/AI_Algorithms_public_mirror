# BACKUP_PROCEDURE.md — External Archive

## Goal

Create an external `Archive_N` backup that copies the full project tree while excluding third-party, environment, build, and cache folders.

This is implemented by `module_project_backup.py` and exposed via `cli.py backup`.

## What gets copied

Three modes are available:

- **full (default)**: copies the project tree and preserves runtime/project folders such as `ActiveSpace/`, while excluding known environment/build/cache folders.
- **committed**: copies files from `HEAD` only (i.e., committed content).
  - This best matches “what’s on the remote” after you push.
- **tracked**: copies all tracked files in your working tree (may include uncommitted modifications).

The default full-project mode excludes these directories by default:

- `.git`
- `.venv`
- `venv`
- `env`
- `.tox`
- `.nox`
- `node_modules`
- `build`
- `dist`
- `__pycache__`
- `.mypy_cache`
- `.pytest_cache`
- `.ruff_cache`
- `htmlcov`
- `.ipynb_checkpoints`

Legacy Git-only modes remain available when you explicitly need repo-only material.

## One-time setup

Set the archive root path via env var (recommended):

- `AI_ALGORITHMS_ARCHIVE_ROOT=E:\Archive_AI_Algorithms`

Or pass it each time with `--archive-root`.

## Usage

Dry-run (shows where it would write and how many files):

- `py -3 cli.py backup --archive-root E:\Archive_AI_Algorithms --dry-run`

Create the next full-project archive folder:

- `py -3 cli.py backup --archive-root E:\Archive_AI_Algorithms`

Use tracked mode (includes uncommitted tracked edits only):

- `py -3 cli.py backup --archive-root E:\Archive_AI_Algorithms --mode tracked`

Use committed mode (Git `HEAD` only):

- `py -3 cli.py backup --archive-root E:\Archive_AI_Algorithms --mode committed`

## Output layout

Backups are created like:

- `<archive_root>/Archive_<N>/AI_Algorithms/<repo files...>`

Safety:

- The backup command will never write into an existing `Archive_<N>` folder.
- If a candidate `Archive_<N>` already exists (e.g., due to a concurrent backup or manual folder creation), it will advance to the next available number.
- As a defense-in-depth guard, it will also refuse to overwrite any file path if it somehow already exists in the destination.

Staging behavior:

- The backup copies into a temporary sibling folder first (e.g., `Archive_<N>.__staging__*`).
- Only after all files copy successfully does it rename the staging folder to `Archive_<N>`.
- Result: `Archive_<N>` never appears in a partially-copied state.

Failure reporting:

- `cli.py backup` always prints JSON.
- On failure, the JSON includes `ok: false`, `error_count`, and an `errors` list (capped).
- A troubleshooting manifest is also written into the staging folder at:
  - `Archive_<N>.__staging__*/AI_Algorithms/archive_manifest.json`

Exit codes:

- `0`: success
- `2`: missing archive root (neither `--archive-root` nor `AI_ALGORITHMS_ARCHIVE_ROOT` provided)
- `3`: copy failure (stopped during staging copy; see `errors` and staging manifest)
- `4`: finalize failure (rename staging to `Archive_<N>` failed; see `finalize_error` and staging manifest)
- `1`: other error

A manifest is written to:

- `<archive_root>/Archive_<N>/AI_Algorithms/archive_manifest.json`

The manifest includes:

- backup scope and active exclude list for full-project backups
- Git `HEAD` hash
- `git_dirty` indicator
- file counts and copy stats
- created timestamp (deterministic-fixed timestamp when determinism mode is enabled)
