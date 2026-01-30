# VS Code chat + task contract (AI_Algorithms)

This document describes the **expected VS Code Copilot Chat setup** and the **project task labels** that external automation (for example, `AI_Coder_Controller`) can assume when operating this workspace.

This is intentionally **low-detail** and **safe-to-publish**:
- It does not include secrets.
- It does not include machine-specific absolute paths.
- It avoids UI pixel coordinates.

---

## Expected Copilot Chat setup

### Chat views/tabs

- Expected **qty** of Copilot Chat views: **1**.
- Expected view: **GitHub Copilot Chat** (VS Code side panel view).

Notes:
- VS Code “chat tabs” are UI state and are not reliably representable in a repo artifact.
- Automation should treat the chat view as a **single target**: open/focus it, send a message, wait for a response.

### Expected behavior

- The chat thread is expected to be used for: status checks, prompts to run tasks, and lightweight “keep-alive / continue” nudges.
- Long-running work should be driven by **VS Code Tasks** (below) rather than by chat alone.

---

## Project tasks (labels)

These are the **task labels** expected to exist in this workspace’s VS Code Task Runner.

### Core

- `AI Brain: status`
- `AI Brain: eval`
- `AI Brain: stress`

### Background helpers

- `AI Brain: dashboard (bg)` (serves static pages over `http://127.0.0.1:8000/`)
- `AI Brain: metrics watch (bg)` (optional)

### Public mirror

- `Public mirror: build (core_thinking)`

---

## Integration notes for AI_Coder_Controller

- The controller should be able to run in a separate VS Code window/workspace, then operate this workspace by:
  - Bringing the AI_Algorithms VS Code window to the foreground.
  - Opening/focusing the Copilot Chat view.
  - Issuing prompts that instruct a human/agent to run the named VS Code tasks.

If your automation needs a stricter contract (machine-readable JSON, required extensions, or command IDs), add a separate `docs/VSCODE_AUTOMATION_CONTRACT.json` and keep it free of secrets/absolute paths.
