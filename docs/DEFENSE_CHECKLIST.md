# Thesis Defense Checklist - MedGemma (Dr7.ai)

## Before Defense (No Local Setup Needed)

### Verify Dr7.ai API is working

- [ ] Check MedGemma status:

```bash
curl -s https://safe-triage-459364571026.us-central1.run.app/medgemma/status | python3 -m json.tool
```

- [ ] Confirm response includes:
  - `"provider": "Dr7.ai"`
  - `"status": "operational"`

- [ ] If status is `degraded`:
  - Verify `DR7_API_KEY` is set in Cloud Run.
  - Verify Dr7 account is active and key has not expired.

### Run final validation (optional)

- [ ] Trigger validation audit:

```bash
curl -X POST "https://safe-triage-459364571026.us-central1.run.app/medgemma/validate?days_back=7"
```

- [ ] Fetch latest report:

```bash
curl -s https://safe-triage-459364571026.us-central1.run.app/medgemma/validation-latest | python3 -m json.tool
```

## During Defense

No local terminals are required.

Show:
1. Slides with validation metrics.
2. Validation report screenshot.
3. Live `/medgemma/status` check (if internet available).

## Backup Plan

If Dr7.ai is unavailable:
- Show screenshots from prior successful runs.
- Explain fallback architecture (Vertex/Gemini safety fallback).
