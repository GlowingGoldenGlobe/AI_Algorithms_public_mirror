AI_Algorithms — dashboard.html

What it is:
- dashboard.html is a self-contained, offline-friendly dashboard for viewing:
  - metrics.json counters
  - adversarial_report_*.json summaries
  - escalation event table (best-effort heuristics)
  - charts via Plotly CDN

How to use (offline / file://):
1) Open dashboard.html in a browser.
2) Use the file pickers:
   - metrics.json: select TemporaryQueue\metrics.json
   - adversarial_report_*.json: select one or more report files
   - sweep_results.csv: optional
3) Click “Render Dashboard”.

Why file pickers:
- Browsers do not allow reading arbitrary local files or listing directories for security.

Optional “server mode” (enables relative-path fetch):
1) From repo root, run:
   py -3 -m http.server 8000
2) Open:
   http://localhost:8000/dashboard.html
3) Click “Try Fetch Defaults (server mode)”.

Note:
- The dashboard cannot discover all adversarial report filenames automatically; server mode tries a small set of known candidate names.
- File picker mode is the most reliable.
