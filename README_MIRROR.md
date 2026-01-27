# public_mirror

This folder is a minimal, safe-to-publish mirror generated from the main repo.

- Profile `adversarial`: smallest runnable adversarial harness + tests.
- Profile `core_thinking`: broader review set (all `module_*.py` plus selected docs).

For an authoritative file list, see `mirror_manifest.json`.

## Two-repo workflow (important)

This folder is generated from the main repo, but is meant to be published as a **separate public git repo**.

- In the main repo, `public_mirror/` is intentionally ignored (so `git status` in the main repo will not show mirror changes).
- To publish updates, regenerate the mirror from the main repo, then commit/push from inside `public_mirror/`.

If present (profile `core_thinking`), see `docs/PUBLIC_MIRROR_WORKFLOW.md` for the step-by-step.

## What to run

Windows (PowerShell):

```powershell
py -3 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
pytest -q
python run_eval.py
```

macOS/Linux (bash):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt
pytest -q
python run_eval.py
```

## Files

- `module_adversarial_test.py` provides `run_scenario(...)`.
- `tests/test_adversarial.py` exercises scenarios S1–S6.
- `run_eval.py` is mirror-only and runs the adversarial eval gates.

## Assessment progression

If present (profile `core_thinking`), start with:

- `roadmap_table_2.md` (assessment-oriented progression)
- `temp_12.md` (change log; what passed eval)

See `PUBLISHING.md` for how to publish this folder as a public repo.
