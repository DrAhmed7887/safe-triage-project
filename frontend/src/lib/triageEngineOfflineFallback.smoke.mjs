/**
 * Node smoke test for the offline-fallback JS engine.
 *
 * Run with:  node frontend/src/lib/triageEngineOfflineFallback.smoke.mjs
 *
 * Asserts a handful of safety-critical cases. NOT a full clinical
 * validation suite — the canonical engine is the Python one in
 * `backend/logic/triage_engine_v2.py`. The cross-engine *parity* harness
 * (parityFixtures.runner.mjs + backend/tests/test_triage_parity.py)
 * compares the two against a shared fixture file.
 */

import { runOfflineFallbackTriage } from './triageEngineOfflineFallback.js';
const runTriage = runOfflineFallbackTriage;

let pass = 0, fail = 0;
const cases = [];

function assertCase(name, input, expect) {
    const result = runTriage(input);
    let ok = true;
    const fails = [];

    if (expect.maxLevel != null && result.level > expect.maxLevel) {
        ok = false; fails.push(`level ${result.level} > maxLevel ${expect.maxLevel}`);
    }
    if (expect.minLevel != null && result.level < expect.minLevel) {
        ok = false; fails.push(`level ${result.level} < minLevel ${expect.minLevel}`);
    }
    if (expect.exactLevel != null && result.level !== expect.exactLevel) {
        ok = false; fails.push(`level ${result.level} !== ${expect.exactLevel}`);
    }
    if (expect.category != null && result.category !== expect.category) {
        ok = false; fails.push(`category ${result.category} !== ${expect.category}`);
    }
    if (expect.aiUsed === false && result.ai_used !== false) {
        ok = false; fails.push('ai_used should be false');
    }
    if (expect.floors) {
        for (const name of expect.floors) {
            if (!result.floorsApplied.find((f) => f.name === name)) {
                ok = false; fails.push(`missing floor ${name}`);
            }
        }
    }

    cases.push({ name, ok, fails, level: result.level, category: result.category });
    if (ok) pass++; else fail++;
}

// ---- Critical: cardiac arrest must be L1 ----
assertCase('Cardiac arrest, no pulse', {
    age: 60, gender: 'male',
    chief_complaint_text: 'cardiac arrest, no pulse',
    vitals: { hr: 0, rr: 0, sbp: 0, dbp: 0, spo2: 60, temp: 35 },
    consciousness: 'U',
}, { exactLevel: 1, category: 'cardiac_arrest', aiUsed: false, floors: ['unresponsive', 'critical_hypoxia'] });

// ---- Critical: unresponsive AVPU=U forces L1 even with mild complaint ----
assertCase('Unresponsive elderly', {
    age: 78, gender: 'female',
    chief_complaint_text: 'found unresponsive at home',
    vitals: { hr: 110, rr: 22, sbp: 100, dbp: 60, spo2: 92, temp: 36.5 },
    consciousness: 'U',
}, { exactLevel: 1, floors: ['unresponsive'] });

// ---- Arabic: ألم صدر → chest pain → L2 ----
assertCase('Arabic chest pain', {
    age: 55, gender: 'male',
    chief_complaint_text: 'ألم في الصدر منذ ساعة',
    vitals: { hr: 95, rr: 18, sbp: 140, dbp: 90, spo2: 96, temp: 37 },
    consciousness: 'A',
}, { exactLevel: 2, category: 'chest_pain_cardiac' });

// ---- Egyptian dialect respiratory arrest ----
assertCase('Arabic dialect: مش بيتنفس', {
    age: 70, gender: 'male',
    chief_complaint_text: 'الراجل مش بيتنفس',
    vitals: { hr: 50, rr: 4, sbp: 80, dbp: 50, spo2: 70, temp: 36 },
    consciousness: 'P',
}, { exactLevel: 1, category: 'respiratory_arrest' });

// ---- SpO2 < 88 must cap at L1 ----
assertCase('Severe hypoxia floor', {
    age: 40, gender: 'female',
    chief_complaint_text: 'feels dizzy',
    vitals: { hr: 95, rr: 22, sbp: 110, dbp: 70, spo2: 85, temp: 37 },
    consciousness: 'A',
}, { exactLevel: 1, floors: ['critical_hypoxia'] });

// ---- SBP 85 must cap at L2 ----
assertCase('Hypotension floor', {
    age: 65, gender: 'male',
    chief_complaint_text: 'feels weak',
    vitals: { hr: 105, rr: 20, sbp: 85, dbp: 55, spo2: 96, temp: 37 },
    consciousness: 'A',
}, { maxLevel: 2, floors: ['hypotension'] });

// ---- Severe pain modifier ----
assertCase('Severe abdominal pain', {
    age: 30, gender: 'female',
    chief_complaint_text: 'abdominal pain',
    vitals: { hr: 100, rr: 18, sbp: 120, dbp: 80, spo2: 98, temp: 37 },
    consciousness: 'A',
    pain_scale: 9,
}, { maxLevel: 2, floors: ['severe_pain'] });

// ---- Mild fever + normal vitals → L4 ----
assertCase('Mild fever', {
    age: 25, gender: 'male',
    chief_complaint_text: 'mild fever',
    vitals: { hr: 80, rr: 16, sbp: 120, dbp: 80, spo2: 99, temp: 37.8 },
    consciousness: 'A',
}, { exactLevel: 4, category: 'fever_simple' });

// ---- Medication refill → L5 ----
assertCase('Medication refill', {
    age: 50, gender: 'female',
    chief_complaint_text: 'prescription refill, no symptoms',
    vitals: { hr: 75, rr: 14, sbp: 125, dbp: 80, spo2: 98, temp: 36.8 },
    consciousness: 'A',
}, { exactLevel: 5, category: 'chronic_refill' });

// ---- Pregnant + bleeding ----
assertCase('Pregnant with bleeding', {
    age: 28, gender: 'female',
    chief_complaint_text: 'vaginal bleeding',
    vitals: { hr: 110, rr: 20, sbp: 100, dbp: 65, spo2: 97, temp: 37 },
    consciousness: 'A',
    is_pregnant: true,
}, { maxLevel: 2, floors: ['pregnancy_emergency'] });

// ---- AI must never be used in lite engine ----
assertCase('No AI flag', {
    age: 40, gender: 'male',
    chief_complaint_text: 'cough',
    vitals: { hr: 80, rr: 16, sbp: 120, dbp: 80, spo2: 98, temp: 37 },
    consciousness: 'A',
}, { aiUsed: false });

// ---- Pediatric tachycardia escalation ----
assertCase('Toddler fever + tachycardia', {
    age: 2, gender: 'male',
    chief_complaint_text: 'fever and vomiting',
    vitals: { hr: 170, rr: 32, sbp: 90, dbp: 55, spo2: 96, temp: 39.5 },
    consciousness: 'A',
}, { maxLevel: 2 });

for (const c of cases) {
    const mark = c.ok ? 'PASS' : 'FAIL';
    console.log(`[${mark}] ${c.name} — level=${c.level} cat=${c.category}`);
    if (!c.ok) for (const f of c.fails) console.log(`     · ${f}`);
}

console.log(`\n${pass} passed, ${fail} failed (${cases.length} total)`);
process.exit(fail === 0 ? 0 : 1);
