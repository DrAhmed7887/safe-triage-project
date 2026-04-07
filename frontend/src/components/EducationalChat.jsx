import React, { useState, useRef, useEffect, useMemo } from 'react';
import {
    ChevronDown,
    ChevronUp,
    Send,
    BookOpen,
    ExternalLink,
    Loader2,
    Activity,
    Shield,
    Lightbulb,
    AlertTriangle,
    GraduationCap,
    Heart,
    Thermometer,
    Wind,
    Droplets,
    Gauge,
    Brain,
} from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ---------------------------------------------------------------------------
// NEWS2 scoring logic (client-side, deterministic)
// ---------------------------------------------------------------------------

const NEWS2_PARAMS = [
    {
        key: 'rr',
        label: 'Respiratory Rate',
        labelAr: '\u0645\u0639\u062f\u0644 \u0627\u0644\u062a\u0646\u0641\u0633',
        unit: '/min',
        icon: Wind,
        score: (v) => {
            if (v == null) return null;
            if (v <= 8) return 3;
            if (v <= 11) return 1;
            if (v <= 20) return 0;
            if (v <= 24) return 2;
            return 3;
        },
    },
    {
        key: 'spo2',
        label: 'SpO\u2082',
        labelAr: '\u062a\u0634\u0628\u0639 \u0627\u0644\u0623\u0643\u0633\u062c\u064a\u0646',
        unit: '%',
        icon: Droplets,
        score: (v) => {
            if (v == null) return null;
            if (v <= 91) return 3;
            if (v <= 93) return 2;
            if (v <= 95) return 1;
            return 0;
        },
    },
    {
        key: 'sbp',
        altKeys: ['bp_sys'],
        label: 'Systolic BP',
        labelAr: '\u0636\u063a\u0637 \u0627\u0644\u062f\u0645 \u0627\u0644\u0627\u0646\u0642\u0628\u0627\u0636\u064a',
        unit: 'mmHg',
        icon: Gauge,
        score: (v) => {
            if (v == null) return null;
            if (v <= 90) return 3;
            if (v <= 100) return 2;
            if (v <= 110) return 1;
            if (v <= 219) return 0;
            return 3;
        },
    },
    {
        key: 'hr',
        label: 'Heart Rate',
        labelAr: '\u0645\u0639\u062f\u0644 \u0636\u0631\u0628\u0627\u062a \u0627\u0644\u0642\u0644\u0628',
        unit: 'bpm',
        icon: Heart,
        score: (v) => {
            if (v == null) return null;
            if (v <= 40) return 3;
            if (v <= 50) return 1;
            if (v <= 90) return 0;
            if (v <= 110) return 1;
            if (v <= 130) return 2;
            return 3;
        },
    },
    {
        key: 'temp',
        label: 'Temperature',
        labelAr: '\u062f\u0631\u062c\u0629 \u0627\u0644\u062d\u0631\u0627\u0631\u0629',
        unit: '\u00b0C',
        icon: Thermometer,
        score: (v) => {
            if (v == null) return null;
            if (v <= 35.0) return 3;
            if (v <= 36.0) return 1;
            if (v <= 38.0) return 0;
            if (v <= 39.0) return 1;
            return 2;
        },
    },
    {
        key: 'consciousness',
        altKeys: ['avpu', 'gcs'],
        label: 'Consciousness',
        labelAr: '\u0645\u0633\u062a\u0648\u0649 \u0627\u0644\u0648\u0639\u064a',
        unit: '',
        icon: Brain,
        score: (v) => {
            if (v == null) return null;
            if (typeof v === 'string') {
                const lower = v.toLowerCase();
                return lower === 'a' || lower === 'alert' ? 0 : 3;
            }
            // GCS: 15 = alert, <15 = not alert
            if (typeof v === 'number') return v >= 15 ? 0 : 3;
            return null;
        },
    },
];

const SCORE_COLORS = {
    0: { bg: 'bg-emerald-100', text: 'text-emerald-700', border: 'border-emerald-300', dot: 'bg-emerald-500' },
    1: { bg: 'bg-yellow-100', text: 'text-yellow-700', border: 'border-yellow-300', dot: 'bg-yellow-500' },
    2: { bg: 'bg-orange-100', text: 'text-orange-700', border: 'border-orange-300', dot: 'bg-orange-500' },
    3: { bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-300', dot: 'bg-red-500' },
};

function getVitalValue(vitals, param) {
    if (!vitals) return null;
    if (vitals[param.key] != null) return vitals[param.key];
    if (param.altKeys) {
        for (const alt of param.altKeys) {
            if (vitals[alt] != null) return vitals[alt];
        }
    }
    return null;
}

// ---------------------------------------------------------------------------
// ESI Decision Path
// ---------------------------------------------------------------------------

const ESI_DECISIONS = [
    {
        point: 'A',
        question: 'Immediate life-saving intervention?',
        questionAr: '\u062a\u062f\u062e\u0644 \u0625\u0646\u0642\u0627\u0630 \u062d\u064a\u0627\u0629 \u0641\u0648\u0631\u064a\u061f',
        result: 'ESI 1',
        levels: [1],
    },
    {
        point: 'B',
        question: 'High-risk situation? Should not wait?',
        questionAr: '\u062d\u0627\u0644\u0629 \u0639\u0627\u0644\u064a\u0629 \u0627\u0644\u062e\u0637\u0648\u0631\u0629\u061f \u0645\u064a\u0646\u0641\u0639\u0634 \u064a\u0633\u062a\u0646\u0649\u061f',
        result: 'ESI 2',
        levels: [2],
    },
    {
        point: 'C',
        question: 'How many resources needed?',
        questionAr: '\u0643\u0627\u0645 \u0645\u0648\u0631\u062f \u0645\u062d\u062a\u0627\u062c\u061f',
        result: '2+ \u2192 ESI 3 \u00b7 1 \u2192 ESI 4 \u00b7 0 \u2192 ESI 5',
        levels: [3, 4, 5],
    },
    {
        point: 'D',
        question: 'Vital signs in danger zone?',
        questionAr: '\u0627\u0644\u0639\u0644\u0627\u0645\u0627\u062a \u0627\u0644\u062d\u064a\u0648\u064a\u0629 \u0641\u064a \u0645\u0646\u0637\u0642\u0629 \u0627\u0644\u062e\u0637\u0631\u061f',
        result: 'Upgrade to ESI 3',
        levels: [3],
        isCheck: true,
    },
];

// ---------------------------------------------------------------------------
// Quick questions
// ---------------------------------------------------------------------------

const QUICK_QUESTIONS_EN = [
    'What red flags should I watch for?',
    'How should I reassess this patient?',
    'What are common pitfalls for this presentation?',
];

const QUICK_QUESTIONS_AR = [
    '\u0625\u064a\u0647 \u0627\u0644\u0623\u0639\u0631\u0627\u0636 \u0627\u0644\u062e\u0637\u064a\u0631\u0629 \u0627\u0644\u0644\u064a \u0644\u0627\u0632\u0645 \u0623\u0631\u0627\u0642\u0628\u0647\u0627\u061f',
    '\u0625\u0632\u0627\u064a \u0623\u0639\u064a\u062f \u062a\u0642\u064a\u064a\u0645 \u0627\u0644\u0645\u0631\u064a\u0636\u061f',
    '\u0625\u064a\u0647 \u0627\u0644\u0623\u062e\u0637\u0627\u0621 \u0627\u0644\u0634\u0627\u0626\u0639\u0629 \u0641\u064a \u0641\u0631\u0632 \u0627\u0644\u062d\u0627\u0644\u0629 \u062f\u064a\u061f',
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function EducationalChat({
    esiLevel,
    news2Score,
    chiefComplaint,
    vitals,
    snomedCode,
    snomedTerm,
    icd10Code,
    icd10Description,
}) {
    const [isOpen, setIsOpen] = useState(false);
    const [sections, setSections] = useState(null);
    const [pubmedRefs, setPubmedRefs] = useState([]);
    const [initialLoading, setInitialLoading] = useState(false);
    const [initialError, setInitialError] = useState(false);

    // Follow-up Q&A
    const [qaMessages, setQaMessages] = useState([]);
    const [input, setInput] = useState('');
    const [qaLoading, setQaLoading] = useState(false);
    const qaEndRef = useRef(null);
    const inputRef = useRef(null);

    // NEWS2 breakdown (computed client-side)
    const news2Breakdown = useMemo(() => {
        if (!vitals) return [];
        return NEWS2_PARAMS.map((param) => {
            const value = getVitalValue(vitals, param);
            const score = param.score(value);
            return { ...param, value, paramScore: score };
        });
    }, [vitals]);

    const computedTotal = useMemo(() => {
        return news2Breakdown.reduce((sum, p) => sum + (p.paramScore ?? 0), 0);
    }, [news2Breakdown]);

    // Auto-load initial explanation when opened
    useEffect(() => {
        if (!isOpen || sections || initialLoading) return;
        loadInitialExplanation();
    }, [isOpen]); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => {
        if (isOpen && qaEndRef.current) {
            qaEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [qaMessages, isOpen]);

    const buildPayload = (query, isInitial = false) => ({
        query,
        esi_level: esiLevel,
        news2_score: news2Score,
        chief_complaint: chiefComplaint,
        vitals: vitals || {},
        snomed_code: snomedCode || null,
        snomed_term: snomedTerm || null,
        icd10_code: icd10Code || null,
        icd10_description: icd10Description || null,
        language: 'auto',
        initial_explain: isInitial,
        conversation_history: isInitial
            ? []
            : qaMessages.map((m) => ({ role: m.role, content: m.content })),
    });

    const loadInitialExplanation = async () => {
        setInitialLoading(true);
        setInitialError(false);
        try {
            const res = await fetch(`${API_URL}/api/educational-chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(buildPayload('Explain this triage decision', true)),
            });
            if (!res.ok) throw new Error(`${res.status}`);
            const data = await res.json();
            setSections(data.sections || { protocol_basis: data.answer });
            setPubmedRefs(data.pubmed_references || []);
        } catch {
            setInitialError(true);
        } finally {
            setInitialLoading(false);
        }
    };

    const sendFollowUp = async (text) => {
        if (!text.trim() || qaLoading) return;
        const userMsg = { role: 'user', content: text.trim() };
        const updated = [...qaMessages, userMsg];
        setQaMessages(updated);
        setInput('');
        setQaLoading(true);

        try {
            const res = await fetch(`${API_URL}/api/educational-chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(buildPayload(text.trim())),
            });
            if (!res.ok) throw new Error(`${res.status}`);
            const data = await res.json();
            setQaMessages((prev) => [
                ...prev,
                { role: 'assistant', content: data.answer, language: data.language_used },
            ]);
        } catch {
            setQaMessages((prev) => [
                ...prev,
                {
                    role: 'assistant',
                    content: 'Sorry, an error occurred. Please try again. | \u0639\u0630\u0631\u0627\u064b\u060c \u062d\u0627\u0648\u0644 \u0645\u0631\u0629 \u0623\u062e\u0631\u0649.',
                    language: 'en',
                },
            ]);
        } finally {
            setQaLoading(false);
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendFollowUp(input);
        }
    };

    const isArabic = (text) => {
        const arabicChars = [...text].filter(
            (c) => (c >= '\u0600' && c <= '\u06FF') || (c >= '\uFE70' && c <= '\uFEFF')
        ).length;
        const total = text.replace(/\s/g, '').length;
        return total > 0 && arabicChars / total > 0.3;
    };

    const ESI_COLORS_MAP = {
        1: 'bg-red-500',
        2: 'bg-orange-500',
        3: 'bg-yellow-400',
        4: 'bg-green-500',
        5: 'bg-blue-500',
    };

    // -----------------------------------------------------------------------
    // Collapsed state
    // -----------------------------------------------------------------------
    if (!isOpen) {
        return (
            <button
                onClick={() => setIsOpen(true)}
                className="w-full py-4 px-6 bg-gradient-to-r from-teal-500 to-emerald-500 hover:from-teal-600 hover:to-emerald-600 text-white rounded-2xl shadow-lg transition-all duration-200 flex items-center justify-center gap-3 group"
            >
                <GraduationCap className="w-5 h-5 group-hover:scale-110 transition-transform" />
                <span className="text-base font-semibold">
                    Learn About This Decision | \u0627\u062a\u0639\u0644\u0645 \u0639\u0646 \u0627\u0644\u0642\u0631\u0627\u0631 \u062f\u0647
                </span>
                <ChevronDown className="w-4 h-4 opacity-70" />
            </button>
        );
    }

    // -----------------------------------------------------------------------
    // Expanded — Educational Module
    // -----------------------------------------------------------------------
    return (
        <div className="bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden">
            {/* ── Header ── */}
            <div className="bg-gradient-to-r from-teal-600 to-emerald-500 px-5 py-4">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-white">
                        <GraduationCap className="w-5 h-5" />
                        <span className="font-bold text-sm tracking-wide">
                            SAFE-Triage Educational Module
                        </span>
                    </div>
                    <button
                        onClick={() => setIsOpen(false)}
                        className="text-white/80 hover:text-white transition-colors p-1"
                    >
                        <ChevronUp className="w-5 h-5" />
                    </button>
                </div>
                <div className="flex flex-wrap gap-2 mt-3">
                    <span className={`${ESI_COLORS_MAP[esiLevel] || 'bg-slate-500'} text-white text-xs font-bold px-2.5 py-1 rounded-full`}>
                        ESI {esiLevel}
                    </span>
                    <span className="bg-white/20 text-white text-xs font-medium px-2.5 py-1 rounded-full">
                        NEWS2: {news2Score}
                    </span>
                    <span className="bg-white/20 text-white text-xs font-medium px-2.5 py-1 rounded-full truncate max-w-[200px]">
                        {chiefComplaint}
                    </span>
                </div>
            </div>

            <div className="p-5 space-y-5">
                {/* ── NEWS2 Visual Breakdown ── */}
                <div className="border border-slate-200 rounded-xl overflow-hidden">
                    <div className="bg-slate-50 px-4 py-2.5 border-b border-slate-200 flex items-center gap-2">
                        <Activity className="w-4 h-4 text-teal-600" />
                        <h3 className="text-sm font-bold text-slate-800">
                            NEWS2 Score Breakdown | \u062a\u0641\u0627\u0635\u064a\u0644 \u062f\u0631\u062c\u0629 NEWS2
                        </h3>
                    </div>
                    <div className="divide-y divide-slate-100">
                        {news2Breakdown.map((param) => {
                            const colors = param.paramScore != null ? SCORE_COLORS[param.paramScore] : null;
                            const Icon = param.icon;
                            return (
                                <div key={param.key} className="flex items-center px-4 py-2.5 gap-3">
                                    <Icon className="w-4 h-4 text-slate-400 flex-shrink-0" />
                                    <div className="flex-1 min-w-0">
                                        <div className="text-xs font-medium text-slate-700 truncate">{param.label}</div>
                                        <div className="text-[10px] text-slate-400 font-arabic">{param.labelAr}</div>
                                    </div>
                                    <div className="text-sm font-mono text-slate-600 w-16 text-right">
                                        {param.value != null ? `${param.value}${param.unit ? ` ${param.unit}` : ''}` : '\u2014'}
                                    </div>
                                    {colors ? (
                                        <div className={`${colors.bg} ${colors.text} ${colors.border} border rounded-lg px-2.5 py-1 text-xs font-bold w-10 text-center`}>
                                            {param.paramScore}
                                        </div>
                                    ) : (
                                        <div className="bg-slate-100 text-slate-400 border border-slate-200 rounded-lg px-2.5 py-1 text-xs w-10 text-center">
                                            \u2014
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                    <div className="bg-slate-50 px-4 py-3 border-t border-slate-200 flex items-center justify-between">
                        <span className="text-xs font-semibold text-slate-600">
                            Total Score | \u0627\u0644\u0645\u062c\u0645\u0648\u0639
                        </span>
                        <span className={`text-lg font-black ${computedTotal >= 7 ? 'text-red-600' : computedTotal >= 5 ? 'text-orange-600' : computedTotal >= 1 ? 'text-yellow-600' : 'text-emerald-600'}`}>
                            {computedTotal}
                        </span>
                    </div>
                </div>

                {/* ── ESI Decision Path ── */}
                <div className="border border-slate-200 rounded-xl overflow-hidden">
                    <div className="bg-slate-50 px-4 py-2.5 border-b border-slate-200 flex items-center gap-2">
                        <Shield className="w-4 h-4 text-teal-600" />
                        <h3 className="text-sm font-bold text-slate-800">
                            ESI v5 Decision Path | \u0645\u0633\u0627\u0631 \u0642\u0631\u0627\u0631 ESI
                        </h3>
                    </div>
                    <div className="p-3 space-y-2">
                        {ESI_DECISIONS.map((step) => {
                            const isActive = step.levels.includes(esiLevel);
                            const isPast = step.levels.some((l) => l > esiLevel) && !step.isCheck;
                            return (
                                <div
                                    key={step.point}
                                    className={`flex items-start gap-3 p-3 rounded-lg border transition-colors ${
                                        isActive
                                            ? 'bg-teal-50 border-teal-300 ring-1 ring-teal-200'
                                            : isPast
                                                ? 'bg-slate-50 border-slate-200 opacity-50'
                                                : 'bg-slate-50 border-slate-200'
                                    }`}
                                >
                                    <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                                        isActive
                                            ? 'bg-teal-600 text-white'
                                            : 'bg-slate-300 text-white'
                                    }`}>
                                        {step.point}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="text-xs font-medium text-slate-700">
                                            {step.question}
                                        </div>
                                        <div className="text-[10px] text-slate-400 font-arabic mt-0.5" dir="rtl">
                                            {step.questionAr}
                                        </div>
                                        {isActive && (
                                            <div className="mt-1.5 text-xs font-bold text-teal-700 flex items-center gap-1">
                                                \u2713 {step.result}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* ── AI-Generated Educational Cards ── */}
                {initialLoading && (
                    <div className="flex items-center justify-center py-8 gap-3 text-teal-600">
                        <Loader2 className="w-5 h-5 animate-spin" />
                        <span className="text-sm font-medium">
                            Generating explanation... | \u062c\u0627\u0631\u064a \u062a\u0648\u0644\u064a\u062f \u0627\u0644\u0634\u0631\u062d...
                        </span>
                    </div>
                )}

                {initialError && (
                    <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-center">
                        <p className="text-sm text-red-700 mb-2">
                            Failed to load explanation | \u0641\u0634\u0644 \u062a\u062d\u0645\u064a\u0644 \u0627\u0644\u0634\u0631\u062d
                        </p>
                        <button
                            onClick={loadInitialExplanation}
                            className="text-xs bg-red-600 text-white px-3 py-1.5 rounded-lg hover:bg-red-700 transition-colors"
                        >
                            Retry | \u0625\u0639\u0627\u062f\u0629
                        </button>
                    </div>
                )}

                {sections && (
                    <div className="space-y-3">
                        {/* Protocol Basis */}
                        {sections.protocol_basis && (
                            <div className="p-4 bg-teal-50 border-l-4 border-teal-500 rounded-lg">
                                <h4 className="text-xs font-bold text-teal-800 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                                    <Shield className="w-3.5 h-3.5" />
                                    Protocol Basis | \u0623\u0633\u0627\u0633 \u0627\u0644\u0628\u0631\u0648\u062a\u0648\u0643\u0648\u0644
                                </h4>
                                <p className="text-sm text-teal-900 leading-relaxed" dir="auto">
                                    {sections.protocol_basis}
                                </p>
                            </div>
                        )}

                        {/* Supporting Evidence */}
                        {sections.supporting_evidence && (
                            <div className="p-4 bg-blue-50 border-l-4 border-blue-400 rounded-lg">
                                <h4 className="text-xs font-bold text-blue-800 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                                    <Activity className="w-3.5 h-3.5" />
                                    Clinical Evidence | \u0627\u0644\u062f\u0644\u064a\u0644 \u0627\u0644\u0633\u0631\u064a\u0631\u064a
                                </h4>
                                <p className="text-sm text-blue-900 leading-relaxed" dir="auto">
                                    {sections.supporting_evidence}
                                </p>
                            </div>
                        )}

                        {/* Clinical Pearls */}
                        {sections.clinical_pearls && (
                            <div className="p-4 bg-purple-50 border-l-4 border-purple-400 rounded-lg">
                                <h4 className="text-xs font-bold text-purple-800 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                                    <Lightbulb className="w-3.5 h-3.5" />
                                    Clinical Pearls | \u0646\u0635\u0627\u0626\u062d \u0633\u0631\u064a\u0631\u064a\u0629
                                </h4>
                                <p className="text-sm text-purple-900 leading-relaxed" dir="auto">
                                    {sections.clinical_pearls}
                                </p>
                            </div>
                        )}

                        {/* Limitations */}
                        {sections.limitations && (
                            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                                <div className="flex items-start gap-2">
                                    <AlertTriangle className="w-3.5 h-3.5 text-amber-600 flex-shrink-0 mt-0.5" />
                                    <p className="text-xs text-amber-800 leading-relaxed" dir="auto">
                                        {sections.limitations}
                                    </p>
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* ── PubMed References ── */}
                {pubmedRefs.length > 0 && (
                    <div className="border border-blue-200 rounded-xl overflow-hidden">
                        <div className="bg-blue-50 px-4 py-2.5 border-b border-blue-200 flex items-center gap-2">
                            <BookOpen className="w-4 h-4 text-blue-600" />
                            <h3 className="text-sm font-bold text-blue-800">
                                PubMed References | \u0645\u0631\u0627\u062c\u0639 \u0639\u0644\u0645\u064a\u0629
                            </h3>
                        </div>
                        <ul className="divide-y divide-blue-100">
                            {pubmedRefs.map((ref) => (
                                <li key={ref.pmid} className="px-4 py-3">
                                    <a
                                        href={ref.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-sm font-medium text-blue-800 hover:text-blue-600 hover:underline inline-flex items-start gap-1.5 leading-snug"
                                    >
                                        {ref.title}
                                        <ExternalLink className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                                    </a>
                                    <div className="text-xs text-blue-600 mt-1">
                                        {ref.authors} &middot; <em>{ref.journal}</em> ({ref.year})
                                    </div>
                                </li>
                            ))}
                        </ul>
                    </div>
                )}

                {/* ── Follow-up Q&A ── */}
                <div className="border border-slate-200 rounded-xl overflow-hidden">
                    <div className="bg-slate-50 px-4 py-2.5 border-b border-slate-200 flex items-center gap-2">
                        <GraduationCap className="w-4 h-4 text-teal-600" />
                        <h3 className="text-sm font-bold text-slate-800">
                            Ask a Follow-up | \u0627\u0633\u0623\u0644 \u0633\u0624\u0627\u0644
                        </h3>
                    </div>

                    {/* Quick questions */}
                    <div className="px-4 pt-3 pb-2 flex flex-wrap gap-1.5">
                        {QUICK_QUESTIONS_EN.map((q, i) => (
                            <button
                                key={i}
                                onClick={() => sendFollowUp(q)}
                                disabled={qaLoading}
                                className="text-[11px] bg-teal-50 text-teal-700 border border-teal-200 rounded-full px-3 py-1.5 hover:bg-teal-100 transition-colors disabled:opacity-50"
                            >
                                {q}
                            </button>
                        ))}
                    </div>

                    {/* Q&A messages */}
                    {qaMessages.length > 0 && (
                        <div className="max-h-[300px] overflow-y-auto px-4 py-2 space-y-3">
                            {qaMessages.map((msg, i) => {
                                const msgIsAr = msg.language === 'ar' || isArabic(msg.content);
                                if (msg.role === 'user') {
                                    return (
                                        <div key={i} className="flex justify-end">
                                            <div
                                                className="bg-teal-50 border border-teal-100 rounded-xl rounded-br-sm px-3.5 py-2.5 max-w-[85%]"
                                                dir={isArabic(msg.content) ? 'rtl' : 'ltr'}
                                            >
                                                <p className={`text-sm text-teal-900 ${isArabic(msg.content) ? 'font-arabic' : ''}`}>
                                                    {msg.content}
                                                </p>
                                            </div>
                                        </div>
                                    );
                                }
                                return (
                                    <div key={i} className="flex justify-start">
                                        <div
                                            className="bg-slate-50 border border-slate-100 rounded-xl rounded-bl-sm px-3.5 py-2.5 max-w-[95%]"
                                            dir={msgIsAr ? 'rtl' : 'ltr'}
                                        >
                                            <p className={`text-sm text-slate-800 whitespace-pre-wrap leading-relaxed ${msgIsAr ? 'font-arabic' : ''}`}>
                                                {msg.content}
                                            </p>
                                        </div>
                                    </div>
                                );
                            })}

                            {qaLoading && (
                                <div className="flex justify-start">
                                    <div className="bg-slate-50 border border-slate-100 rounded-xl rounded-bl-sm px-3.5 py-2.5">
                                        <Loader2 className="w-4 h-4 text-teal-500 animate-spin" />
                                    </div>
                                </div>
                            )}
                            <div ref={qaEndRef} />
                        </div>
                    )}

                    {/* Input */}
                    <div className="border-t border-slate-100 p-3 flex gap-2">
                        <input
                            ref={inputRef}
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            disabled={qaLoading}
                            placeholder="Ask about the triage... | \u0627\u0633\u0623\u0644 \u0639\u0646 \u0627\u0644\u0641\u0631\u0632..."
                            className="flex-1 text-sm border border-slate-200 rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent disabled:bg-slate-50 disabled:text-slate-400 placeholder:text-slate-400"
                            dir="auto"
                        />
                        <button
                            onClick={() => sendFollowUp(input)}
                            disabled={qaLoading || !input.trim()}
                            className="bg-teal-600 text-white rounded-xl px-4 py-2.5 hover:bg-teal-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                        >
                            <Send className="w-4 h-4" />
                        </button>
                    </div>
                </div>
            </div>

            {/* ── Disclaimer footer ── */}
            <div className="px-5 py-2.5 bg-amber-50 border-t border-amber-100 text-center">
                <p className="text-[10px] text-amber-800 leading-snug">
                    {'\u2695\ufe0f'} Educational only {'\u2014'} Final triage is determined by the deterministic ESI/NEWS2 engine and confirmed by the treating clinician. | \u062a\u0639\u0644\u064a\u0645\u064a \u0641\u0642\u0637 {'\u2014'} \u0627\u0644\u0641\u0631\u0632 \u0627\u0644\u0646\u0647\u0627\u0626\u064a \u064a\u062a\u0645 \u0628\u0648\u0627\u0633\u0637\u0629 \u0645\u062d\u0631\u0643 ESI/NEWS2 \u0627\u0644\u062b\u0627\u0628\u062a \u0648\u064a\u064f\u0624\u0643\u062f \u0645\u0646 \u0627\u0644\u0637\u0628\u064a\u0628 \u0627\u0644\u0645\u0639\u0627\u0644\u062c.
                </p>
            </div>
        </div>
    );
}
