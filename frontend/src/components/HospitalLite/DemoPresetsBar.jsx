import React from 'react';
import { FlaskConical, HeartPulse, Wind, Baby, Bandage, Brain } from 'lucide-react';

/**
 * DemoPresetsBar — one-tap synthetic cases for hackathon / thesis demos.
 *
 * Each preset is a *partial* form patch (age, gender, complaint, vitals,
 * AVPU, pain, risk flags). The parent merges it into form state and the
 * clinician still has to press "Suggest triage" — the deterministic engine
 * is always in the decision path. Presets never write a final ESI level.
 *
 * Hard constraints:
 *   - Synthetic cases only — no real patient data.
 *   - Numbers chosen to exercise the engine's safety floors (hypoxia,
 *     altered mental status, pediatric tachycardia, etc.).
 *   - Patient ID / name intentionally left blank so each demo run is
 *     independent and the audit chain stays clean.
 */

const PRESETS = [
    {
        id: 'chest_pain_mi',
        icon: HeartPulse,
        label: { en: 'Chest pain · ?MI', ar: 'ألم صدر · ؟احتشاء' },
        sub:   { en: 'M, 58 y · crushing CP + sweating', ar: 'ذكر ٥٨ سنة · ألم ضاغط مع تعرق' },
        tone: 'red',
        fill: {
            age: '58', gender: 'male',
            chief_complaint_text:
                'Crushing central chest pain for 30 minutes, radiating to the left arm, with sweating and shortness of breath.',
            vitals: { hr: '108', rr: '22', sbp: '105', dbp: '70', spo2: '94', temp: '36.8' },
            consciousness: 'A', pain_scale: 9,
        },
    },
    {
        id: 'sob_hypoxia',
        icon: Wind,
        label: { en: 'SOB · low SpO₂', ar: 'ضيق نفس · أكسجين منخفض' },
        sub:   { en: 'F, 72 y · COPD · SpO₂ 86%', ar: 'أنثى ٧٢ سنة · انسداد رئوي · أكسجين ٨٦٪' },
        tone: 'red',
        fill: {
            age: '72', gender: 'female',
            chief_complaint_text:
                'Increasing shortness of breath over 2 days, productive cough, baseline COPD.',
            vitals: { hr: '118', rr: '28', sbp: '128', dbp: '78', spo2: '86', temp: '37.6' },
            consciousness: 'A', pain_scale: 3,
            is_copd: true,
        },
    },
    {
        id: 'fever_child',
        icon: Baby,
        label: { en: 'Fever in child', ar: 'حمى عند طفل' },
        sub:   { en: 'F, 4 y · T 39.4 °C · lethargic', ar: 'طفلة ٤ سنوات · ٣٩٫٤°م · خمول' },
        tone: 'orange',
        fill: {
            age: '4', gender: 'female',
            chief_complaint_text:
                'Fever for 2 days, mildly lethargic, drinking less, no rash, no neck stiffness.',
            vitals: { hr: '150', rr: '32', sbp: '95', dbp: '60', spo2: '97', temp: '39.4' },
            consciousness: 'A', pain_scale: 2,
        },
    },
    {
        id: 'minor_wound',
        icon: Bandage,
        label: { en: 'Minor wound · low risk', ar: 'جرح بسيط · خطر منخفض' },
        sub:   { en: 'M, 28 y · 3 cm forearm laceration', ar: 'ذكر ٢٨ سنة · جرح ٣ سم بالساعد' },
        tone: 'green',
        fill: {
            age: '28', gender: 'male',
            chief_complaint_text:
                '3 cm laceration on the left forearm from a kitchen knife, mild bleeding, otherwise well.',
            vitals: { hr: '78', rr: '14', sbp: '124', dbp: '78', spo2: '99', temp: '36.7' },
            consciousness: 'A', pain_scale: 3,
        },
    },
    {
        id: 'confused_elderly',
        icon: Brain,
        label: { en: 'Confused elderly', ar: 'مسن مشوش' },
        sub:   { en: 'M, 82 y · new AMS · ?sepsis', ar: 'ذكر ٨٢ سنة · تشوش جديد · ؟التهاب' },
        tone: 'orange',
        fill: {
            age: '82', gender: 'male',
            chief_complaint_text:
                'New confusion since this morning, urinary frequency, low appetite, no localising signs.',
            vitals: { hr: '112', rr: '24', sbp: '102', dbp: '64', spo2: '93', temp: '38.4' },
            consciousness: 'V', pain_scale: 4,
        },
    },
];

const TONE = {
    red:    'border-red-200 hover:border-red-300 hover:bg-red-50 text-red-700',
    orange: 'border-orange-200 hover:border-orange-300 hover:bg-orange-50 text-orange-700',
    green:  'border-green-200 hover:border-green-300 hover:bg-green-50 text-green-700',
};

export default function DemoPresetsBar({ lang, onLoadPreset }) {
    const heading = lang === 'ar'
        ? 'حالات تجريبية · للعرض فقط — لا تمثّل مرضى حقيقيين'
        : 'Demo presets · sample cases, not real patients';

    return (
        <section
            className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden"
            aria-label={heading}
        >
            <header className="px-4 py-2.5 border-b border-slate-100 bg-slate-50 flex items-center gap-2">
                <FlaskConical className="w-4 h-4 text-teal-700" aria-hidden="true" />
                <h3 className="text-[12.5px] font-bold text-slate-800">{heading}</h3>
            </header>
            <div className="p-3 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
                {PRESETS.map((p) => {
                    const Icon = p.icon;
                    return (
                        <button
                            type="button"
                            key={p.id}
                            onClick={() => onLoadPreset(p.fill)}
                            className={`text-start rounded-lg border bg-white px-3 py-2.5 transition-colors ${TONE[p.tone] || TONE.green}`}
                        >
                            <div className="flex items-center gap-2">
                                <Icon className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
                                <span className="text-[12.5px] font-semibold leading-tight">
                                    {lang === 'ar' ? p.label.ar : p.label.en}
                                </span>
                            </div>
                            <p className="mt-1 text-[11px] text-slate-500 leading-snug">
                                {lang === 'ar' ? p.sub.ar : p.sub.en}
                            </p>
                        </button>
                    );
                })}
            </div>
        </section>
    );
}
