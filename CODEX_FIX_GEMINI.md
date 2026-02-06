# CODEX TASK: Fix Gemini AI Integration - FULL AUTONOMY

## CURRENT STATE
- Health endpoint: `{"ai":{"status":"ok","mode":"api_key","model":"gemini-2.5-flash"}}` ✅
- Triage endpoint: Returns `ai_data: null`, falls back to deterministic ❌
- No Gemini logs appear when /ai-triage is called
- Import in main.py looks correct: `from ai_service import ai_service`

## YOUR MISSION
Find why `ai_service.analyze_triage()` is not being called or its result is discarded.

## FILES TO EXAMINE

### 1. backend/main.py - Around line 149
Look for the ai_triage endpoint. Check:
- Is `ai_service.analyze_triage()` actually called?
- Is the result used or discarded?
- Is there a try/except swallowing errors silently?
- Is there conditional logic skipping the AI call?

### 2. backend/ai_service.py
Verify:
- Singleton `ai_service = AIService()` exists at bottom
- `analyze_triage()` method has proper logging

## EXPECTED CODE FLOW
```
POST /ai-triage 
  → main.py ai_triage() 
  → ai_service.analyze_triage(patient_data)
  → Gemini API call
  → Return JSON with ai_data populated
```

## DEBUGGING APPROACH

### Step 1: Add trace logging to main.py ai_triage endpoint
Find the endpoint and add prints:
```python
@app.post("/ai-triage")
async def ai_triage(request: TriageRequest):
    print("=" * 50, flush=True)
    print("🏥 AI-TRIAGE ENDPOINT CALLED", flush=True)
    print(f"   ai_service.client = {ai_service.client}", flush=True)
    print(f"   ai_service.mode = {ai_service.mode}", flush=True)
    # ... rest of function
```

### Step 2: Find where ai_result is used
Search for `ai_result` and trace if it's:
- Assigned but never used in response
- Overwritten 
- Conditionally skipped

### Step 3: Check the response building
The response must include `ai_data=ai_result` or similar.

## LIKELY BUG PATTERNS

### Pattern A: Silent try/except
```python
try:
    ai_result = ai_service.analyze_triage(...)
except:
    pass  # BUG: silently ignores errors
```
FIX: Add `print(f"AI error: {e}", flush=True)`

### Pattern B: Result not included in response
```python
ai_result = ai_service.analyze_triage(...)
# ... lots of code ...
return TriageResponse(
    level=level,
    # ai_data=ai_result  # MISSING!
)
```
FIX: Add `ai_data=ai_result` to response

### Pattern C: Conditional skip
```python
if some_condition:
    ai_result = ai_service.analyze_triage(...)
else:
    ai_result = None  # Always hits this branch
```
FIX: Check the condition

## COMMANDS TO RUN AFTER FIX
```bash
# Deploy
gcloud run deploy safe-triage --source ./backend --region me-west1 \
  --allow-unauthenticated --memory 2Gi \
  --set-env-vars="PYTHONPATH=/app,PYTHONUNBUFFERED=1,GEMINI_API_KEY=YOUR_GEMINI_API_KEY"

# Test
curl -X POST "https://safe-triage-459364571026.me-west1.run.app/ai-triage" \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"CODEX-FIX","age":45,"gender":"female","chief_complaint_text":"severe headache","vitals":{"hr":88,"sbp":130,"dbp":85,"rr":18,"temp":37.2,"spo2":98},"consciousness":"A"}'

# Check logs
gcloud run services logs read safe-triage --region me-west1 --limit 30
```

## SUCCESS CRITERIA
Response includes `"ai_data"` with actual content (not null):
```json
{
  "ai_data": {
    "extracted_symptoms": ["headache", "..."],
    "clinical_impression": "...",
    "differential_diagnosis": ["..."]
  }
}
```

## START HERE
1. Read backend/main.py lines 140-200 (ai_triage function)
2. Trace the ai_result variable
3. Find why it's not in the response
4. Fix and deploy
