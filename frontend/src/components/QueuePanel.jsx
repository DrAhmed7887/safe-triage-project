import React, { useMemo, useState } from 'react';
import { Plus, Users } from 'lucide-react';

const FILTERS = [
    { id: 'all',      en: 'All',         ar: 'الكل' },
    { id: 'critical', en: '1–2 critical', ar: 'حرج' },
    { id: 'today',    en: 'Today',       ar: 'اليوم' },
];

const getGradient = (level) => {
    switch (level) {
        case 1: return 'from-red-500 to-red-600 shadow-red-500/30';
        case 2: return 'from-orange-500 to-orange-600 shadow-orange-500/30';
        case 3: return 'from-yellow-400 to-yellow-500 shadow-yellow-500/30';
        case 4: return 'from-green-500 to-green-600 shadow-green-500/30';
        case 5: return 'from-blue-500 to-blue-600 shadow-blue-500/30';
        default: return 'from-slate-400 to-slate-500 shadow-slate-400/30';
    }
};

const formatWait = (createdAt) => {
    if (!createdAt) return '';
    const ms = Date.now() - new Date(createdAt).getTime();
    if (Number.isNaN(ms) || ms < 0) return '';
    if (ms < 60_000) return 'now';
    const min = Math.floor(ms / 60_000);
    if (min < 60) return `${min} min`;
    const hr = Math.floor(min / 60);
    if (hr < 24) return `${hr} h`;
    const d = Math.floor(hr / 24);
    return `${d} d`;
};

/**
 * QueuePanel — left-rail Active Queue for the Dashboard.
 * Adapted from ui_kits/clinical-app/QueuePanel.jsx but reads real client-side
 * triage history from localStorage. No fabricated patients in production.
 */
export default function QueuePanel({
    refreshTrigger = 0,
    activeId = null,
    onSelect,
    onNewCase,
}) {
    const [filter, setFilter] = useState('all');

    // Read history during render, keyed on refreshTrigger so a new submission
    // re-evaluates the queue. refreshTrigger is intentionally a dep — the
    // linter can't see it's being used as a memo invalidation key.
    const patients = useMemo(() => {
        try {
            const stored = JSON.parse(localStorage.getItem('triageHistory') || '[]');
            return Array.isArray(stored) ? stored.slice(0, 25) : [];
        } catch {
            return [];
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [refreshTrigger]);

    const filtered = useMemo(() => {
        if (filter === 'critical') {
            return patients.filter((p) => p.triage_level === 1 || p.triage_level === 2);
        }
        if (filter === 'today') {
            const today = new Date().toDateString();
            return patients.filter(
                (p) => p.created_at && new Date(p.created_at).toDateString() === today,
            );
        }
        return patients;
    }, [patients, filter]);

    return (
        <aside className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden flex flex-col h-fit lg:max-h-[calc(100vh-6rem)] lg:sticky lg:top-20">
            {/* Header */}
            <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                    <Users className="w-4 h-4 text-slate-500" aria-hidden="true" />
                    <h2 className="text-sm font-bold text-slate-900 inline-flex items-baseline gap-1.5 min-w-0">
                        <span>Active Queue</span>
                        <span className="text-slate-300 font-normal" aria-hidden="true">|</span>
                        <span dir="rtl" className="font-arabic text-[12px] text-slate-500">
                            طابور الفرز
                        </span>
                    </h2>
                </div>
                <span
                    className="font-mono text-[10px] font-bold bg-slate-100 text-slate-600 rounded-full px-2 py-0.5"
                    aria-label={`${filtered.length} cases`}
                >
                    {filtered.length}
                </span>
            </div>

            {/* Filters */}
            <div className="px-3 py-2 border-b border-slate-100 flex gap-1 overflow-x-auto">
                {FILTERS.map((f) => (
                    <button
                        key={f.id}
                        type="button"
                        onClick={() => setFilter(f.id)}
                        aria-pressed={filter === f.id}
                        className={`px-2.5 py-1 rounded-full text-[11px] font-medium whitespace-nowrap flex-shrink-0 transition-colors ${
                            filter === f.id
                                ? 'bg-slate-900 text-white border border-slate-900'
                                : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
                        }`}
                    >
                        {f.en}
                    </button>
                ))}
            </div>

            {/* Rows */}
            <div className="overflow-y-auto flex-1 divide-y divide-slate-100 min-h-[120px]">
                {filtered.length === 0 ? (
                    <div className="p-6 text-center text-slate-500">
                        <p className="text-[13px] font-medium text-slate-700">No active cases</p>
                        <p className="mt-1 text-[12px] font-arabic" dir="rtl">
                            لا توجد حالات نشطة
                        </p>
                        <p className="mt-2 text-[11px] text-slate-500 leading-relaxed">
                            Submit a triage to populate the queue.
                        </p>
                    </div>
                ) : (
                    filtered.map((p) => {
                        const isActive = activeId != null && activeId === p.id;
                        const isResus = p.triage_level === 1;
                        const flags = Array.isArray(p.triage_red_flags) ? p.triage_red_flags : [];
                        return (
                            <button
                                key={p.id}
                                type="button"
                                onClick={() => onSelect?.(p)}
                                aria-pressed={isActive}
                                className={`w-full text-left px-3 py-3 hover:bg-slate-50 flex gap-3 items-start transition-colors group ${
                                    isActive
                                        ? 'bg-teal-50 border-l-[3px] border-teal-600 pl-[9px]'
                                        : ''
                                }`}
                            >
                                <span
                                    className={`flex-shrink-0 inline-flex items-center justify-center w-9 h-9 rounded-lg text-white font-extrabold text-base shadow-md bg-gradient-to-br ${getGradient(
                                        p.triage_level,
                                    )} ${isResus ? 'animate-pulse' : ''}`}
                                    aria-label={`ESI level ${p.triage_level}`}
                                >
                                    {p.triage_level || '—'}
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
                                            {formatWait(p.created_at)}
                                        </span>
                                    </div>
                                    <p className="text-[12.5px] text-slate-800 mt-0.5 line-clamp-1 leading-snug">
                                        {p.chief_complaint || '—'}
                                    </p>
                                    {p.triage_label_en && (
                                        <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-1">
                                            {p.triage_label_en}
                                            {p.triage_label_ar && (
                                                <>
                                                    {' '}
                                                    <span className="text-slate-300" aria-hidden="true">|</span>{' '}
                                                    <span dir="rtl" className="font-arabic">
                                                        {p.triage_label_ar}
                                                    </span>
                                                </>
                                            )}
                                        </p>
                                    )}
                                    {flags.length > 0 && (
                                        <div className="mt-1.5 flex flex-wrap gap-1">
                                            {flags.slice(0, 2).map((f, i) => (
                                                <span
                                                    key={`${f}-${i}`}
                                                    className="text-[10px] font-semibold bg-red-50 text-red-700 border border-red-200 rounded-full px-1.5 py-0.5"
                                                >
                                                    {String(f).slice(0, 24)}
                                                </span>
                                            ))}
                                            {flags.length > 2 && (
                                                <span className="text-[10px] font-mono text-slate-400">
                                                    +{flags.length - 2}
                                                </span>
                                            )}
                                        </div>
                                    )}
                                </div>
                            </button>
                        );
                    })
                )}
            </div>

            {/* Footer */}
            {onNewCase && (
                <div className="p-3 border-t border-slate-100">
                    <button
                        type="button"
                        onClick={onNewCase}
                        className="w-full inline-flex items-center justify-center gap-2 bg-teal-600 hover:bg-teal-700 text-white rounded-lg px-4 py-2.5 text-[13px] font-semibold transition-colors"
                    >
                        <Plus className="w-4 h-4" aria-hidden="true" />
                        <span>New case</span>
                        <span className="text-teal-100 font-normal" aria-hidden="true">|</span>
                        <span dir="rtl" className="font-arabic text-[12px]">
                            حالة جديدة
                        </span>
                    </button>
                </div>
            )}
        </aside>
    );
}
