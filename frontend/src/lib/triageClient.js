/**
 * triageClient.js — calls the canonical Python triage engine via the FastAPI
 * backend when one is configured, and falls back to the JS offline engine
 * when the network call fails. Hospital Lite App Store builds do not ship
 * with a backend URL, so they run the local deterministic fallback directly.
 *
 * The Python engine in `backend/logic/triage_engine_v2.py` is the *source of
 * truth* — it is what the project benchmarks against (MIETIC, MIETIC-Arabic,
 * KTAS, NHAMCS). This module's job is to:
 *
 *   1. Map the Hospital Lite form payload to the backend `PatientInput` shape.
 *   2. POST it to `/triage` with a tight timeout when a backend URL exists.
 *   3. Adapt the backend `TriageResult` to the UI-facing suggestion shape.
 *   4. On any failure (offline, timeout, 4xx/5xx, parse error), call the
 *      offline JS fallback engine and tag the result so the UI can warn.
 *
 * The returned object always has `engine_source` set to either
 * `'python_engine'` or `'offline_js_fallback'`. The UI must surface this.
 */

import { runOfflineFallbackTriage, LEVEL_LABELS, ESI_CATEGORIES } from './triageEngineOfflineFallback';

const RAW_API_URL = (import.meta.env.VITE_API_URL || '').trim();
const API_URL = RAW_API_URL.replace(/\/$/, '');
const TRIAGE_TIMEOUT_MS = 6000;

/**
 * Convert a Hospital Lite form payload into the shape the backend expects.
 * Backend Vitals fields: hr, rr, spo2, temp, sbp, dbp, gcs (all optional).
 * Backend PatientInput requires: age, gender, chief_complaint_text, vitals.
 */
function toPatientInput(input) {
    const v = input.vitals || {};
    const num = (x) => (x === '' || x == null ? null : Number(x));
    return {
        patient_id: input.patient_id || null,
        patient_name: input.patient_name || null,
        age: Number(input.age),
        gender: input.gender || 'male',
        chief_complaint_text: (input.chief_complaint_text || '').trim(),
        vitals: {
            hr:   num(v.hr),
            rr:   num(v.rr),
            spo2: num(v.spo2),
            temp: num(v.temp),
            sbp:  num(v.sbp),
            dbp:  num(v.dbp),
        },
        consciousness: (input.consciousness || 'A').toUpperCase(),
        pain_scale: input.pain_scale != null ? Number(input.pain_scale) : null,
        is_pregnant: Boolean(input.is_pregnant),
        is_copd: Boolean(input.is_copd),
        on_supplemental_o2: Boolean(input.on_supplemental_o2),
        is_immunocompromised: Boolean(input.is_immunocompromised),
        immuno_compromised: Boolean(input.is_immunocompromised),
    };
}

/**
 * Adapt the backend `TriageResult` (see backend/models.py) to the same
 * suggestion shape `runOfflineFallbackTriage` returns. This keeps every
 * component downstream agnostic to which engine produced the answer.
 */
function adaptBackendResult(raw) {
    const level = Number(raw.level) || 3;
    const levelLabel = LEVEL_LABELS[level] || LEVEL_LABELS[3];

    const category = raw.category || 'unclear_needs_evaluation';
    const categoryLabel = ESI_CATEGORIES[category] || {
        level,
        en: raw.label_en || levelLabel.en,
        ar: raw.label_ar || levelLabel.ar,
    };

    // Floors come back as an array of strings (`safety_floors_applied`) plus
    // free-text notes (`safety_floors` / `red_flag_summary`). The UI's
    // floor card expects { name, level, reason_en, reason_ar }.
    const floorNames = Array.isArray(raw.safety_floors_applied) ? raw.safety_floors_applied : [];
    const floorNotes = Array.isArray(raw.safety_floors) ? raw.safety_floors : [];
    const floorsApplied = [];
    for (let i = 0; i < floorNames.length; i++) {
        const note = floorNotes[i] || floorNames[i];
        floorsApplied.push({
            name: floorNames[i],
            level,
            reason_en: typeof note === 'string' ? note : floorNames[i],
            reason_ar: typeof note === 'string' ? note : floorNames[i],
        });
    }

    const reasoningEn = Array.isArray(raw.reasoning_en) ? raw.reasoning_en
                      : Array.isArray(raw.reasoning)    ? raw.reasoning : [];

    return {
        level,
        level_label: levelLabel,
        category,
        category_label: categoryLabel,
        category_confidence: 'backend',
        news2: {
            // The backend response carries a NEWS2 score on the determ. engine
            // path but the public TriageResult only exposes the final level,
            // not the breakdown. Surface what we have; the UI handles missing.
            total: raw.news2_score ?? null,
            risk: raw.news2_risk ?? null,
            scores: raw.news2_parameter_scores || {},
            missing: raw.news2_missing_vitals || [],
        },
        floorsApplied,
        red_flags: Array.isArray(raw.red_flags) ? raw.red_flags : [],
        decision_path: reasoningEn.join(' · ') || `python_engine → L${level}`,
        ai_used: false,
        engine_source: 'python_engine',
        engine_version: raw.extraction_method || 'backend',
        // Pass through the raw payload too — the handoff record can lean on
        // it (action_en/ar, recommended_action, icd10_code, etc.).
        raw,
        recommended_action: raw.recommended_action || raw.action_en || '',
        recommended_action_ar: raw.action_ar || '',
        time_to_physician: raw.time_to_physician || raw.time_en || '',
    };
}

/**
 * Try the backend deterministic engine; fall back to JS on failure.
 *
 * Returns `{ suggestion, source, error? }` where `source` mirrors
 * `suggestion.engine_source` for convenience.
 */
export async function getTriageSuggestion(input) {
    // App Store / Hospital Lite builds are intentionally self-contained. They
    // use the local deterministic fallback unless a developer explicitly sets
    // VITE_API_URL for a localhost backend demo.
    if (!API_URL) {
        return {
            suggestion: runOfflineFallbackTriage(input),
            source: 'offline_js_fallback',
            error: { kind: 'local_demo', message: 'Hospital Lite local-only mode' },
        };
    }

    // If we already know we're offline, skip the fetch round-trip.
    if (typeof navigator !== 'undefined' && navigator.onLine === false) {
        return {
            suggestion: runOfflineFallbackTriage(input),
            source: 'offline_js_fallback',
            error: { kind: 'offline', message: 'Browser reports offline' },
        };
    }

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), TRIAGE_TIMEOUT_MS);
    try {
        const res = await fetch(`${API_URL}/triage`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(toPatientInput(input)),
            signal: controller.signal,
        });
        clearTimeout(timer);
        if (!res.ok) {
            const text = await res.text().catch(() => '');
            throw Object.assign(new Error(`Backend ${res.status}`), {
                kind: 'http_error',
                status: res.status,
                body: text,
            });
        }
        const data = await res.json();
        return {
            suggestion: adaptBackendResult(data),
            source: 'python_engine',
        };
    } catch (err) {
        clearTimeout(timer);
        const kind =
            err.name === 'AbortError' ? 'timeout' :
            err.kind || (err.message?.includes('Failed to fetch') ? 'network' : 'unknown');
        return {
            suggestion: runOfflineFallbackTriage(input),
            source: 'offline_js_fallback',
            error: { kind, message: err.message || 'Backend unavailable' },
        };
    }
}

export const TRIAGE_API_URL = API_URL ? `${API_URL}/triage` : null;
