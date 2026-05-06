import React, { useMemo, useState } from 'react';
import TriageForm from '../components/TriageForm';
import TriageResult from '../components/TriageResult';
import TriageStatsWidget from '../components/TriageStatsWidget';
import AppHeader from '../components/AppHeader';
import QueuePanel from '../components/QueuePanel';

export default function Dashboard() {
    const [currentResult, setCurrentResult] = useState(null);
    const [refreshTrigger, setRefreshTrigger] = useState(0);
    const [activePatientId, setActivePatientId] = useState(null);

    // Derive a queue count for the AppHeader badge from local history.
    // refreshTrigger is the memo invalidation key — the linter can't see
    // that, so suppress its check on the dep array.
    const queueCount = useMemo(() => {
        try {
            const stored = JSON.parse(localStorage.getItem('triageHistory') || '[]');
            return Array.isArray(stored) ? stored.length : 0;
        } catch {
            return 0;
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [refreshTrigger]);

    /**
     * Persist a completed triage to local history and surface it in the main
     * column. Identical persistence logic to the previous Dashboard — the only
     * change here is the surrounding 3-col layout.
     */
    const handleResult = (data) => {
        const result = data.result || data;
        const input = data.input || {};
        const mergedResult = { ...result, patient_id: input.patient_id || result.patient_id };

        setCurrentResult(mergedResult);

        if (data.input) {
            const newRecord = {
                id: Date.now(),
                created_at: new Date().toISOString(),
                patient_id: input.patient_id || null,
                name: input.patient_name || 'Anonymous',
                age: input.age,
                gender: input.gender,
                chief_complaint: input.chief_complaint_text,
                vitals: input.vitals,
                triage_level: result.level,
                triage_color: result.color_code,
                triage_label_en: result.label_en,
                triage_label_ar: result.label_ar,
                triage_reasoning: result.reasoning,
                triage_red_flags: result.red_flags,
                ai_data: result.ai_data,
            };

            try {
                const existing = JSON.parse(localStorage.getItem('triageHistory') || '[]');
                const updated = [newRecord, ...existing];
                localStorage.setItem('triageHistory', JSON.stringify(updated));
                setActivePatientId(newRecord.id);
                setRefreshTrigger((prev) => prev + 1);
            } catch (e) {
                console.error('Storage Error', e);
            }
        }
    };

    const startNewCase = () => {
        setCurrentResult(null);
        setActivePatientId(null);
    };

    return (
        <div className="min-h-screen bg-slate-50 font-sans" dir="ltr">
            <AppHeader queueCount={queueCount} />

            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                {/* 3-col grid — Active Queue rail + main triage workspace.
                    Adapted from ui_kits/clinical-app/index.html. Stacks on
                    narrow viewports so the form is never crushed. */}
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 lg:items-start">
                    <div className="lg:col-span-3 order-2 lg:order-1">
                        <QueuePanel
                            refreshTrigger={refreshTrigger}
                            activeId={activePatientId}
                            onSelect={(p) => setActivePatientId(p?.id ?? null)}
                            onNewCase={startNewCase}
                        />
                    </div>

                    <div className="lg:col-span-9 order-1 lg:order-2 min-w-0">
                        {!currentResult ? (
                            <TriageForm onResult={handleResult} />
                        ) : (
                            <TriageResult result={currentResult} onReset={startNewCase} />
                        )}
                    </div>
                </div>

                <div className="mt-8">
                    <TriageStatsWidget />
                </div>
            </main>

            <footer className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 text-center text-slate-400 text-sm">
                <p>
                    Clinical Decision Support Tool — not a substitute for professional
                    medical judgment.
                </p>
            </footer>
        </div>
    );
}
