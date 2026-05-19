import React, { useEffect, useState } from 'react';
import HospitalShell from '../../components/HospitalLite/HospitalShell';
import ClinicianGate from '../../components/HospitalLite/ClinicianGate';
import LiteTriageForm from '../../components/HospitalLite/LiteTriageForm';
import SuggestedTriage from '../../components/HospitalLite/SuggestedTriage';
import QueueRail from '../../components/HospitalLite/QueueRail';
import HandoffRecord from '../../components/HospitalLite/HandoffRecord';
import {
    getClinician, clearClinician, addQueueEntry, getQueue, getQueueEntry,
} from '../../lib/hospitalLite';
import { getTriageSuggestion } from '../../lib/triageClient';
import { getLang, setLang as persistLang } from '../../lib/i18n';

const STAGE = { ENTRY: 'entry', REVIEW: 'review', HANDOFF: 'handoff' };

/**
 * HospitalLitePage — single-page workflow for the hospital pilot.
 *
 * Stages:
 *   ENTRY   → LiteTriageForm
 *   REVIEW  → SuggestedTriage (clinician must confirm or override+reason)
 *   HANDOFF → printable + queueable handoff
 *
 * Side rail: live queue, supports re-opening an existing entry.
 */
export default function HospitalLitePage() {
    const [lang, setLangState] = useState(getLang());
    const [clinician, setClinicianState] = useState(() => getClinician());

    const [stage, setStage] = useState(STAGE.ENTRY);
    const [pendingInput, setPendingInput] = useState(null);
    const [suggestion, setSuggestion] = useState(null);
    const [engineError, setEngineError] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [activeEntry, setActiveEntry] = useState(null);
    const [queue, setQueueState] = useState(() => getQueue());

    // Apply lang dir on first paint and whenever it changes.
    useEffect(() => {
        persistLang(lang);
    }, [lang]);

    const refreshQueue = () => setQueueState(getQueue());

    const handleFormSubmit = async (input) => {
        setIsLoading(true);
        setEngineError(null);
        try {
            // Canonical Python engine first; offline JS engine only on failure.
            const { suggestion: result, source, error } = await getTriageSuggestion(input);
            setPendingInput(input);
            setSuggestion(result);
            setEngineError(source === 'offline_js_fallback' ? (error || { kind: 'unknown' }) : null);
            setStage(STAGE.REVIEW);
            if (typeof window !== 'undefined') window.scrollTo({ top: 0, behavior: 'smooth' });
        } finally {
            setIsLoading(false);
        }
    };

    const handleDecision = ({ action, final_level, reason }) => {
        if (!pendingInput || !suggestion) return;

        const engineSource = suggestion.engine_source || 'unknown';

        const baseAudit = [
            {
                at: new Date().toISOString(),
                action: 'suggested',
                level: suggestion.level,
                by: 'system',
                role: 'engine',
                engine_source: engineSource,
                fallback_error: engineError ? engineError.kind : null,
                reason: null,
            },
            {
                at: new Date().toISOString(),
                action,
                level: final_level,
                by: clinician?.name || 'unknown',
                role: clinician?.role || 'nurse',
                reason: reason || null,
            },
        ];

        const entry = addQueueEntry({
            patient_id: pendingInput.patient_id,
            patient_name: pendingInput.patient_name,
            age: pendingInput.age,
            gender: pendingInput.gender,
            chief_complaint: pendingInput.chief_complaint_text,
            vitals: pendingInput.vitals,
            consciousness: pendingInput.consciousness,
            pain_scale: pendingInput.pain_scale,
            is_pregnant: pendingInput.is_pregnant,
            is_copd: pendingInput.is_copd,
            on_supplemental_o2: pendingInput.on_supplemental_o2,
            suggestion,
            suggested_level: suggestion.level,
            engine_source: engineSource,
            fallback_error: engineError || null,
            final_level,
            action,
            override_reason: reason || null,
            clinician: clinician ? { name: clinician.name, role: clinician.role } : null,
            audit: baseAudit,
        });

        refreshQueue();
        setActiveEntry(entry);
        setStage(STAGE.HANDOFF);
    };

    const startNewCase = () => {
        setPendingInput(null);
        setSuggestion(null);
        setEngineError(null);
        setActiveEntry(null);
        setStage(STAGE.ENTRY);
    };

    const handleSelectFromQueue = (p) => {
        const fresh = getQueueEntry(p.id);
        if (!fresh) return;
        setActiveEntry(fresh);
        setStage(STAGE.HANDOFF);
        if (typeof window !== 'undefined') window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    const signOut = () => {
        clearClinician();
        setClinicianState(null);
    };

    if (!clinician) {
        return (
            <HospitalShell lang={lang} onLangChange={setLangState} clinician={null} onSignOut={signOut}>
                <ClinicianGate lang={lang} onSignedIn={setClinicianState} />
            </HospitalShell>
        );
    }

    return (
        <HospitalShell lang={lang} onLangChange={setLangState} clinician={clinician} onSignOut={signOut}>
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 lg:items-start">
                <div className="lg:col-span-3 order-2 lg:order-1">
                    <QueueRail
                        lang={lang}
                        items={queue}
                        activeId={activeEntry?.id || null}
                        onSelect={handleSelectFromQueue}
                        onNewCase={startNewCase}
                    />
                </div>

                <div className="lg:col-span-9 order-1 lg:order-2 min-w-0 grid gap-4">
                    {stage === STAGE.ENTRY && (
                        <LiteTriageForm lang={lang} onSubmit={handleFormSubmit} loading={isLoading} />
                    )}
                    {stage === STAGE.REVIEW && (
                        <SuggestedTriage
                            lang={lang}
                            suggestion={suggestion}
                            engineError={engineError}
                            onDecision={handleDecision}
                        />
                    )}
                    {stage === STAGE.HANDOFF && (
                        <HandoffRecord lang={lang} entry={activeEntry} onNew={startNewCase} />
                    )}
                </div>
            </div>
        </HospitalShell>
    );
}
