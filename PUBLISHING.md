# Publishing this mirror

This folder is intended to be published as its own **public** GitHub repository so the desktop Copilot app (or other tooling) can access it.

## Quick publish (new repo)

1. Create an empty public GitHub repo (no README/license) named e.g. `AI_Algorithms_public_mirror`.
2. From this folder:

Windows PowerShell:

```powershell
git init
# Optional: match your default branch naming
# git checkout -b main

git add -A
git commit -m "public mirror: adversarial harness"

git remote add origin REPLACE_WITH_GITHUB_REPO_URL
# If your default branch is main:
# git push -u origin main
# If your branch is master:
# git push -u origin master
```

## Safety checklist

- Only publish the contents of this folder (not the full workspace).
- Do not include large logs, secrets, or private data.
- `config.json` in this mirror is intentionally minimized and contains no credentials.
