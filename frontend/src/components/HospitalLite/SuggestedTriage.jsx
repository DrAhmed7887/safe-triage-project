import React, { useState } from 'react';
import { ShieldCheck, AlertTriangle, Pencil, CheckCircle2 } from 'lucide-react';
import { LEVEL_LABELS } from '../../lib/triageEngineOfflineFallback';
import { t } from '../../lib/i18n';
import EngineSourceBadge from './EngineSourceBadge';

const tone = {
    red:    { ring: 'ring-red-200', bg: 'bg-red-50',    text: 'text-red-700',    bar: 'bg-red-500' },
    orange: { ring: 'ring-orange-200', bg: 'bg-orange-50', text: 'text-orange-700', bar: 'bg-orange-500' },
    yellow: { ring: 'ring-yellow-200', bg: 'bg-yellow-50', text: 'text-yellow-800', bar: 'bg-yellow-400' },
    green:  { ring: 'ring-green-200', bg: 'bg-green-50',  text: 'text-green-700',  bar: 'bg-green-500' },
    blue:   { ring: 'ring-blue-200', bg: 'bg-blue-50',   text: 'text-blue-700',   bar: 'bg-blue-500' },
};

/**
 * SuggestedTriage — renders the engine's suggestion and exposes the
 * mandatory clinician confirmation step.
 *
 * Confirmation flow:
 *   1. Engine suggests a level.
 *   2. Clinician must either CONFIRM the suggestion or OVERRIDE it.
 *   3. Override requires a free-text reason — enforced at submit time.
 *
 * The component intentionally does no networking. The parent decides
 * what to do with the decision (write to the queue + audit + advance).
 */
export default function SuggestedTriage({ lang, suggestion, engineError, onDecision }) {
    const [overriding, setOverriding] = useState(false);
    const [newLevel, setNewLevel] = useState(suggestion?.level || 3);
    const [reason, setReason] = useState('');

    if (!suggestion) return null;

    const label = suggestion.level_label || LEVEL_LABELS[suggestion.level];
    const toneCfg = tone[label?.tone] || tone.yellow;

    const submitConfirm = () => {
        onDecision({
            action: 'confirmed',
            final_level: suggestion.level,
            reason: null,
        });
    };

    const submitOverride = (e) => {
        e.preventDefault();
        const r = reason.trim();
        if (!r) return;
        onDecision({
            action: 'overridden',
            final_level: Number(newLevel),
            reason: r,
        });
    };

    return (
        <div className={`bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden ring-1 ${toneCfg.ring}`}>
            {/* Headline level */}
            <div className={`${toneCfg.bg} px-4 sm:px-6 py-4 flex items-center gap-4`}>
                <div
                    className={`w-14 h-14 rounded-2xl ${toneCfg.bar} text-white inline-flex items-center justify-center text-3xl font-extrabold shadow-sm`}
                    aria-label={`ESI level ${suggestion.level}`}
                >
                    {suggestion.level}
                </div>
                <div className="flex-1 min-w-0">
                    <p className="text-[12px] uppercase tracking-wider text-slate-600 font-semibold">
                        {t('suggested_triage', lang)}
                    </p>
                    <p className={`text-xl sm:text-2xl font-extrabold ${toneCfg.text} leading-tight`}>
                        {lang === 'ar' ? label?.ar : label?.en}
                    </p>
                    <p className="text-[12px] text-slate-500 mt-0.5 font-mono break-all">
                        {suggestion.category_label
                            ? (lang === 'ar' ? suggestion.category_label.ar : suggestion.category_label.en)
                            : suggestion.category}
                    </p>
                </div>
            </div>

            <div className="px-4 sm:px-6 py-4 grid gap-3">
                <EngineSourceBadge
                    lang={lang}
                    source={suggestion.engine_source}
                    error={engineError}
                    variant="banner"
                />
                <div className="text-[12px] text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 inline-flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
                    <span>{t('decision_support', lang)}</span>
                </div>

                {/* Rules / red flags */}
                <div className="grid sm:grid-cols-2 gap-3">
                    <Card title={t('rules_used', lang)}>
                        <ul className="text-[12.5px] text-slate-700 space-y-1 leading-snug">
                            <li className="font-mono">NEWS2 = {suggestion.news2?.total} ({suggestion.news2?.risk})</li>
                            <li className="font-mono break-all">{suggestion.decision_path}</li>
                            {suggestion.news2?.missing?.length > 0 && (
                                <li className="text-amber-700">⚠ {t('missing_vitals_note', lang)}</li>
                            )}
                        </ul>
                    </Card>
                    <Card title={t('red_flags', lang)}>
                        {suggestion.red_flags?.length ? (
                            <div className="flex flex-wrap gap-1.5">
                                {suggestion.red_flags.map((f) => (
                                    <span
                                        key={f}
                                        className="text-[11px] font-semibold bg-red-50 text-red-700 border border-red-200 rounded-full px-2 py-0.5"
                                    >
                                        {f}
                                    </span>
                                ))}
                            </div>
                        ) : (
                            <p className="text-[12.5px] text-slate-500">—</p>
                        )}
                        {suggestion.floorsApplied?.length > 0 && (
                            <ul className="text-[11.5px] text-red-700 mt-2 space-y-0.5 list-disc list-inside">
                                {suggestion.floorsApplied.map((f) => (
                                    <li key={f.name}>
                                        L{f.level} · {lang === 'ar' ? f.reason_ar : f.reason_en}
                                    </li>
                                ))}
                            </ul>
                        )}
                    </Card>
                </div>

                {!overriding ? (
                    <div className="grid sm:grid-cols-2 gap-2 pt-1">
                        <button
                            type="button"
                            onClick={submitConfirm}
                            className="inline-flex items-center justify-center gap-2 bg-teal-600 hover:bg-teal-700 text-white rounded-xl px-4 py-3 text-[14px] font-semibold shadow-sm"
                        >
                            <ShieldCheck className="w-4 h-4" aria-hidden="true" />
                            {t('confirm_level', lang)}
                        </button>
                        <button
                            type="button"
                            onClick={() => setOverriding(true)}
                            className="inline-flex items-center justify-center gap-2 bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 rounded-xl px-4 py-3 text-[14px] font-semibold"
                        >
                            <Pencil className="w-4 h-4" aria-hidden="true" />
                            {t('override_level', lang)}
                        </button>
                    </div>
                ) : (
                    <form onSubmit={submitOverride} className="grid gap-3 border-t border-slate-100 pt-3 mt-1">
                        <div>
                            <label className="block text-[12.5px] font-semibold text-slate-700 mb-1">
                                {t('override_new_level', lang)}
                            </label>
                            <div className="grid grid-cols-5 gap-1.5">
                                {[1, 2, 3, 4, 5].map((lv) => {
                                    const lvLabel = LEVEL_LABELS[lv];
                                    const lvTone = tone[lvLabel.tone];
                                    const active = Number(newLevel) === lv;
                                    return (
                                        <button
                                            type="button"
                                            key={lv}
                                            onClick={() => setNewLevel(lv)}
                                            aria-pressed={active}
                                            className={`px-2 py-2 rounded-lg text-[12.5px] font-bold border transition-colors ${
                                                active
                                                    ? `${lvTone.bar} text-white border-transparent`
                                                    : 'bg-white border-slate-300 text-slate-700 hover:bg-slate-50'
                                            }`}
                                        >
                                            <span className="block text-base leading-none">{lv}</span>
                                            <span className="block text-[10px] mt-0.5 leading-tight">
                                                {lang === 'ar' ? lvLabel.ar : lvLabel.en}
                                            </span>
                                        </button>
                                    );
                                })}
                            </div>
                        </div>
                        <div>
                            <label className="block text-[12.5px] font-semibold text-slate-700 mb-1">
                                {t('override_reason_label', lang)}
                            </label>
                            <textarea
                                rows={2}
                                value={reason}
                                onChange={(e) => setReason(e.target.value)}
                                required
                                className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:border-teal-500 focus:ring-2 focus:ring-teal-100 outline-none text-[14px] bg-white min-h-[64px] resize-y"
                            />
                        </div>
                        <div className="flex flex-wrap gap-2 justify-end">
                            <button
                                type="button"
                                onClick={() => { setOverriding(false); setReason(''); setNewLevel(suggestion.level); }}
                                className="px-3 py-2 rounded-lg text-[13px] border border-slate-300 text-slate-700 hover:bg-slate-50"
                            >
                                {t('cancel', lang)}
                            </button>
                            <button
                                type="submit"
                                disabled={!reason.trim()}
                                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white text-[13px] font-semibold"
                            >
                                <CheckCircle2 className="w-4 h-4" aria-hidden="true" />
                                {t('save_override', lang)}
                            </button>
                        </div>
                    </form>
                )}
            </div>
        </div>
    );
}

function Card({ title, children }) {
    return (
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-3">
            <p className="text-[11px] font-bold uppercase tracking-wide text-slate-500 mb-1.5">{title}</p>
            {children}
        </div>
    );
}
