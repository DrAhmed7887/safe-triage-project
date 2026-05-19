import React from 'react';
import { Printer, Download, Plus } from 'lucide-react';
import { LEVEL_LABELS } from '../../lib/triageEngineOfflineFallback';
import { t } from '../../lib/i18n';
import { exportEntryAsJson } from '../../lib/hospitalLite';
import EngineSourceBadge from './EngineSourceBadge';

const TONE_BG = {
    red:    '#fef2f2',
    orange: '#fff7ed',
    yellow: '#fefce8',
    green:  '#f0fdf4',
    blue:   '#eff6ff',
};

/**
 * HandoffRecord — bilingual printable summary shown after a triage decision
 * is committed to the queue. Doubles as the on-screen confirmation panel.
 *
 * Print stylesheet is bundled inline (`@media print`) so it works without
 * touching index.css.
 */
export default function HandoffRecord({ lang, entry, onNew }) {
    if (!entry) return null;
    const label = LEVEL_LABELS[entry.final_level || entry.suggested_level];
    const bg = TONE_BG[label?.tone] || TONE_BG.yellow;

    return (
        <div id="handoff-record" className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <style>{`
                @media print {
                    body * { visibility: hidden !important; }
                    #handoff-record, #handoff-record * { visibility: visible !important; }
                    #handoff-record { position: absolute; left: 0; top: 0; width: 100%; box-shadow: none; border: none; }
                    .print\\:hidden { display: none !important; }
                }
            `}</style>

            <header className="px-4 sm:px-6 py-4 border-b border-slate-100 flex flex-wrap items-center justify-between gap-3">
                <div>
                    <p className="text-[11px] uppercase tracking-wider text-slate-500 font-semibold">
                        {t('handoff_title', lang)}
                    </p>
                    <p className="text-base font-bold text-slate-900">
                        {entry.patient_id}
                    </p>
                </div>
                <div className="flex items-center gap-2 print:hidden">
                    <button
                        type="button"
                        onClick={() => window.print()}
                        className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-[12.5px] font-semibold"
                    >
                        <Printer className="w-4 h-4" aria-hidden="true" />
                        {t('print_handoff', lang)}
                    </button>
                    <button
                        type="button"
                        onClick={() => exportEntryAsJson(entry)}
                        className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 text-[12.5px] font-semibold"
                    >
                        <Download className="w-4 h-4" aria-hidden="true" />
                        {t('export_json', lang)}
                    </button>
                    {onNew && (
                        <button
                            type="button"
                            onClick={onNew}
                            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-[12.5px] font-semibold"
                        >
                            <Plus className="w-4 h-4" aria-hidden="true" />
                            {t('start_new', lang)}
                        </button>
                    )}
                </div>
            </header>

            <div className="px-4 sm:px-6 py-4 grid gap-4">
                {/* Engine source — surfaced first so it can never be missed
                    when reviewing or auditing the case. */}
                <EngineSourceBadge
                    lang={lang}
                    source={entry.engine_source || entry.suggestion?.engine_source}
                    error={entry.fallback_error}
                    variant="banner"
                />

                {/* Top: final level banner */}
                <div
                    className="rounded-xl px-4 py-3 flex items-center gap-4 border border-slate-200"
                    style={{ background: bg }}
                >
                    <div
                        className="w-14 h-14 rounded-2xl text-white inline-flex items-center justify-center text-3xl font-extrabold shadow-sm"
                        style={{ background: label?.color }}
                    >
                        {entry.final_level}
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="text-[11px] text-slate-500 uppercase font-semibold tracking-wider">
                            {t('handoff_final', lang)}
                        </p>
                        <p className="text-xl font-bold text-slate-900">
                            {lang === 'ar' ? label?.ar : label?.en}
                        </p>
                        {entry.action === 'overridden' && (
                            <p className="text-[12px] text-amber-700 mt-0.5">
                                ↻ {t('handoff_suggested', lang)}: L{entry.suggested_level}
                            </p>
                        )}
                    </div>
                </div>

                {/* Patient + clinician + complaint */}
                <div className="grid sm:grid-cols-2 gap-3 text-[13px] text-slate-800">
                    <DL items={[
                        [t('patient_name', lang), entry.patient_name || '—'],
                        [t('age', lang),         entry.age ? `${entry.age}` : '—'],
                        [t('gender', lang),      t(entry.gender || 'male', lang)],
                    ]} />
                    <DL items={[
                        [t('handoff_clinician', lang), entry.clinician?.name || '—'],
                        [t('role', lang),              t(`role_${entry.clinician?.role || 'nurse'}`, lang)],
                        [t('handoff_generated', lang), new Date(entry.created_at).toLocaleString(lang === 'ar' ? 'ar-EG' : 'en-GB')],
                    ]} />
                </div>

                <div>
                    <p className="text-[11px] uppercase font-bold text-slate-500 tracking-wide mb-1">
                        {t('section_complaint', lang)}
                    </p>
                    <p className="text-[14px] text-slate-900 leading-relaxed bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 whitespace-pre-wrap">
                        {entry.chief_complaint || '—'}
                    </p>
                </div>

                {/* Vitals */}
                <div>
                    <p className="text-[11px] uppercase font-bold text-slate-500 tracking-wide mb-1">
                        {t('section_vitals', lang)}
                    </p>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[12.5px] font-mono">
                        {[
                            ['HR',  entry.vitals?.hr,  'bpm'],
                            ['RR',  entry.vitals?.rr,  '/min'],
                            ['BP',  entry.vitals?.sbp != null && entry.vitals?.dbp != null ? `${entry.vitals.sbp}/${entry.vitals.dbp}` : entry.vitals?.sbp ?? '—', 'mmHg'],
                            ['SpO₂', entry.vitals?.spo2, '%'],
                            ['T°',  entry.vitals?.temp, '°C'],
                            ['AVPU', entry.consciousness, ''],
                            ['Pain', entry.pain_scale, '/10'],
                            ['NEWS2', entry.suggestion?.news2?.total, `(${entry.suggestion?.news2?.risk})`],
                        ].map(([k, v, u]) => (
                            <div key={k} className="bg-white border border-slate-200 rounded-lg px-2.5 py-1.5">
                                <p className="text-[10px] text-slate-500">{k}</p>
                                <p className="text-slate-900">{v != null && v !== '' ? `${v} ${u || ''}`.trim() : '—'}</p>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Audit trail */}
                <div>
                    <p className="text-[11px] uppercase font-bold text-slate-500 tracking-wide mb-1">
                        {t('audit_trail', lang)}
                    </p>
                    <ol className="text-[12.5px] text-slate-700 space-y-1">
                        {(entry.audit || []).map((ev, i) => (
                            <li key={i} className="font-mono">
                                <span className="text-slate-400">[{new Date(ev.at).toLocaleString(lang === 'ar' ? 'ar-EG' : 'en-GB')}]</span>{' '}
                                <span className="font-bold">{t(`audit_${ev.action}`, lang)}</span>{' '}
                                <span>L{ev.level}</span>
                                {ev.by ? <span className="text-slate-500"> · {ev.by} ({ev.role})</span> : null}
                                {ev.engine_source ? <span className="text-slate-500"> · {ev.engine_source}</span> : null}
                                {ev.fallback_error ? <span className="text-amber-700"> · fallback:{ev.fallback_error}</span> : null}
                                {ev.reason ? <span className="text-amber-700"> · {ev.reason}</span> : null}
                            </li>
                        ))}
                    </ol>
                </div>
            </div>
        </div>
    );
}

function DL({ items }) {
    return (
        <dl className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 grid grid-cols-[auto,1fr] gap-x-3 gap-y-1">
            {items.map(([k, v]) => (
                <React.Fragment key={k}>
                    <dt className="text-[11px] uppercase tracking-wide text-slate-500 font-semibold self-center">{k}</dt>
                    <dd className="text-slate-900 truncate">{v}</dd>
                </React.Fragment>
            ))}
        </dl>
    );
}
