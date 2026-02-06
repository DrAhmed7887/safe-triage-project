# Human Confirmation Design (SAFE-Triage)

Date: 2026-02-05

## Goal
Ensure SAFE-Triage does **not** auto-assign ESI. Final decisions require clinician confirmation, with audit trail and escalation after 5 minutes.

## Proposed Backend API

### 1) Create Confirmation Request (server-side on triage result)
- Triggered by `/ai-triage` and `/triage` responses.
- Stores a pending confirmation record.

### 2) POST `/confirm-triage`
**Body**
```
{
  "patient_id": "...",
  "recommended_esi": 2,
  "confirmed_esi": 2,
  "clinician_id": "...",
  "action": "confirmed" | "overridden",
  "override_reason": "...",
  "timestamp": "..."
}
```
**Behavior**
- Writes to BigQuery `triage_confirmations`
- If `confirmed_esi <= 2`, send alert (Telegram + n8n)
- Marks pending record as resolved

### 3) GET `/pending-confirmations`
Returns unconfirmed triage cases for supervisor dashboard.

### 4) POST `/override-triage`
- Requires supervisor approval if downgrading (e.g., ESI 2 -> 3)
- Stores override reason, approver ID, and PIN validation result

## Data Model (BigQuery)
Table: `triage_confirmations`
- `patient_id` (STRING)
- `recommended_esi` (INTEGER)
- `confirmed_esi` (INTEGER)
- `action` (STRING: confirmed | overridden)
- `override_reason` (STRING)
- `clinician_id` (STRING)
- `supervisor_id` (STRING, nullable)
- `timestamp` (TIMESTAMP)
- `response_time_seconds` (INTEGER)
- `escalated` (BOOLEAN)

## Frontend UX

### Component: `TriageConfirmation`
- Displays recommended ESI + category + red flags
- Countdown timer (default 5 minutes)
- Buttons:
  - **Confirm ESI**
  - **Override** (dropdown + reason)
- If timer expires: auto-escalate to supervisor queue

### Escalation
- 5-minute timeout triggers:
  - Supervisor alert via n8n (WhatsApp/SMS/email)
  - Case moves to `/pending-confirmations`

## Open Decisions (Ahmed Approval Needed)
1. Supervisor PIN policy (static vs rotating)
2. Allowed roles for override (nurse vs physician vs supervisor)
3. Timeout duration (default 5 min; should this be configurable?)
4. Escalation channels (Telegram only vs n8n multi-channel)

## Safety Notes
- Overrides must be logged with reason.
- Downgrades should require supervisor PIN.
- No auto-assignment is permitted by safety plan.
