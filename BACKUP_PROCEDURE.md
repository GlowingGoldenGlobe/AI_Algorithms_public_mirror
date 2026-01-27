# BACKUP_PROCEDURE.md — External Archive (Git-only)

## Goal

Create an external “Archive_N” backup that contains *only* files that belong to the Git repo (the same set of files you’d push to GitHub), avoiding local artifacts like venv folders, caches, runtime stores, etc.

This is implemented by `module_backup.py` and exposed via `cli.py backup`.

## What gets copied

Two modes are available:

- **committed (default)**: copies files from `HEAD` only (i.e., committed content).
  - This best matches “what’s on the remote” after you push.
- **tracked**: copies all tracked files in your working tree (may include uncommitted modifications).

Both modes explicitly avoid copying untracked / ignored files because they are not listed by Git.

## One-time setup

Set the archive root path via env var (recommended):

- `AI_ALGORITHMS_ARCHIVE_ROOT=E:\Archive_AI_Algorithms`

Or pass it each time with `--archive-root`.

## Usage

Dry-run (shows where it would write and how many files):

- `py -3 cli.py backup --archive-root E:\Archive_AI_Algorithms --dry-run`

Create the next archive folder:

- `py -3 cli.py backup --archive-root E:\Archive_AI_Algorithms`

Use tracked mode (includes uncommitted tracked edits):

- `py -3 cli.py backup --archive-root E:\Archive_AI_Algorithms --mode tracked`

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

- Git `HEAD` hash
- `git_dirty` indicator
- file counts and copy stats
- created timestamp (deterministic-fixed timestamp when determinism mode is enabled)
