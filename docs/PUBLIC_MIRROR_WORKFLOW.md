# Public mirror workflow (two repos)

## Where are the git-operation docs?

This repo has *two* places where “git operations” are documented, depending on whether you’re working in the **main repo** or the **mirror repo**:

- Main repo (this workspace): `README.md` → **Version Control** section (init/commit/push the main code repo).
- Mirror repo (inside `public_mirror/`): `public_mirror/PUBLISHING.md` (how to publish/update the mirror as its own GitHub repo).
- Mirror overview: `public_mirror/README_MIRROR.md` (two-repo explanation + pointers).

This file focuses on the **mirror repo workflow** (regenerate → publish).

This project uses two separate Git repositories:

1) **Main repo** (this workspace)
- Contains source code and tooling.
- Generates the `public_mirror/` folder as an artifact.
- Intentionally **does not track** `public_mirror/` in git (it is ignored).

2) **Mirror repo** (inside `public_mirror/`)
- A separate, public Git repo that you publish to GitHub so the desktop Copilot app (and other tools) can read it.
- You commit/push updates from inside the `public_mirror/` folder.

---

## Regenerate the mirror (recommended)

From the main repo root:

```powershell
py -3 scripts/create_public_mirror.py --profile core_thinking --preserve-git
```

Notes:
- Use `--preserve-git` if `public_mirror/` already has its own `.git/` folder (common on Windows to avoid file-lock churn and to keep the mirror repo intact).
- The authoritative allowlist is captured in `public_mirror/mirror_manifest.json`.

---

## Publish/update the mirror repo

### Fast path: sync workspace HTML + publish (pull → copy → smart merge → commit → push)

If you maintain `public_mirror/glowinggoldenglobe_workspace.html` by copying it from an external mirror folder, use:

```powershell
${workspaceFolder}/.venv/Scripts/python.exe scripts/sync_publish_public_mirror_workspace_html.py \
	--source "C:/Users/.../public_mirror" \
	--commit-message "mirror: sync workspace html"
```

This runs the correct order automatically:
- `git -C public_mirror pull --ff-only` (get the latest mirror repo first)
- copy the latest `glowinggoldenglobe_workspace.html` into `public_mirror/`
- preserve any local overlay block (if present)
- commit + push only if there are actual changes

Tip: set `PUBLIC_MIRROR_SOURCE` so you don't have to pass `--source` each time.

From inside the mirror folder:

```powershell
cd public_mirror

git status
# review changes

git add -A
# pick a clear message like "mirror: refresh core_thinking"
git commit -m "mirror: refresh"
git push
```

If this is the first time publishing, follow `public_mirror/PUBLISHING.md`.

---

## Why the main repo ignores `public_mirror/`

Keeping the generated mirror out of the main repo:
- prevents constant “dirty working tree” noise,
- avoids accidentally committing large/duplicated artifacts,
- keeps review focused on the real source of truth.

If you need to change what the mirror contains, edit `scripts/create_public_mirror.py` in the main repo and regenerate.
