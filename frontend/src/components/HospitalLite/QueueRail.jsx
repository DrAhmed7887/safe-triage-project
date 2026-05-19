import React from 'react';
import { Users, Plus, CloudOff } from 'lucide-react';
import { t } from '../../lib/i18n';
import { LEVEL_LABELS } from '../../lib/triageEngineOfflineFallback';

const gradient = {
    red:    'from-red-500 to-red-600 shadow-red-500/30',
    orange: 'from-orange-500 to-orange-600 shadow-orange-500/30',
    yellow: 'from-yellow-400 to-yellow-500 shadow-yellow-500/30',
    green:  'from-green-500 to-green-600 shadow-green-500/30',
    blue:   'from-blue-500 to-blue-600 shadow-blue-500/30',
};

function formatWait(createdAt, lang) {
    if (!createdAt) return '';
    const ms = Date.now() - new Date(createdAt).getTime();
    if (Number.isNaN(ms) || ms < 0) return '';
    if (ms < 60_000) return lang === 'ar' ? 'الآن' : 'now';
    const min = Math.floor(ms / 60_000);
    if (min < 60) return lang === 'ar' ? `${min} د` : `${min} min`;
    const hr = Math.floor(min / 60);
    if (hr < 24) return lang === 'ar' ? `${hr} س` : `${hr} h`;
    const d = Math.floor(hr / 24);
    return lang === 'ar' ? `${d} ي` : `${d} d`;
}

export default function QueueRail({ lang, items, activeId, onSelect, onNewCase }) {
    return (
        <aside className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden flex flex-col h-fit lg:max-h-[calc(100vh-7rem)] lg:sticky lg:top-20">
            <header className="px-4 py-3 border-b border-slate-100 flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                    <Users className="w-4 h-4 text-slate-500" aria-hidden="true" />
                    <h2 className="text-[13px] font-bold text-slate-900">{t('active_queue', lang)}</h2>
                </div>
                <span className="font-mono text-[10px] font-bold bg-slate-100 text-slate-600 rounded-full px-2 py-0.5">
                    {items.length}
                </span>
            </header>

            <div className="overflow-y-auto flex-1 divide-y divide-slate-100 min-h-[120px]">
                {items.length === 0 ? (
                    <div className="p-6 text-center">
                        <p className="text-[13px] font-medium text-slate-700">{t('no_cases', lang)}</p>
                    </div>
                ) : (
                    items.map((p) => {
                        const isActive = activeId != null && activeId === p.id;
                        const label = LEVEL_LABELS[p.final_level || p.suggested_level];
                        const isResus = (p.final_level || p.suggested_level) === 1;
                        const overrode = p.action === 'overridden';
                        return (
                            <button
                                key={p.id}
                                type="button"
                                onClick={() => onSelect?.(p)}
                                aria-pressed={isActive}
                                className={`w-full text-left px-3 py-3 hover:bg-slate-50 flex gap-3 items-start transition-colors ${
                                    isActive ? 'bg-teal-50 border-l-[3px] border-teal-600 pl-[9px]' : ''
                                }`}
                            >
                                <span
                                    className={`flex-shrink-0 inline-flex items-center justify-center w-9 h-9 rounded-lg text-white font-extrabold text-base shadow-md bg-gradient-to-br ${gradient[label?.tone] || gradient.yellow} ${
                                        isResus ? 'animate-pulse' : ''
                                    }`}
                                    aria-label={`Level ${p.final_level || p.suggested_level}`}
                                >
                                    {p.final_level || p.suggested_level}
                                </span>
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-baseline gap-2">
                                        <span className="text-[12px] font-mono font-semibold text-slate-900 truncate">
                                            {p.patient_id || `#${p.id}`}
                                        </span>
                                        <span className="text-[11px] text-slate-500 font-mono whitespace-nowrap">
                                            {p.gender === 'male' ? 'M' : p.gender === 'female' ? 'F' : '?'}
                                            {p.age ? ` · ${Math.round(p.age)}y` : ''}
                                        </span>
                                        <span className="text-[11px] text-slate-400 font-mono ml-auto whitespace-nowrap">
                                            {formatWait(p.created_at, lang)}
                                        </span>
                                    </div>
                                    <p className="text-[12.5px] text-slate-800 mt-0.5 line-clamp-1 leading-snug">
                                        {p.chief_complaint || '—'}
                                    </p>
                                    {overrode && (
                                        <p className="text-[10.5px] text-amber-700 mt-0.5">
                                            ↻ {t('audit_overridden', lang)} L{p.suggested_level} → L{p.final_level}
                                        </p>
                                    )}
                                    {p.engine_source === 'offline_js_fallback' && (
                                        <p className="text-[10.5px] text-amber-700 mt-0.5 inline-flex items-center gap-1">
                                            <CloudOff className="w-3 h-3" aria-hidden="true" />
                                            {t('engine_fallback', lang)}
                                        </p>
                                    )}
                                </div>
                            </button>
                        );
                    })
                )}
            </div>

            {onNewCase && (
                <div className="p-3 border-t border-slate-100">
                    <button
                        type="button"
                        onClick={onNewCase}
                        className="w-full inline-flex items-center justify-center gap-2 bg-teal-600 hover:bg-teal-700 text-white rounded-lg px-4 py-2.5 text-[13px] font-semibold transition-colors"
                    >
                        <Plus className="w-4 h-4" aria-hidden="true" />
                        <span>{t('new_case', lang)}</span>
                    </button>
                </div>
            )}
        </aside>
    );
}
