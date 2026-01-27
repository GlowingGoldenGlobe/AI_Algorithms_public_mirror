# Secrets / Owner-Only Information

This repo can be opened locally or published (e.g., GitHub, static website). Treat any committed file as **public**.

## Rule of thumb

- If it’s in git, it’s not a secret.
- Hiding text in HTML/JS (or putting it behind a “hidden” UI) is not security.

## What should be treated as secrets

- Owner names, emails, phone numbers
- API keys, tokens, credentials
- Internal URLs that require authentication

## Recommended pattern (local-only secrets file)

1. Keep a local file **outside** of version control:
   - `secrets.local.json` (ignored by `.gitignore`)

2. Optional: keep a non-sensitive example in git:
   - `secrets.example.json`

3. If you want the dashboard to display owner-only info, load it locally:
   - Use the “Load Secrets” button in `index.html` (reads a local file via browser file picker).

### Example schema

```json
{
  "owner": {
    "feature_owner": "(private)",
    "sre_ci_owner": "(private)",
    "qa_adversarial_lead": "(private)",
    "contact_email": "(private)"
  },
  "links": {
    "private_runbook_url": "(private)",
    "ticket_queue_url": "(private)"
  }
}
```

## About putting secrets on a website “and having the project search for it”

If the website is public (or searchable), the data is **not secret**.

If you truly need remote retrieval:
- Use an authenticated secrets manager or a private API endpoint (requires auth).
- Prefer storing owner info in a password manager or secure note and copying it when needed.

This repo intentionally stays **offline-friendly** and avoids building a remote secret-fetch mechanism.
