import React from 'react';
import { BookOpen, ExternalLink } from 'lucide-react';
import AppHeader from '../components/AppHeader';

/**
 * KnowledgePage — placeholder for the Knowledge tab at /knowledge.
 * Real RAG-grounded educational content lives inline in TriageResult's
 * EducationalChat component (per-case companion). This page sets
 * expectations for a future standalone knowledge surface and lists the
 * standards SAFE-Triage is built against.
 */
export default function KnowledgePage() {
    const standards = [
        { en: 'ESI v5 (Emergency Severity Index)', ar: 'مؤشر شدة الطوارئ', source: 'AHRQ' },
        { en: 'NEWS2 (National Early Warning Score)', ar: 'مؤشر الإنذار المبكر الوطني', source: 'RCP' },
        { en: 'SNOMED-CT clinical terminology', ar: 'مصطلحات سنوميد السريرية', source: 'SNOMED International' },
        { en: 'ICD-10 diagnosis coding', ar: 'تصنيف الأمراض الدولي', source: 'WHO' },
        { en: 'GAHAR hospital safety standards', ar: 'معايير الجهار للسلامة', source: 'EAHA' },
    ];

    return (
        <div className="min-h-screen bg-slate-50 font-sans" dir="ltr">
            <AppHeader />
            <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                <div className="mb-5">
                    <h1 className="text-2xl font-bold text-slate-900 inline-flex items-baseline gap-2 flex-wrap">
                        <BookOpen className="w-6 h-6 text-teal-600 self-center" aria-hidden="true" />
                        <span>Knowledge</span>
                        <span className="text-slate-300 font-normal" aria-hidden="true">|</span>
                        <span dir="rtl" className="font-arabic text-xl text-slate-700">
                            المعرفة
                        </span>
                    </h1>
                    <p className="text-sm text-slate-500 mt-1">
                        Standards reference and clinical companions.
                    </p>
                </div>

                <section
                    className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 mb-5"
                    aria-labelledby="education-companion-heading"
                >
                    <h2
                        id="education-companion-heading"
                        className="text-base font-bold text-slate-900 mb-2"
                    >
                        Per-case educational companion
                    </h2>
                    <p className="text-[13px] text-slate-600 leading-relaxed">
                        After each triage, the result page includes an inline,
                        RAG-grounded educational layer with citations specific to that
                        case. Open any case to use it.
                    </p>
                    <p
                        className="text-[13px] text-slate-500 leading-relaxed font-arabic mt-1"
                        dir="rtl"
                    >
                        بعد كل فرز، تظهر طبقة تعليمية موثّقة بالمصادر داخل صفحة النتيجة.
                    </p>
                </section>

                <section
                    className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6"
                    aria-labelledby="standards-heading"
                >
                    <h2 id="standards-heading" className="text-base font-bold text-slate-900 mb-3">
                        Standards SAFE-Triage is built against
                    </h2>
                    <ul className="divide-y divide-slate-100">
                        {standards.map((s) => (
                            <li
                                key={s.en}
                                className="py-3 flex items-start gap-3 first:pt-0 last:pb-0"
                            >
                                <ExternalLink
                                    className="w-4 h-4 text-teal-600 mt-0.5 flex-shrink-0"
                                    aria-hidden="true"
                                />
                                <div className="flex-1 min-w-0">
                                    <div className="text-[13.5px] font-semibold text-slate-900">
                                        {s.en}
                                    </div>
                                    <div
                                        className="text-[12.5px] text-slate-600 font-arabic mt-0.5"
                                        dir="rtl"
                                    >
                                        {s.ar}
                                    </div>
                                </div>
                                <span className="font-mono text-[10px] font-semibold bg-slate-100 text-slate-600 rounded-full px-2 py-0.5 mt-1">
                                    {s.source}
                                </span>
                            </li>
                        ))}
                    </ul>
                </section>

                <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-amber-800 text-[13px] leading-relaxed">
                    A standalone knowledge surface is in development. This page lists the
                    clinical standards in scope today.
                    <span className="block font-arabic mt-1" dir="rtl">
                        صفحة معرفية مستقلة قيد التطوير. الصفحة الحالية تستعرض المعايير
                        السريرية المعتمدة.
                    </span>
                </div>
            </main>
        </div>
    );
}
