# SAFE-Triage Docs Index

## MedGemma Setup

### Dr7.ai Hosted API (Production)

Advantages: managed hosting, no local setup, consistent operations.

1. Create account at [https://dr7.ai](https://dr7.ai)
2. Generate API key from Dashboard -> API Keys
3. Configure Cloud Run:

```bash
gcloud run services update safe-triage \
  --region us-central1 \
  --project safe-triage-ai \
  --update-env-vars DR7_API_KEY=dr7_your_key_here
```

4. Validate:

```bash
curl -s https://safe-triage-459364571026.us-central1.run.app/medgemma/status
```

Expected:
- `provider: Dr7.ai`
- `status: operational`

## References

- `docs/reproducibility/SYSTEM_CARD.md`
- `docs/reproducibility/EVALUATION_PROTOCOL.md`
- `docs/reproducibility/DATA_AVAILABILITY.md`
- `docs/DEFENSE_CHECKLIST.md`
- `docs/thesis_defense/Deployment_Guide.md`
- `docs/thesis_defense/Performance_Benchmark.md`
- `docs/wiki/README.md`
