# SAFE-Triage Deployment Guide

## Prerequisites
- Google Cloud project with billing enabled
- UMLS API key
- Firebase project for frontend hosting

## Environment Variables
- `UMLS_API_KEY`: UMLS API key
- `USE_VERTEX_SPEECH`: `true` to enable Speech-to-Text
- `SUPERVISOR_PIN`: Supervisor PIN for downgrades (default `0000`)
- `CONFIRMATION_TIMEOUT_SECONDS`: default `300`

## Backend Deploy (Cloud Run)
```bash
gcloud run deploy safe-triage \
  --source ./backend \
  --region us-central1 \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 10 \
  --allow-unauthenticated \
  --project safe-triage-ai \
  --set-env-vars="UMLS_API_KEY=... ,USE_VERTEX_SPEECH=true,SUPERVISOR_PIN=0000,CONFIRMATION_TIMEOUT_SECONDS=300"
```

## Frontend Deploy (Firebase)
```bash
cd frontend
npm run build
firebase deploy --only hosting
```

## Speech-to-Text Enablement
```bash
gcloud services enable speech.googleapis.com --project safe-triage-ai
gcloud projects add-iam-policy-binding safe-triage-ai \
  --member="serviceAccount:459364571026-compute@developer.gserviceaccount.com" \
  --role="roles/speech.client"
```

## MedGemma QA Job
```bash
gcloud run jobs deploy medgemma-qa-review \
  --source ./backend \
  --region us-central1 \
  --project safe-triage-ai \
  --command python \
  --args jobs/medgemma_qa_job.py

gcloud scheduler jobs create http medgemma-qa-schedule \
  --location us-central1 \
  --schedule "*/15 * * * *" \
  --uri "https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/safe-triage-ai/jobs/medgemma-qa-review:run" \
  --http-method POST \
  --oauth-service-account-email 459364571026-compute@developer.gserviceaccount.com
```
