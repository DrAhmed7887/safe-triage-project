#!/bin/bash

set -euo pipefail

PROJECT_ID="${PROJECT_ID:-safe-triage-ai}"
REGION="${REGION:-us-central1}"
SERVICE_URL="${SERVICE_URL:-https://safe-triage-eciux5h4aq-uc.a.run.app}"
JOB_NAME="${JOB_NAME:-medgemma-hourly-review}"

echo "Setting up Cloud Scheduler job: ${JOB_NAME}"

if gcloud scheduler jobs describe "${JOB_NAME}" --location="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud scheduler jobs update http "${JOB_NAME}" \
    --schedule="0 * * * *" \
    --uri="${SERVICE_URL}/medgemma/hourly-review" \
    --http-method=POST \
    --location="${REGION}" \
    --project="${PROJECT_ID}" \
    --description="MedGemma-2B hourly QA review + reports" \
    --attempt-deadline=300s \
    --max-retry-attempts=2
  echo "Updated existing job ${JOB_NAME}"
else
  gcloud scheduler jobs create http "${JOB_NAME}" \
    --schedule="0 * * * *" \
    --uri="${SERVICE_URL}/medgemma/hourly-review" \
    --http-method=POST \
    --location="${REGION}" \
    --project="${PROJECT_ID}" \
    --description="MedGemma-2B hourly QA review + reports" \
    --attempt-deadline=300s \
    --max-retry-attempts=2
  echo "Created job ${JOB_NAME}"
fi

echo ""
echo "Scheduler jobs in ${REGION}:"
gcloud scheduler jobs list --location="${REGION}" --project="${PROJECT_ID}"

