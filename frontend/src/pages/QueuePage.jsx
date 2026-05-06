import React from 'react';
import AppHeader from '../components/AppHeader';
import PatientList from '../components/PatientList';

/**
 * QueuePage — full-page Triage Queue route at /queue.
 * Reuses the existing PatientList component (search, export, clear,
 * detail modal) at full width. Kept separate from the Dashboard's slim
 * left-rail QueuePanel because PatientList carries supervisor-level
 * controls (Export My Cases, Clear) that should not be crammed into
 * the rail.
 */
export default function QueuePage() {
    return (
        <div className="min-h-screen bg-slate-50 font-sans" dir="ltr">
            <AppHeader />
            <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                <div className="mb-5">
                    <h1 className="text-2xl font-bold text-slate-900 inline-flex items-baseline gap-2 flex-wrap">
                        <span>Triage Queue</span>
                        <span className="text-slate-300 font-normal" aria-hidden="true">|</span>
                        <span dir="rtl" className="font-arabic text-xl text-slate-700">
                            طابور الفرز
                        </span>
                    </h1>
                    <p className="text-sm text-slate-500 mt-1 leading-relaxed">
                        Local case history. Search, filter, and export your cases.
                        <span className="hidden sm:inline">{' '}</span>
                        <span dir="rtl" className="font-arabic block sm:inline">
                            سجل الحالات المحلي. ابحث وصدّر حالاتك.
                        </span>
                    </p>
                </div>
                <PatientList refreshTrigger={0} />
            </main>
        </div>
    );
}
