# CODEX TASK: Debug Gemini AI Integration on Cloud Run

## PROBLEM
AI triage falls back to deterministic mode. `ai_data: null` in responses.
No Gemini logs appearing despite successful HTTP 200.

## DEPLOYED SERVICE
- URL: https://safe-triage-459364571026.me-west1.run.app
- Project: safe-triage-ai
- Region: me-west1
- API Key env var: GEMINI_API_KEY is set

## DIAGNOSIS STEPS

### Step 1: Check if AI service initializes
Add explicit startup logging to see if AIService.__init__ runs:
```python
# In ai_service.py, at very top of __init__:
print("=" * 60, flush=True)
print("🚀 AIService.__init__ STARTING", flush=True)
print(f"   GEMINI_API_KEY present: {bool(os.getenv('GEMINI_API_KEY'))}", flush=True)
print("=" * 60, flush=True)
```

### Step 2: Check if singleton is imported in main.py
Verify main.py line 17 says:
```python
from ai_service import ai_service  # NOT AIService
```

And NO duplicate instantiation anywhere (search for `AIService()`).

### Step 3: Check the /ai-triage endpoint
In main.py, add logging at start of ai_triage endpoint:
```python
@app.post("/ai-triage")
async def ai_triage(request: TriageRequest):
    print(f"🏥 /ai-triage called, ai_service.client={ai_service.client}", flush=True)
    print(f"   ai_service.mode={ai_service.mode}", flush=True)
```

### Step 4: Test health endpoint
```bash
curl https://safe-triage-459364571026.me-west1.run.app/health | jq .ai
```
Should show: `{"status":"ok","mode":"api_key","model":"gemini-2.5-flash"}`

If mode is "none" → API key not being read
If mode is "vertex" → API key fallback failed

### Step 5: Verify API key works locally
```bash
cd backend
GEMINI_API_KEY=AIzaSyAoNjF3ydHvr2EZnCxbz0hA6rhCIaI7pjg python3 -c "
from ai_service import ai_service
print(f'Mode: {ai_service.mode}')
print(f'Client: {ai_service.client}')
result = ai_service.analyze_triage({
    'age': 55,
    'gender': 'male', 
    'chief_complaint_text': 'chest pain',
    'vitals': {'hr': 90, 'sbp': 120}
})
print(f'Result: {result}')
"
```

## LIKELY ROOT CAUSES

1. **main.py still creates duplicate AIService()** - singleton not used
2. **Environment variable not reaching ai_service.py** - check Cloud Run env vars
3. **Import order issue** - ai_service singleton created before env loaded
4. **Silent exception in __init__** - add try/except with print

## FIX TEMPLATE

If the issue is duplicate instantiation in main.py:
```python
# main.py line 17 - CORRECT:
from ai_service import ai_service

# REMOVE any line like:
# ai_service = AIService()
```

If the issue is env var not loaded:
```python
# ai_service.py - load env BEFORE class definition
import os
from dotenv import load_dotenv
load_dotenv()

# Debug print
print(f"ENV CHECK: GEMINI_API_KEY={'YES' if os.getenv('GEMINI_API_KEY') else 'NO'}", flush=True)
```

## DEPLOY & TEST
```bash
gcloud run deploy safe-triage --source ./backend --region me-west1 \
  --allow-unauthenticated --memory 2Gi \
  --set-env-vars="PYTHONPATH=/app,PYTHONUNBUFFERED=1,GEMINI_API_KEY=AIzaSyAoNjF3ydHvr2EZnCxbz0hA6rhCIaI7pjg"

# Then test:
curl -X POST "https://safe-triage-459364571026.me-west1.run.app/ai-triage" \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"DEBUG","age":55,"gender":"male","chief_complaint_text":"headache","vitals":{"hr":80,"sbp":120,"dbp":80,"rr":16,"temp":37,"spo2":98},"consciousness":"A"}'

# Check logs:
gcloud run services logs read safe-triage --region me-west1 --limit 50
```
