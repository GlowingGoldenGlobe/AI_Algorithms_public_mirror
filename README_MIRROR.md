# public_mirror

This folder is a minimal, safe-to-publish mirror of the adversarial harness from the main repo.

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

See `PUBLISHING.md` for how to publish this folder as a public repo.
