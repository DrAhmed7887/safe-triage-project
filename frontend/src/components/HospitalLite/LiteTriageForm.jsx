import React, { useMemo, useState } from 'react';
import {
    User, Stethoscope, Activity, ShieldAlert, Sparkles, RefreshCw, Loader2,
} from 'lucide-react';
import { t } from '../../lib/i18n';
import { generatePatientId } from '../../lib/hospitalLite';
import DemoPresetsBar from './DemoPresetsBar';

const PAIN_OPTIONS = Array.from({ length: 11 }, (_, i) => i); // 0..10
const CONSCIOUSNESS_OPTIONS = [
    { value: 'A', en: 'Alert',        ar: 'يقظ' },
    { value: 'V', en: 'Voice',        ar: 'يستجيب للصوت' },
    { value: 'P', en: 'Pain',         ar: 'يستجيب للألم' },
    { value: 'U', en: 'Unresponsive', ar: 'لا يستجيب' },
];

const VITAL_FIELDS = [
    { key: 'hr',   tKey: 'hr',   type: 'number', step: '1',    min: 20, max: 250 },
    { key: 'rr',   tKey: 'rr',   type: 'number', step: '1',    min: 4,  max: 60 },
    { key: 'sbp',  tKey: 'sbp',  type: 'number', step: '1',    min: 50, max: 250 },
    { key: 'dbp',  tKey: 'dbp',  type: 'number', step: '1',    min: 20, max: 150 },
    { key: 'spo2', tKey: 'spo2', type: 'number', step: '1',    min: 50, max: 100 },
    { key: 'temp', tKey: 'temp', type: 'number', step: '0.1',  min: 30, max: 45 },
];

function Section({ icon: Icon, title, children }) {
    return (
        <section className="bg-white rounded-xl border border-slate-200 shadow-sm">
            <header className="px-4 py-3 border-b border-slate-100 bg-slate-50 flex items-center gap-2 rounded-t-xl">
                {Icon ? <Icon className="w-4 h-4 text-teal-600" aria-hidden="true" /> : null}
                <h3 className="text-[13.5px] font-bold text-slate-900">{title}</h3>
            </header>
            <div className="p-4 grid gap-3">{children}</div>
        </section>
    );
}

function Field({ label, children }) {
    return (
        <label className="block">
            <span className="block text-[12px] font-semibold text-slate-700 mb-1">{label}</span>
            {children}
        </label>
    );
}

const inputClass =
    'w-full px-3 py-2 rounded-lg border border-slate-300 focus:border-teal-500 focus:ring-2 focus:ring-teal-100 outline-none text-[15px] bg-white';

/**
 * LiteTriageForm — the streamlined Hospital Lite intake.
 *
 * Deliberately leaner than the demo TriageForm:
 *   - no voice input, no monitor integration, no Firebase token
 *   - clear required fields (chief complaint, vitals)
 *   - generate patient ID with one tap
 *   - mobile-first layout (single column on small screens)
 */
export default function LiteTriageForm({ lang, onSubmit, loading = false }) {
    const [form, setForm] = useState({
        patient_id: '',
        patient_name: '',
        age: '',
        gender: 'male',
        chief_complaint_text: '',
        vitals: { hr: '', rr: '', sbp: '', dbp: '', spo2: '', temp: '' },
        consciousness: 'A',
        pain_scale: 0,
        is_pregnant: false,
        is_copd: false,
        on_supplemental_o2: false,
        is_immunocompromised: false,
    });
    const [error, setError] = useState(null);

    const ageN = useMemo(() => Number.parseFloat(form.age), [form.age]);
    const isPregnancyEligible = form.gender === 'female' && !Number.isNaN(ageN) && ageN >= 12 && ageN <= 55;

    const update = (patch) => setForm((p) => ({ ...p, ...patch }));
    const updateVital = (k, v) => setForm((p) => ({ ...p, vitals: { ...p.vitals, [k]: v } }));

    // Demo-preset loader: shallow merge top-level fields + deep merge vitals.
    // Patient ID / name are intentionally NOT overwritten so each preset run
    // produces a fresh ID at submit time.
    const loadPreset = (preset) => {
        if (!preset) return;
        setForm((p) => ({
            ...p,
            ...preset,
            patient_id: p.patient_id,
            patient_name: p.patient_name,
            vitals: { ...p.vitals, ...(preset.vitals || {}) },
        }));
        setError(null);
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!form.chief_complaint_text.trim()) {
            setError(t('missing_complaint', lang));
            return;
        }
        if (!form.age) {
            setError(t('missing_age', lang));
            return;
        }
        setError(null);

        // Normalize vitals to numbers (or null) before passing on
        const cleanVitals = {};
        for (const k of Object.keys(form.vitals)) {
            const v = form.vitals[k];
            cleanVitals[k] = v === '' || v == null ? null : Number(v);
        }

        onSubmit({
            ...form,
            patient_id: form.patient_id || generatePatientId(),
            age: Number(form.age),
            pain_scale: Number(form.pain_scale) || 0,
            vitals: cleanVitals,
        });
    };

    return (
        <form className="grid gap-4" onSubmit={handleSubmit}>
            <DemoPresetsBar lang={lang} onLoadPreset={loadPreset} />

            <Section icon={User} title={t('section_patient', lang)}>
                <div className="grid sm:grid-cols-2 gap-3">
                    <Field label={t('patient_id', lang)}>
                        <div className="flex gap-2">
                            <input
                                type="text"
                                value={form.patient_id}
                                onChange={(e) => update({ patient_id: e.target.value })}
                                className={`${inputClass} font-mono`}
                                placeholder="HL-YYYYMMDD-0001"
                            />
                            <button
                                type="button"
                                onClick={() => update({ patient_id: generatePatientId() })}
                                className="px-2.5 py-2 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50 text-[12.5px] inline-flex items-center gap-1"
                            >
                                <RefreshCw className="w-3.5 h-3.5" aria-hidden="true" />
                                {t('generate_id', lang)}
                            </button>
                        </div>
                    </Field>
                    <Field label={t('patient_name', lang)}>
                        <input
                            type="text"
                            value={form.patient_name}
                            onChange={(e) => update({ patient_name: e.target.value })}
                            className={inputClass}
                            autoComplete="off"
                        />
                    </Field>
                    <Field label={t('age', lang)}>
                        <input
                            type="number"
                            inputMode="numeric"
                            min={0}
                            max={130}
                            value={form.age}
                            onChange={(e) => update({ age: e.target.value })}
                            className={inputClass}
                            required
                        />
                    </Field>
                    <Field label={t('gender', lang)}>
                        <div className="grid grid-cols-2 gap-2">
                            {['male', 'female'].map((g) => (
                                <button
                                    type="button"
                                    key={g}
                                    onClick={() => update({ gender: g })}
                                    aria-pressed={form.gender === g}
                                    className={`px-2 py-2 rounded-lg text-[12.5px] font-semibold border transition-colors ${
                                        form.gender === g
                                            ? 'bg-teal-600 border-teal-600 text-white'
                                            : 'bg-white border-slate-300 text-slate-700 hover:bg-slate-50'
                                    }`}
                                >
                                    {t(g, lang)}
                                </button>
                            ))}
                        </div>
                    </Field>
                </div>
            </Section>

            <Section icon={Stethoscope} title={t('section_complaint', lang)}>
                <textarea
                    rows={3}
                    value={form.chief_complaint_text}
                    onChange={(e) => update({ chief_complaint_text: e.target.value })}
                    className={`${inputClass} min-h-[88px] resize-y`}
                    placeholder={t('chief_complaint_ph', lang)}
                    required
                />
                <Field label={t('pain', lang)}>
                    <div className="flex items-center gap-3">
                        <input
                            type="range"
                            min={0}
                            max={10}
                            step={1}
                            value={form.pain_scale}
                            onChange={(e) => update({ pain_scale: Number(e.target.value) })}
                            className="flex-1"
                            aria-label={t('pain', lang)}
                        />
                        <select
                            value={form.pain_scale}
                            onChange={(e) => update({ pain_scale: Number(e.target.value) })}
                            className={`${inputClass} w-20`}
                            aria-label={t('pain', lang)}
                        >
                            {PAIN_OPTIONS.map((p) => (
                                <option key={p} value={p}>{p}</option>
                            ))}
                        </select>
                    </div>
                </Field>
            </Section>

            <Section icon={Activity} title={t('section_vitals', lang)}>
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                    {VITAL_FIELDS.map((f) => (
                        <Field key={f.key} label={t(f.tKey, lang)}>
                            <input
                                type={f.type}
                                inputMode="decimal"
                                step={f.step}
                                min={f.min}
                                max={f.max}
                                value={form.vitals[f.key]}
                                onChange={(e) => updateVital(f.key, e.target.value)}
                                className={inputClass}
                            />
                        </Field>
                    ))}
                </div>
                <Field label={t('consciousness', lang)}>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                        {CONSCIOUSNESS_OPTIONS.map((c) => (
                            <button
                                type="button"
                                key={c.value}
                                onClick={() => update({ consciousness: c.value })}
                                aria-pressed={form.consciousness === c.value}
                                className={`px-2 py-2 rounded-lg text-[12.5px] font-semibold border transition-colors ${
                                    form.consciousness === c.value
                                        ? 'bg-teal-600 border-teal-600 text-white'
                                        : 'bg-white border-slate-300 text-slate-700 hover:bg-slate-50'
                                }`}
                            >
                                <span className="font-mono mr-1">{c.value}</span>
                                <span>{lang === 'ar' ? c.ar : c.en}</span>
                            </button>
                        ))}
                    </div>
                </Field>
            </Section>

            <Section icon={ShieldAlert} title={t('section_risks', lang)}>
                <div className="grid sm:grid-cols-2 gap-2">
                    <Toggle
                        label={t('on_oxygen', lang)}
                        checked={form.on_supplemental_o2}
                        onChange={(v) => update({ on_supplemental_o2: v })}
                    />
                    <Toggle
                        label={t('is_copd', lang)}
                        checked={form.is_copd}
                        onChange={(v) => update({ is_copd: v })}
                    />
                    <Toggle
                        label={t('immunocompromised', lang)}
                        checked={form.is_immunocompromised}
                        onChange={(v) => update({ is_immunocompromised: v })}
                    />
                    {isPregnancyEligible && (
                        <Toggle
                            label={t('is_pregnant', lang)}
                            checked={form.is_pregnant}
                            onChange={(v) => update({ is_pregnant: v })}
                        />
                    )}
                </div>
            </Section>

            {error && (
                <div
                    role="alert"
                    className="bg-red-50 border border-red-200 text-red-800 rounded-lg px-3 py-2 text-[13px]"
                >
                    {error}
                </div>
            )}

            <button
                type="submit"
                disabled={loading}
                className="w-full sm:w-auto sm:self-end inline-flex items-center justify-center gap-2 bg-teal-600 hover:bg-teal-700 disabled:bg-slate-400 disabled:cursor-progress text-white rounded-xl px-5 py-3 text-[14.5px] font-semibold shadow-sm shadow-teal-600/20 transition-colors"
            >
                {loading ? (
                    <>
                        <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                        {t('running_triage', lang)}
                    </>
                ) : (
                    <>
                        <Sparkles className="w-4 h-4" aria-hidden="true" />
                        {t('run_triage', lang)}
                    </>
                )}
            </button>
        </form>
    );
}

function Toggle({ label, checked, onChange }) {
    return (
        <label className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-200 bg-white cursor-pointer hover:bg-slate-50 transition-colors">
            <input
                type="checkbox"
                checked={!!checked}
                onChange={(e) => onChange(e.target.checked)}
                className="w-4 h-4 rounded accent-teal-600"
            />
            <span className="text-[13px] text-slate-800">{label}</span>
        </label>
    );
}
