# Deep Research Prompt for Copilot DeepResearch Package Core

**Goal:** Obtain authoritative guidance on deterministic measurement harnesses, 3D-to-relational mapping best practices, and integration test patterns for AI bridge modules.

**Context:** Repository: Copilot_DeepResearch_Package_20260201_Core. Target files: module_ai_brain_bridge.py, module_relational_adapter.py, module_measure.py. Tests must be deterministic using timestamp `2025-01-01T00:00:00Z`.

**Questions to answer:**
1. Recommended interface contract for an AI bridge module that accepts 3D measurements and an AI client, and returns a relational mapping suitable for downstream adapters.
2. Deterministic testing patterns for measurement pipelines that rely on time, randomness, or external services.
3. Minimal, robust schema for relational mapping output (required keys, types, and validation rules).
4. Common pitfalls when mocking AI brain clients and how to avoid brittle tests.
5. Example unit and integration test snippets (Python/pytest) that are CI-friendly and do not require external binaries.

**Deliverable format:** concise report (max 2 pages) with:
- 5–8 bullet recommendations
- 2 short code snippets (one mock, one test)
- A short checklist for converting a flaky test into a deterministic one

**Constraints:** Prefer authoritative sources (academic papers, engineering blogs from major AI infra teams, official pytest docs). Cite sources inline.
