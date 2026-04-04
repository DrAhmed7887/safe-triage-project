#!/usr/bin/env bash
# Setup hourly budget guard via Cloud Scheduler.
#
# This creates a Cloud Scheduler job that runs budget_guard.py every hour
# via a Cloud Run job, auto-undeploying endpoints if the $1,000 budget is hit.
#
# Prerequisites:
#   - gcloud CLI authenticated
#   - Cloud Scheduler API enabled
#   - Cloud Run API enabled
#
# Usage:
#   bash setup_budget_guard.sh
#   bash setup_budget_guard.sh --budget 800   # custom cap

set -euo pipefail

PROJECT_ID="${PROJECT_ID:-safe-triage-ai}"
REGION="${REGION:-us-central1}"
BUDGET="${1:-950}"

echo "=== Budget Guard Setup ==="
echo "  Project:  $PROJECT_ID"
echo "  Region:   $REGION"
echo "  Budget:   \$$BUDGET"
echo ""

# 1. Enable required APIs
echo "[1/3] Enabling APIs..."
gcloud services enable cloudscheduler.googleapis.com run.googleapis.com --project="$PROJECT_ID" --quiet

# 2. Create Cloud Run job for budget guard
echo "[2/3] Creating Cloud Run job..."
gcloud run jobs create budget-guard \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --image="us-docker.pkg.dev/cloudrun/container/job:latest" \
  --command="python3" \
  --args="budget_guard.py,--budget,$BUDGET" \
  --set-env-vars="PROJECT_ID=$PROJECT_ID,VERTEX_REGION=$REGION,VERTEX_BUDGET_USD=$BUDGET" \
  --max-retries=1 \
  --task-timeout=300s \
  --quiet 2>/dev/null || \
gcloud run jobs update budget-guard \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --args="budget_guard.py,--budget,$BUDGET" \
  --set-env-vars="PROJECT_ID=$PROJECT_ID,VERTEX_REGION=$REGION,VERTEX_BUDGET_USD=$BUDGET" \
  --quiet

# 3. Create hourly scheduler
echo "[3/3] Creating Cloud Scheduler job (hourly)..."
gcloud scheduler jobs create http budget-guard-hourly \
  --project="$PROJECT_ID" \
  --location="$REGION" \
  --schedule="0 * * * *" \
  --uri="https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/budget-guard:run" \
  --http-method=POST \
  --oauth-service-account-email="$PROJECT_ID@appspot.gserviceaccount.com" \
  --quiet 2>/dev/null || \
echo "  (Scheduler job already exists — update manually if needed)"

echo ""
echo "=== Setup Complete ==="
echo "  Budget guard will run every hour."
echo "  Manual check:  python budget_guard.py --status"
echo "  Manual run:    python budget_guard.py --budget $BUDGET"
echo "  Dry run:       python budget_guard.py --dry-run"
echo ""
echo "  Hard stop triggers at \$$BUDGET (buffer from \$1,000 credit)."
echo "  All Vertex AI endpoints will be undeployed automatically."
