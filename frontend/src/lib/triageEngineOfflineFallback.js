/**
 * triageEngineOfflineFallback.js — DEGRADED-MODE FALLBACK ONLY.
 *
 * ⚠️  This is NOT the canonical SAFE-Triage engine. ⚠️
 *
 * The canonical engine lives in `backend/logic/triage_engine_v2.py` and its
 * companions, and is what the project benchmarks (MIETIC, MIETIC-Arabic,
 * KTAS, NHAMCS) validate against. This file is a best-effort *partial* port
 * used only when the browser cannot reach the backend (offline iPad, network
 * blip, backend unhealthy). It exists so the Hospital Lite triage desk keeps
 * working when the network is unavailable.
 *
 * Behavioural rules:
 *   • Hospital Lite tries `POST /triage` first (see `triageClient.js`).
 *   • This fallback runs ONLY when that call fails.
 *   • The suggestion carries `engine_source: 'offline_js_fallback'` and the
 *     UI must show an explicit "offline fallback" warning to the clinician.
 *   • A parity harness (`backend/tests/test_triage_parity.py` +
 *     `frontend/src/lib/parityFixtures.runner.mjs`) keeps this engine from
 *     producing *less acute* suggestions than the Python engine on a fixed
 *     set of critical cases. JS may over-triage; under-triaging vs Python
 *     is a parity failure.
 *
 * Implemented (subset of the Python canonical engine):
 *   1. NEWS2 scoring (RCP, 2017)
 *   2. Keyword-based symptom classification → ESI category
 *   3. A subset of ESI v5 critical safety floors
 *   4. Pediatric / elderly / pain / pregnancy modifiers
 *
 * AI is never used in this fallback. "AI Extracts → Rules Decide → Humans
 * Confirm" — this is the *Rules* layer, running in degraded mode.
 */

// ---------- ESI categories (subset mirrors SYMPTOM_CATEGORIES in Python) ----------

export const ESI_CATEGORIES = {
    // Level 1 — Resuscitation
    cardiac_arrest:           { level: 1, en: 'Cardiac arrest',                ar: 'توقف القلب' },
    respiratory_arrest:       { level: 1, en: 'Respiratory arrest',            ar: 'توقف التنفس' },
    unconscious_unresponsive: { level: 1, en: 'Unconscious / Unresponsive',    ar: 'فاقد الوعي / لا يستجيب' },
    active_seizure:           { level: 1, en: 'Active seizure',                ar: 'تشنجات نشطة' },
    severe_trauma:            { level: 1, en: 'Severe trauma',                 ar: 'إصابة شديدة / حادث خطير' },
    anaphylaxis:              { level: 1, en: 'Anaphylaxis',                   ar: 'صدمة حساسية' },
    poisoning_overdose:       { level: 1, en: 'Poisoning / Overdose',          ar: 'تسمم / جرعة زائدة' },
    choking_airway:           { level: 1, en: 'Choking / Airway obstruction',  ar: 'انسداد مجرى الهواء / شرقة' },

    // Level 2 — Emergent
    chest_pain_cardiac:       { level: 2, en: 'Cardiac chest pain',            ar: 'ألم صدر قلبي' },
    stroke_symptoms:          { level: 2, en: 'Stroke symptoms',               ar: 'أعراض جلطة دماغية' },
    respiratory_distress:     { level: 2, en: 'Severe respiratory distress',   ar: 'ضيق تنفس شديد' },
    severe_bleeding:          { level: 2, en: 'Severe bleeding',               ar: 'نزيف شديد' },
    altered_mental_status:    { level: 2, en: 'Altered mental status',         ar: 'تغير في الوعي' },
    psychiatric_emergency:    { level: 2, en: 'Psychiatric emergency',         ar: 'حالة نفسية طارئة' },
    obstetric_emergency:      { level: 2, en: 'Obstetric emergency',           ar: 'طوارئ حمل / نزيف مهبلي' },
    severe_pain:              { level: 2, en: 'Severe pain (≥ 8/10)',          ar: 'ألم شديد جداً (≥ 8/10)' },
    diabetic_emergency:       { level: 2, en: 'Diabetic emergency',            ar: 'طوارئ سكر' },

    // Level 3 — Urgent
    abdominal_pain_moderate:  { level: 3, en: 'Moderate abdominal pain',       ar: 'ألم بطن متوسط' },
    moderate_trauma:          { level: 3, en: 'Moderate trauma',               ar: 'إصابة متوسطة' },
    headache_severe:          { level: 3, en: 'Severe headache',               ar: 'صداع شديد' },
    fever_with_symptoms:      { level: 3, en: 'Fever with other symptoms',     ar: 'سخونية مع أعراض أخرى' },
    vomiting_diarrhea_dehydration: { level: 3, en: 'Vomiting / Diarrhea with dehydration', ar: 'قيء/إسهال مع جفاف' },
    urinary_symptoms_severe:  { level: 3, en: 'Severe urinary symptoms',       ar: 'أعراض بولية شديدة' },
    pediatric_moderate:       { level: 3, en: 'Pediatric — urgent evaluation', ar: 'طفل يحتاج تقييم عاجل' },

    // Level 4 — Less Urgent
    minor_trauma:             { level: 4, en: 'Minor trauma',                  ar: 'إصابة بسيطة' },
    fever_simple:             { level: 4, en: 'Simple fever',                  ar: 'سخونية بسيطة' },
    mild_pain:                { level: 4, en: 'Mild pain',                     ar: 'ألم خفيف' },
    skin_rash_stable:         { level: 4, en: 'Stable skin rash',              ar: 'طفح جلدي مستقر' },
    minor_bleeding:           { level: 4, en: 'Minor bleeding / laceration',   ar: 'نزيف بسيط / جرح' },
    cold_flu_symptoms:        { level: 4, en: 'Cold / Flu symptoms',           ar: 'أعراض برد/إنفلونزا' },
    ear_eye_throat:           { level: 4, en: 'Ear / Eye / Throat',            ar: 'مشاكل أذن/عين/حلق' },

    // Level 5 — Non-urgent
    chronic_refill:           { level: 5, en: 'Chronic medication refill',     ar: 'تجديد علاج مزمن' },
    minor_complaint:          { level: 5, en: 'Minor complaint',               ar: 'شكوى بسيطة' },
    medical_certificate:      { level: 5, en: 'Medical certificate',           ar: 'شهادة طبية' },

    // Fallback
    unclear_needs_evaluation: { level: 3, en: 'Needs medical evaluation',      ar: 'يحتاج تقييم طبي' },
};

export const LEVEL_LABELS = {
    1: { en: 'Resuscitation',  ar: 'إنعاش',     color: '#ef4444', tone: 'red' },
    2: { en: 'Emergent',       ar: 'طارئ',      color: '#f97316', tone: 'orange' },
    3: { en: 'Urgent',         ar: 'عاجل',      color: '#eab308', tone: 'yellow' },
    4: { en: 'Less Urgent',    ar: 'أقل إلحاحاً', color: '#22c55e', tone: 'green' },
    5: { en: 'Non-urgent',     ar: 'غير عاجل',  color: '#3b82f6', tone: 'blue' },
};

// ---------- Keyword → category mapping (EN + Arabic, including Egyptian dialect) ----------

// Order matters: most-specific & most-acute first. Each entry's keywords are
// lowercase-matched against the chief complaint.
const KEYWORD_RULES = [
    // ----- Level 1 -----
    { cat: 'cardiac_arrest',          kw: ['cardiac arrest', 'no pulse', 'no heartbeat', 'pulseless', 'توقف القلب', 'مفيش نبض'] },
    { cat: 'respiratory_arrest',      kw: ['respiratory arrest', 'not breathing', 'stopped breathing', 'apnea', 'توقف التنفس', 'مش بيتنفس', 'بطل يتنفس'] },
    { cat: 'choking_airway',          kw: ['choking', 'airway obstruction', 'can\'t breathe', 'cannot breathe', 'شرقة', 'انسداد مجرى الهواء'] },
    { cat: 'unconscious_unresponsive',kw: ['unconscious', 'unresponsive', 'not responding', 'فاقد الوعي', 'مش بيرد', 'مغمى عليه'] },
    { cat: 'active_seizure',          kw: ['active seizure', 'seizing', 'convulsion', 'تشنج', 'صرع', 'تشنجات'] },
    { cat: 'anaphylaxis',             kw: ['anaphylaxis', 'anaphylactic', 'صدمة حساسية', 'حساسية شديدة'] },
    { cat: 'severe_trauma',           kw: ['severe trauma', 'multiple trauma', 'major trauma', 'gunshot', 'stab wound', 'high speed', 'إصابة شديدة', 'حادث خطير', 'طلق ناري'] },
    { cat: 'poisoning_overdose',      kw: ['overdose', 'poisoning', 'ingested poison', 'تسمم', 'جرعة زائدة'] },

    // ----- Level 2 -----
    { cat: 'chest_pain_cardiac',      kw: ['chest pain', 'crushing chest', 'cardiac chest', 'left arm pain radiating', 'ألم صدر', 'ألم في الصدر', 'ألم شديد في الصدر', 'وجع في الصدر', 'ضغط في الصدر', 'ضيق في الصدر', 'في الصدر'] },
    { cat: 'stroke_symptoms',         kw: ['stroke', 'facial droop', 'slurred speech', 'one sided weakness', 'hemiparesis', 'fast positive', 'جلطة', 'سكتة دماغية', 'لخبطة في الكلام', 'ضعف نصفي'] },
    { cat: 'respiratory_distress',    kw: ['shortness of breath', 'severe sob', 'gasping', 'using accessory muscles', 'ضيق تنفس شديد', 'مش قادر يتنفس'] },
    { cat: 'severe_bleeding',         kw: ['heavy bleeding', 'massive bleeding', 'hemorrhage', 'spurting blood', 'نزيف شديد', 'نزيف كتير'] },
    // AMS keyword list kept in lockstep with the Python canonical engine
    // (see backend/logic/deterministic_triage.py — `_text_has_altered_mental_status_signal`
    // and the glucose-recommend AMS tokens). Adding 'confusion' / 'new confusion'
    // / 'تشوش' closes a JS-only gap Codex flagged in the Phase-1 QA review
    // (confused-elderly preset previously fell through to unclear_needs_evaluation).
    { cat: 'altered_mental_status',   kw: ['confused', 'confusion', 'new confusion', 'altered mental', 'altered mental status', 'altered mentality', 'disoriented', 'lethargic', 'تغير في الوعي', 'تغير الوعي', 'تشوش', 'مش فاهم', 'هياج'] },
    { cat: 'psychiatric_emergency',   kw: ['suicidal', 'suicide', 'self harm', 'violent', 'أفكار انتحارية', 'انتحار', 'إيذاء نفسه'] },
    { cat: 'obstetric_emergency',     kw: ['vaginal bleeding', 'labor', 'pregnant bleeding', 'placental', 'ruptured membranes', 'نزيف حمل', 'طلق', 'مية الجنين نزلت'] },
    { cat: 'diabetic_emergency',      kw: ['hypoglycemia', 'hyperglycemia', 'dka', 'diabetic ketoacidosis', 'هبوط سكر', 'ارتفاع سكر شديد'] },

    // ----- Level 3 -----
    { cat: 'abdominal_pain_moderate', kw: ['abdominal pain', 'belly pain', 'stomach pain', 'ألم بطن', 'وجع بطن', 'مغص'] },
    { cat: 'headache_severe',         kw: ['severe headache', 'worst headache', 'thunderclap headache', 'صداع شديد', 'صداع نصفي شديد'] },
    { cat: 'fever_with_symptoms',     kw: ['fever and', 'fever with', 'high fever', 'سخونية عالية', 'حرارة عالية'] },
    { cat: 'vomiting_diarrhea_dehydration', kw: ['vomiting and diarrhea', 'dehydration', 'severe diarrhea', 'قيء وإسهال', 'جفاف'] },
    { cat: 'urinary_symptoms_severe', kw: ['dysuria with fever', 'urinary retention', 'hematuria', 'دم في البول', 'حصر بول'] },
    { cat: 'moderate_trauma',         kw: ['fracture', 'broken bone', 'dislocation', 'كسر', 'خلع'] },

    // ----- Level 4 -----
    { cat: 'minor_bleeding',          kw: ['laceration', 'small cut', 'minor cut', 'wound', 'جرح بسيط', 'قطع'] },
    { cat: 'fever_simple',            kw: ['mild fever', 'low grade fever', 'سخونية خفيفة'] },
    { cat: 'cold_flu_symptoms',       kw: ['cough', 'cold', 'flu', 'sore throat', 'runny nose', 'برد', 'كحة', 'رشح', 'احتقان حلق'] },
    { cat: 'ear_eye_throat',          kw: ['earache', 'eye pain', 'red eye', 'وجع ودن', 'وجع عين'] },
    { cat: 'mild_pain',               kw: ['mild pain', 'ألم بسيط'] },
    { cat: 'skin_rash_stable',        kw: ['rash', 'skin rash', 'hives stable', 'طفح جلدي', 'حساسية جلد'] },
    { cat: 'minor_trauma',            kw: ['sprain', 'twisted ankle', 'bruise', 'كدمة', 'التواء'] },

    // ----- Level 5 -----
    { cat: 'chronic_refill',          kw: ['medication refill', 'prescription refill', 'تجديد علاج', 'تجديد روشتة'] },
    { cat: 'medical_certificate',     kw: ['medical certificate', 'sick note', 'تقرير طبي', 'شهادة مرضية'] },
];

function normalizeText(s) {
    return (s || '').toString().toLowerCase().trim();
}

/**
 * Arabic hamza-bearing alif normalization — أ / إ / آ → ا.  Mirrors the
 * canonical Python engine (`backend/logic/deterministic_triage.py`)
 * which collapses these characters before pair-matching.  Keeping the
 * two engines aligned on normalization is what lets the pair-check
 * below recognise the same Arabic pain × chest co-occurrences the
 * Python engine recognises.
 */
function normalizeArabic(s) {
    return (s || '').replace(/[أإآ]/g, 'ا');
}

/**
 * Mirrors the Python canonical engine's pain ⊕ chest co-occurrence
 * check (see _AR_PAIN_TERMS / _AR_CHEST_TERMS in
 * `backend/logic/deterministic_triage.py`).  Any Arabic pain-word
 * together with any Arabic chest-word — in any order, with any
 * modifier between them, including possessive forms (صدري / صدره /
 * صدرها) — routes to `chest_pain_cardiac`.  Without this the JS
 * fallback would silently under-triage cases like "ألم في صدري"
 * relative to the Python engine.
 */
const _AR_PAIN_TERMS = [
    'الم',      // ألم / الم after hamza-alif normalization
    'وجع',
    'اوجاع',
    'اوجع',
    'حرقان',
    'ضغط',
    'ضيق',
    'ضيقة',
    'نغزة',
    'حارق',
];
const _AR_CHEST_TERMS = [
    'في الصدر',
    'بالصدر',
    'على الصدر',
    'في صدري',
    'في صدره',
    'في صدرها',
    'بصدري',
    'صدري',
];

function hasArabicChestPainPair(normalized) {
    if (!normalized) return false;
    const hasPain  = _AR_PAIN_TERMS.some((p) => normalized.includes(p));
    const hasChest = _AR_CHEST_TERMS.some((c) => normalized.includes(c));
    return hasPain && hasChest;
}

export function classifyComplaint(complaint) {
    const text = normalizeText(complaint);
    if (!text) return { category: 'unclear_needs_evaluation', confidence: 'low', matched: null };
    const normalized = normalizeArabic(text);
    for (const rule of KEYWORD_RULES) {
        for (const kw of rule.kw) {
            // Match against both the raw lowercase form and the
            // hamza-collapsed form so keywords written with either
            // ألم or الم catch correctly.
            if (text.includes(kw) || normalized.includes(normalizeArabic(kw))) {
                return { category: rule.cat, confidence: 'medium', matched: kw };
            }
        }
        // Synthetic Arabic pair-check at the chest_pain_cardiac slot.
        // Runs only after every L1 rule has been considered (since L1
        // rules precede chest_pain_cardiac in KEYWORD_RULES) and only
        // when no L1 keyword fired — guaranteeing the more-acute L1
        // categories still win when a complaint contains both.
        if (rule.cat === 'chest_pain_cardiac' && hasArabicChestPainPair(normalized)) {
            return {
                category: 'chest_pain_cardiac',
                confidence: 'medium',
                matched: 'ar_pain_chest_pair',
            };
        }
    }
    return { category: 'unclear_needs_evaluation', confidence: 'low', matched: null };
}

// ---------- NEWS2 ----------

function asInt(v)   { const n = Number.parseFloat(v); return Number.isFinite(n) ? Math.round(n) : null; }
function asFloat(v) { const n = Number.parseFloat(v); return Number.isFinite(n) ? n : null; }

function scoreRR(rr) {
    if (rr == null) return { score: 0, missing: 'rr' };
    if (rr <= 8)  return { score: 3 };
    if (rr <= 11) return { score: 1 };
    if (rr <= 20) return { score: 0 };
    if (rr <= 24) return { score: 2 };
    return { score: 3 };
}
function scoreSpo2(spo2, isCopd) {
    if (spo2 == null) return { score: 0, missing: 'spo2' };
    if (isCopd) {
        // Scale 2 (target 88–92%)
        if (spo2 <= 83)  return { score: 3 };
        if (spo2 <= 85)  return { score: 2 };
        if (spo2 <= 87)  return { score: 1 };
        if (spo2 <= 92)  return { score: 0 };
        if (spo2 <= 94)  return { score: 1 };
        if (spo2 <= 96)  return { score: 2 };
        return { score: 3 };
    }
    if (spo2 <= 91) return { score: 3 };
    if (spo2 <= 93) return { score: 2 };
    if (spo2 <= 95) return { score: 1 };
    return { score: 0 };
}
function scoreSbp(sbp) {
    if (sbp == null) return { score: 0, missing: 'sbp' };
    if (sbp <= 90)  return { score: 3 };
    if (sbp <= 100) return { score: 2 };
    if (sbp <= 110) return { score: 1 };
    if (sbp <= 219) return { score: 0 };
    return { score: 3 };
}
function scoreHr(hr) {
    if (hr == null) return { score: 0, missing: 'hr' };
    if (hr <= 40)  return { score: 3 };
    if (hr <= 50)  return { score: 1 };
    if (hr <= 90)  return { score: 0 };
    if (hr <= 110) return { score: 1 };
    if (hr <= 130) return { score: 2 };
    return { score: 3 };
}
function scoreConsciousness(avpu) {
    if (!avpu) return { score: 0, missing: 'consciousness' };
    return avpu.toUpperCase() === 'A' ? { score: 0 } : { score: 3 };
}
function scoreTemp(t) {
    if (t == null) return { score: 0, missing: 'temp' };
    if (t <= 35.0) return { score: 3 };
    if (t <= 36.0) return { score: 1 };
    if (t <= 38.0) return { score: 0 };
    if (t <= 39.0) return { score: 1 };
    return { score: 2 };
}

export function calculateNews2(vitals, options = {}) {
    const v = vitals || {};
    const rr  = asInt(v.rr);
    const spo2 = asInt(v.spo2);
    const sbp = asInt(v.sbp);
    const hr  = asInt(v.hr);
    const temp = asFloat(v.temp);
    const avpu = v.avpu || v.consciousness || null;
    const onOxygen = Boolean(v.on_oxygen || options.on_supplemental_o2);

    const scores = {};
    const missing = [];
    const push = (key, r) => { scores[key] = r.score; if (r.missing) missing.push(r.missing); };

    push('rr',   scoreRR(rr));
    push('spo2', scoreSpo2(spo2, Boolean(options.is_copd)));
    scores.supplemental_o2 = onOxygen ? 2 : 0;
    push('sbp',  scoreSbp(sbp));
    push('hr',   scoreHr(hr));
    push('consciousness', scoreConsciousness(avpu));
    push('temp', scoreTemp(temp));

    const total = Object.values(scores).reduce((a, b) => a + b, 0);
    const hasExtreme = Object.values(scores).some((s) => s === 3);
    // NEWS2 risk banding mirrors the Royal College of Physicians escalation:
    //   - Any single parameter scoring 3 → HIGH risk (covered by `hasExtreme`).
    //   - Aggregate total 7+ → HIGH risk.
    //   - Aggregate total 5-6 → MEDIUM risk.
    //   - Anything else → LOW risk.
    let risk;
    if (total >= 7 || hasExtreme) risk = 'HIGH';
    else if (total >= 5)          risk = 'MEDIUM';
    else                          risk = 'LOW';

    return { total, risk, scores, missing };
}

// ---------- Engine ----------

/**
 * NEWS2 → triage *escalation* level. Returns the worst-case ESI level that
 * NEWS2 alone should force, or `null` if NEWS2 is fine and the category
 * should decide on its own (so a true L5 patient stays L5).
 */
function news2EscalationLevel(risk) {
    if (risk === 'HIGH')   return 2;
    if (risk === 'MEDIUM' || risk === 'LOW_MEDIUM') return 3;
    return null;
}

function applyModifiers(level, category, age, news2, painScale) {
    let out = level;
    // Pediatric (< 5 years). Cardiopulmonary instability in young children
    // deteriorates fast — match the Python canonical engine's tendency to
    // floor these at L1 when multiple NEWS2 parameters are critical.
    if (age != null && age < 5) {
        const criticalParams = Object.values(news2.scores).filter((s) => s === 3).length;
        if (news2.risk === 'HIGH' && criticalParams >= 2) {
            out = Math.min(out, 1);
        } else if (news2.total >= 3) {
            out = Math.min(out, 2);
        }
        if (['fever_simple', 'vomiting_diarrhea_dehydration'].includes(category)) {
            out = Math.min(out, 3);
        }
    }
    // Elderly (≥ 65) with abnormal vitals
    if (age != null && age >= 65 && news2.total >= 5) {
        out = Math.min(out, 2);
    }
    // Severe pain modifier
    if (painScale != null && painScale >= 8) {
        out = Math.min(out, 2);
    }
    return out;
}

/**
 * Critical safety floors — drawn from ESI v5 (AHRQ) + the existing
 * `apply_critical_safety_rules` logic. A floor *caps* the triage level
 * (i.e. it can only make the patient *more* acute, never less).
 *
 * Returns { level, floorsApplied: [{ name, level, reason_en, reason_ar }] }.
 */
function applyCriticalSafetyFloors(level, { vitals, consciousness, painScale, isPregnant, complaint }) {
    const floors = [];
    // A floor records the *clinical reason* the patient cannot be below
    // `target` — recorded even when the level is already there, so the audit
    // trail reflects the constraint. The level itself is clamped via min.
    const cap = (cur, target, name, reason_en, reason_ar) => {
        floors.push({ name, level: target, reason_en, reason_ar });
        return Math.min(cur, target);
    };
    let out = level;

    const spo2 = asInt(vitals?.spo2);
    const rr   = asInt(vitals?.rr);
    const sbp  = asInt(vitals?.sbp);
    const hr   = asInt(vitals?.hr);
    const temp = asFloat(vitals?.temp);
    const conscious = (consciousness || vitals?.consciousness || 'A').toUpperCase();

    if (conscious === 'U' || conscious === 'P') {
        out = cap(out, 1, 'unresponsive', 'Unresponsive / responds only to pain', 'فاقد الوعي / يستجيب للألم فقط');
    } else if (conscious === 'V') {
        out = cap(out, 2, 'responds_to_voice_only', 'Responds to voice only', 'يستجيب للصوت فقط');
    }

    if (spo2 != null && spo2 < 88) out = cap(out, 1, 'critical_hypoxia', `Severe hypoxia (SpO₂ ${spo2}%)`, `نقص أكسجين شديد (${spo2}٪)`);
    else if (spo2 != null && spo2 < 92) out = cap(out, 2, 'hypoxia', `Low oxygen (SpO₂ ${spo2}%)`, `أكسجين منخفض (${spo2}٪)`);

    if (rr != null && (rr <= 8 || rr >= 30)) out = cap(out, 2, 'critical_respiratory_rate', `Abnormal RR (${rr}/min)`, `معدل تنفس غير طبيعي (${rr}/د)`);

    if (sbp != null && sbp <= 90) out = cap(out, 2, 'hypotension', `Hypotension (SBP ${sbp})`, `هبوط ضغط (${sbp})`);
    if (sbp != null && sbp >= 220) out = cap(out, 2, 'hypertensive_crisis', `Hypertensive crisis (SBP ${sbp})`, `أزمة ارتفاع ضغط (${sbp})`);

    if (hr != null && (hr <= 40 || hr >= 131)) out = cap(out, 2, 'critical_heart_rate', `Abnormal HR (${hr})`, `نبض غير طبيعي (${hr})`);

    if (temp != null && temp >= 40) out = cap(out, 2, 'hyperthermia', `Hyperthermia (${temp}°C)`, `حرارة شديدة (${temp}°C)`);
    if (temp != null && temp <= 35) out = cap(out, 2, 'hypothermia', `Hypothermia (${temp}°C)`, `هبوط حرارة (${temp}°C)`);

    // Fever + tachycardia sepsis pathway — mirrors the canonical Python
    // engine (`backend/logic/deterministic_triage.py`, "Fever + tachycardia
    // (sepsis pathway)" block).  When the complaint mentions fever (EN/AR)
    // *or* the measured temperature is ≥ 38.0 °C, AND the heart rate is
    // > 100, the patient cannot drop below ESI 2.  Without this floor the
    // JS fallback under-triaged febrile-tachycardic adults relative to
    // Python (e.g. "fever and chills", HR 105, T 38.2 → L3 in JS vs L2 in
    // Python).
    {
        const normalizedComplaint = normalizeText(complaint);
        const fevTerms = ['fever', 'سخونية', 'سخونة', 'حمى'];
        const complaintHasFever = fevTerms.some((t) => normalizedComplaint.includes(t));
        const tempElevated = temp != null && temp >= 38.0;
        const hrTachy = hr != null && hr > 100;
        if ((complaintHasFever || tempElevated) && hrTachy) {
            const tempLabel = temp != null ? `${temp}°C` : 'N/A';
            out = cap(
                out,
                2,
                'sepsis_fever_tachycardia',
                `Fever + tachycardia (temp=${tempLabel}, HR=${hr}) — sepsis pathway`,
                `حمى مع تسارع القلب (الحرارة=${tempLabel}، النبض=${hr}) — مسار تعفن`,
            );
        }
    }

    if (painScale != null && painScale >= 8) {
        out = cap(out, 2, 'severe_pain', `Severe pain (${painScale}/10)`, `ألم شديد (${painScale}/10)`);
    }

    if (isPregnant) {
        const text = normalizeText(complaint);
        if (text.includes('bleeding') || text.includes('نزيف') || text.includes('labor') || text.includes('طلق')) {
            out = cap(out, 2, 'pregnancy_emergency', 'Pregnant patient with bleeding or labor', 'حامل مع نزيف أو طلق');
        }
    }

    return { level: out, floorsApplied: floors };
}

function buildRedFlags(category, news2, vitals, consciousness) {
    const flags = [];
    const conscious = (consciousness || vitals?.consciousness || 'A').toUpperCase();
    if (conscious !== 'A') flags.push(conscious === 'U' || conscious === 'P' ? 'unresponsive' : 'voice-only');
    if (asInt(vitals?.spo2) != null && vitals.spo2 < 92) flags.push('hypoxia');
    if (asInt(vitals?.sbp) != null && vitals.sbp <= 90) flags.push('hypotension');
    if (asInt(vitals?.hr)  != null && (vitals.hr <= 40 || vitals.hr >= 131)) flags.push('abnormal_hr');
    if (asInt(vitals?.rr)  != null && (vitals.rr <= 8 || vitals.rr >= 30)) flags.push('abnormal_rr');
    if (ESI_CATEGORIES[category] && ESI_CATEGORIES[category].level <= 2) flags.push(category);
    if (news2.total >= 7) flags.push('news2_high');
    return [...new Set(flags)];
}

/**
 * Main entry. Returns a stable triage suggestion plus everything the UI
 * needs to render bilingual output and the audit trail.
 *
 * Use this ONLY as a fallback for the backend `/triage` endpoint. The
 * returned shape carries `engine_source: 'offline_js_fallback'` so the UI
 * and audit trail can clearly mark which engine produced the suggestion.
 */
export function runOfflineFallbackTriage(input) {
    // gender is intentionally not destructured: ESI v5 / NEWS2 do not use
    // gender as a triage discriminator. The Python canonical engine also
    // ignores it on the decision path. Pregnancy is captured separately via
    // `is_pregnant` because it is a clinical state, not a gender field.
    const {
        age, chief_complaint_text,
        vitals = {}, consciousness = 'A',
        pain_scale = null, is_pregnant = false,
        is_copd = false, on_supplemental_o2 = false,
    } = input || {};

    const news2 = calculateNews2(
        { ...vitals, avpu: consciousness },
        { is_copd, on_supplemental_o2 },
    );

    const cls = classifyComplaint(chief_complaint_text);
    const cat = ESI_CATEGORIES[cls.category] || ESI_CATEGORIES.unclear_needs_evaluation;

    // Category is primary; NEWS2 only escalates when it indicates risk so a
    // truly low-acuity case (e.g. medication refill, all vitals normal) can
    // legitimately end up at L5.
    const news2Escalation = news2EscalationLevel(news2.risk);
    const baseLevel = news2Escalation != null
        ? Math.min(news2Escalation, cat.level)
        : cat.level;

    const ageN = asFloat(age);
    const modified = applyModifiers(baseLevel, cls.category, ageN, news2, pain_scale);

    const { level: finalLevel, floorsApplied } = applyCriticalSafetyFloors(modified, {
        vitals, consciousness, painScale: pain_scale, isPregnant: is_pregnant, complaint: chief_complaint_text,
    });

    const decisionPath = floorsApplied.length
        ? `news2=${news2.total}/${news2.risk} → cat=${cls.category}(L${cat.level}) → base=L${baseLevel} → mod=L${modified} → floors[${floorsApplied.map(f => f.name).join(',')}] → L${finalLevel}`
        : `news2=${news2.total}/${news2.risk} → cat=${cls.category}(L${cat.level}) → base=L${baseLevel} → mod=L${modified} → L${finalLevel}`;

    const redFlags = buildRedFlags(cls.category, news2, vitals, consciousness);

    return {
        level: finalLevel,
        level_label: LEVEL_LABELS[finalLevel],
        category: cls.category,
        category_label: cat,
        category_confidence: cls.confidence,
        news2,
        floorsApplied,
        red_flags: redFlags,
        decision_path: decisionPath,
        ai_used: false,
        engine_source: 'offline_js_fallback',
        engine_version: '1.0.0',
    };
}
