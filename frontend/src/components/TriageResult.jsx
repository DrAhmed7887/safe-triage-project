import React, { useCallback, useEffect, useState } from 'react';
import { AlertTriangle, Clock, Activity, ArrowLeft } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import TriageConfirmation from './TriageConfirmation';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function TriageResult({ result, onReset }) {
    const { user } = useAuth();
    const [confirmationStatus, setConfirmationStatus] = useState(null);
    const [confirmationError, setConfirmationError] = useState(null);
    const [pendingRegistered, setPendingRegistered] = useState(false);
    const [toast, setToast] = useState(null);
    const [warningDismissed, setWarningDismissed] = useState(false);

    const clinicianId = user?.username || user?.name || 'unknown';
    const clinicianRoleRaw = (user?.role || '').toLowerCase();
    const clinicianRole = clinicianRoleRaw.includes('supervisor')
        ? 'supervisor'
        : clinicianRoleRaw.includes('doctor') || clinicianRoleRaw.includes('physician')
            ? 'physician'
            : 'nurse';

    useEffect(() => {
        const registerPending = async () => {
            if (!result?.patient_id || pendingRegistered) return;
            try {
                await fetch(`${API_URL}/confirm-triage/request`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        patient_id: result.patient_id,
                        recommended_esi: result.level,
                    }),
                });
                setPendingRegistered(true);
            } catch (e) {
                // Silent fail for now
            }
        };
        registerPending();
    }, [result, pendingRegistered]);

    const handleConfirm = async (level) => {
        setConfirmationError(null);
        setConfirmationStatus('confirming');
        try {
            const res = await fetch(`${API_URL}/confirm-triage`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    patient_id: result.patient_id || 'unknown',
                    recommended_esi: result.level,
                    confirmed_esi: level,
                    clinician_id: clinicianId,
                    clinician_role: clinicianRole,
                    action: 'confirmed',
                }),
            });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err?.detail || 'Confirmation failed');
            }
            setConfirmationStatus('confirmed');
        } catch (e) {
            setConfirmationStatus('error');
            setConfirmationError(e.message);
        }
    };

    const handleOverride = async (newLevel, reason, supervisorPin) => {
        setConfirmationError(null);
        if (newLevel > result.level && clinicianRole !== 'supervisor') {
            setConfirmationStatus('error');
            setConfirmationError('Supervisor required for downgrade.');
            return;
        }
        setConfirmationStatus('overriding');
        try {
            const res = await fetch(`${API_URL}/confirm-triage`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    patient_id: result.patient_id || 'unknown',
                    recommended_esi: result.level,
                    confirmed_esi: newLevel,
                    clinician_id: clinicianId,
                    clinician_role: clinicianRole,
                    action: 'overridden',
                    override_reason: reason,
                    supervisor_pin: supervisorPin,
                }),
            });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err?.detail || 'Override failed');
            }
            setConfirmationStatus('confirmed');
        } catch (e) {
            setConfirmationStatus('error');
            setConfirmationError(e.message);
        }
    };
    const isConfirmed = confirmationStatus === 'confirmed';
    const isError = confirmationStatus === 'error';
    const showConfirmation = confirmationStatus === null || confirmationStatus === 'timeout';
    const handleTimeout = useCallback(() => {
        setConfirmationStatus('timeout');
    }, []);

    const aiFollowup = result?.ai_data?.followup_question || '';
    const aiFollowupAr = result?.ai_data?.followup_question_ar || '';
    const showAiExtra = Boolean(aiFollowup || aiFollowupAr);
    const icd10Code = result?.icd10_code || result?.icd10_coding?.primary_code || '';
    const icd10Desc = result?.icd10_description || result?.icd10_coding?.description_en || '';
    const snomedCode = result?.snomed_code || result?.ai_data?.snomed_code || '';
    const snomedTerm = result?.snomed_term || result?.ai_data?.snomed_term || '';
    const redFlagSummary = Array.isArray(result?.red_flag_summary) ? result.red_flag_summary : [];
    const resourcePlan = Array.isArray(result?.resource_plan) ? result.resource_plan : [];
    const fallbackWorkup = Array.isArray(result?.ai_data?.recommended_workup) ? result.ai_data.recommended_workup : [];
    const insufficientInfoWarning = result?.insufficient_info_warning || null;
    const showInsufficientInfoWarning = Boolean(
        insufficientInfoWarning && (!insufficientInfoWarning.dismissible || !warningDismissed)
    );
    const workupItems = resourcePlan.length
        ? resourcePlan.map((item) => ({
            label_en: item.label_en,
            label_ar: item.label_ar,
            code: item.code || '',
        }))
        : fallbackWorkup.map((item) => ({
            label_en: item,
            label_ar: 'فحص إضافي',
            code: '',
        }));

    useEffect(() => {
        if (!result?.alerts_sent || result.level > 2) {
            setToast(null);
            return;
        }

        const { push, email, queued } = result.alerts_sent || {};
        const levelTag = result.level === 1 ? '🔴 ESI 1' : '🟠 ESI 2';
        let message = '';

        if (queued) {
            message = '⚠️ التنبيه في الانتظار | Alert queued — will send when online';
        } else {
            const pushMsg = push
                ? '✅ تم إرسال الإشعار للطبيب المناوب | Push alert sent to the on-call clinician'
                : '';
            const emailMsg = email
                ? '✅ تم إرسال البريد لطبيب الطوارئ المناوب | Email sent to ER Resident on call'
                : '';
            message = [pushMsg, emailMsg].filter(Boolean).join(' • ');
        }

        setToast({
            levelTag,
            message,
            gahar: '🏥 Designed to Align with GAHAR Safety Requirements | مصمم وفقاً لمتطلبات سلامة الجهار',
            type: queued ? 'warning' : 'success',
        });

        const timer = setTimeout(() => setToast(null), 5000);
        return () => clearTimeout(timer);
    }, [result]);

    useEffect(() => {
        setWarningDismissed(false);
    }, [result?.patient_id, result?.level, result?.insufficient_info_warning]);

    // Determine gradient based on level
    const getGradient = (code) => {
        switch (result.level) {
            case 1: return "from-red-500 to-red-600";
            case 2: return "from-orange-500 to-orange-600";
            case 3: return "from-yellow-400 to-yellow-500";
            case 4: return "from-green-500 to-green-600";
            case 5: return "from-blue-500 to-blue-600";
            default: return "from-slate-500 to-slate-600";
        }
    };

    return (
        <div className="max-w-2xl mx-auto space-y-6">
            {toast && (
                <div
                    className={`fixed top-4 right-4 z-50 w-[320px] pointer-events-none toast-slide-in shadow-lg rounded-lg border px-4 py-3 text-sm ${
                        toast.type === 'warning'
                            ? 'bg-amber-50 border-amber-200 text-amber-900'
                            : 'bg-emerald-50 border-emerald-200 text-emerald-900'
                    }`}
                >
                    <div className="font-semibold mb-1">{toast.levelTag}</div>
                    <div className="text-xs leading-snug">{toast.message}</div>
                    <div className="text-[10px] mt-2 text-slate-600">{toast.gahar}</div>
                </div>
            )}
            <button
                onClick={isConfirmed ? onReset : undefined}
                disabled={!isConfirmed}
                className={`flex items-center text-sm transition-colors ${isConfirmed ? 'text-slate-500 hover:text-slate-800' : 'text-slate-300 cursor-not-allowed'}`}
                title={isConfirmed ? 'Back to Form' : 'Confirm ESI to continue'}
            >
                <ArrowLeft className="w-4 h-4 mr-1" /> Back to Form
            </button>

            {showInsufficientInfoWarning && (
                <div
                    className={`rounded-xl border-2 px-4 py-4 shadow-sm ${
                        insufficientInfoWarning.severity === 'critical'
                            ? 'bg-red-50 border-red-600 animate-pulse'
                            : 'bg-amber-50 border-amber-500'
                    }`}
                >
                    <div className="flex gap-3 items-start">
                        <div className="text-2xl leading-none">
                            {insufficientInfoWarning.severity === 'critical' ? '🚨' : '⚠️'}
                        </div>
                        <div className="flex-1 space-y-2">
                            <p className="text-sm font-semibold text-slate-900">
                                {insufficientInfoWarning.message_en}
                            </p>
                            <p className="text-sm text-slate-800 font-arabic" dir="rtl">
                                {insufficientInfoWarning.message_ar}
                            </p>
                            {Array.isArray(insufficientInfoWarning.ask_patient) && insufficientInfoWarning.ask_patient.length > 0 && (
                                <div className="text-sm text-slate-700">
                                    <div className="font-semibold mb-1">Ask Patient / اسأل المريض:</div>
                                    <ul className="list-disc pl-5 space-y-1">
                                        {insufficientInfoWarning.ask_patient.map((question, idx) => (
                                            <li key={`${question}-${idx}`}>{question}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    </div>
                    {insufficientInfoWarning.dismissible && (
                        <div className="mt-3">
                            <button
                                onClick={() => setWarningDismissed(true)}
                                className="px-3 py-1.5 rounded-md text-xs font-semibold bg-slate-800 text-white hover:bg-slate-700 transition"
                            >
                                I have reviewed this / راجعت
                            </button>
                        </div>
                    )}
                </div>
            )}

            {/* Main Card */}
            <div className="bg-white rounded-2xl shadow-xl overflow-hidden border border-slate-200">
                <div className={`p-8 bg-gradient-to-br ${getGradient(result.color_code)} text-white text-center`}>
                    <h2 className="text-sm uppercase tracking-wider font-semibold opacity-90 mb-2">ESI Triage Level</h2>
                    <h1 className="text-6xl font-black mb-4">{result.level}</h1>
                    <div className="text-3xl font-bold mb-2">{result.label_en}</div>
                    <div className="text-2xl font-arabic">{result.label_ar}</div>
                </div>

                <div className="p-6 space-y-6">
                    {/* Action & Time */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="p-4 bg-slate-50 rounded-lg border border-slate-100">
                            <div className="flex items-center gap-2 text-slate-500 text-xs uppercase font-bold mb-2">
                                <Clock className="w-4 h-4" /> Time to Physician
                            </div>
                            <div className="text-lg font-bold text-slate-800">
                                {result.time_en || result.time_to_physician?.split(' / ')[1] || result.time_to_physician}
                            </div>
                            <div className="text-sm text-slate-600 font-arabic mt-1">
                                {result.time_ar || result.time_to_physician?.split(' / ')[0]}
                            </div>
                        </div>

                        <div className="p-4 bg-slate-50 rounded-lg border border-slate-100">
                            <div className="flex items-center gap-2 text-slate-500 text-xs uppercase font-bold mb-2">
                                <Activity className="w-4 h-4" /> Action
                            </div>
                            <div className="text-base font-medium text-slate-800 leading-snug">
                                {result.action_en || result.recommended_action?.split(' / ')[1] || result.recommended_action}
                            </div>
                            <div className="text-sm text-slate-600 font-arabic mt-1">
                                {result.action_ar || result.recommended_action?.split(' / ')[0]}
                            </div>
                        </div>
                    </div>

                    <div className="p-4 bg-purple-50 border-l-4 border-purple-400 rounded-lg">
                        <h3 className="text-sm font-bold text-purple-900 mb-3">
                            📋 Clinical Coding | الترميز الطبي
                        </h3>
                        <div className="space-y-2 text-sm text-slate-800">
                            <div className="flex flex-wrap items-center gap-2">
                                <span className="text-xs uppercase text-slate-500 font-semibold">ICD-10</span>
                                <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-purple-600 text-white text-xs font-mono">
                                    {icd10Code || '—'}
                                </span>
                                {icd10Desc ? (
                                    <span className="text-slate-700">{icd10Desc}</span>
                                ) : (
                                    <span className="text-slate-400 italic text-xs">Not generated</span>
                                )}
                            </div>
                            {(snomedCode || snomedTerm) && (
                                <div className="flex flex-wrap items-center gap-2">
                                    <span className="text-xs uppercase text-slate-500 font-semibold">SNOMED-CT</span>
                                    <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-teal-600 text-white text-xs font-mono">
                                        {snomedCode || '—'}
                                    </span>
                                    <span className="text-slate-700">{snomedTerm}</span>
                                </div>
                            )}
                        </div>
                        <div className="text-[10px] text-slate-500 mt-2">
                            🏥 Designed to Align with GAHAR Safety Requirements | مصمم وفقاً لمتطلبات سلامة الجهار
                        </div>
                    </div>

                    <div className="p-4 bg-slate-50 border-l-4 border-teal-500 rounded-lg">
                        <h3 className="text-sm font-bold text-slate-900 mb-3">
                            🧪 Recommended Workup | الفحوصات المطلوبة
                        </h3>
                        {workupItems.length > 0 ? (
                            <ul className="space-y-2 text-sm text-slate-700">
                                {workupItems.map((item, idx) => (
                                    <li key={`${item.label_en}-${idx}`} className="flex flex-col gap-1">
                                        <span className="font-medium">{item.label_en}</span>
                                        <span className="font-arabic text-slate-600">{item.label_ar}</span>
                                    </li>
                                ))}
                            </ul>
                        ) : (
                            <div className="text-sm text-slate-600">
                                غير متاح حالياً | Unavailable at this time
                            </div>
                        )}
                        <div className="text-[10px] text-slate-500 mt-2">
                            🏥 Designed to Align with GAHAR Safety Requirements | مصمم وفقاً لمتطلبات سلامة الجهار
                        </div>
                    </div>

                    {showConfirmation && (
                        <TriageConfirmation
                            patientId={result.patient_id}
                            recommendedESI={result.level}
                            category={result.ai_data?.category}
                            redFlags={result.red_flags || []}
                            timeoutSeconds={300}
                            isActive={confirmationStatus === null}
                            onConfirm={handleConfirm}
                            onOverride={handleOverride}
                            onTimeout={handleTimeout}
                        />
                    )}

                    {confirmationStatus && (
                        <div className="text-xs text-slate-600">
                            Status: <span className="font-semibold">{confirmationStatus}</span>
                            {confirmationError && (
                                <span className="text-red-600 ml-2">{confirmationError}</span>
                            )}
                        </div>
                    )}

                    {isConfirmed && (
                        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800 text-sm font-semibold">
                            ✅ Confirmation saved | تم حفظ التأكيد
                        </div>
                    )}

                    {isError && (
                        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                            <div className="font-semibold mb-2">
                                ❌ Confirmation failed | فشل تأكيد الفرز
                            </div>
                            <div className="text-xs mb-3">
                                {confirmationError || 'Network error. Please retry. | خطأ بالشبكة، حاول مرة أخرى.'}
                            </div>
                            <button
                                onClick={() => {
                                    setConfirmationStatus(null);
                                    setConfirmationError(null);
                                }}
                                className="px-3 py-1.5 rounded-md bg-red-600 text-white text-xs font-semibold hover:bg-red-700 transition"
                            >
                                Retry | إعادة المحاولة
                            </button>
                        </div>
                    )}

                    {/* Reasoning */}
                    {redFlagSummary.length > 0 && (
                        <div className="p-4 rounded-lg border border-red-200 bg-[#ffebee]">
                            <h3 className="text-sm font-bold text-red-700 mb-2">🔴 Red Flags Detected | أعلام حمراء</h3>
                            <ul className="list-disc pl-5 text-sm text-red-700 space-y-1">
                                {redFlagSummary.map((flag, idx) => (
                                    <li key={`${flag}-${idx}`}>{flag}</li>
                                ))}
                            </ul>
                        </div>
                    )}
                    <div>
                        <h3 className="text-sm font-bold text-slate-900 mb-3 flex items-center gap-2">
                            Clinical Reasoning
                            {result.isAI && <span className="bg-purple-100 text-purple-700 px-2 py-0.5 rounded text-[10px] uppercase">AI-Generated</span>}
                        </h3>
                        <ul className="space-y-2">
                            {/* Use separate AR/EN if available, otherwise fall back to combined */}
                            {(result.reasoning_en || result.reasoning || []).map((r, i) => (
                                <li key={i} className="flex flex-col gap-1 text-sm text-slate-700 border-l-2 border-blue-500 pl-3 py-1">
                                    <span className="font-medium">
                                        {result.reasoning_en ? result.reasoning_en[i] : (r.includes(' / ') ? r.split(' / ')[1] : r)}
                                    </span>
                                    <span className="text-slate-500 font-arabic">
                                        {result.reasoning_ar ? result.reasoning_ar[i] : (r.includes(' / ') ? r.split(' / ')[0] : '')}
                                    </span>
                                </li>
                            ))}

                            {/* AI Extra Data */}
                            {result.ai_data && showAiExtra && (
                                <li className="block mt-2 p-3 bg-purple-50 rounded-lg border border-purple-100">
                                    {(aiFollowup || aiFollowupAr) && (
                                        <div className="text-xs text-purple-700 pt-2 border-t border-purple-100">
                                            {aiFollowup && (
                                                <div>
                                                    <span className="font-bold uppercase">Ask Patient:</span> {aiFollowup}
                                                </div>
                                            )}
                                            {aiFollowupAr && (
                                                <div className="font-arabic text-right mt-1 opacity-90">{aiFollowupAr}</div>
                                            )}
                                        </div>
                                    )}
                                </li>
                            )}

                            {result.red_flags.length > 0 && (
                                <div className="mt-4 p-3 bg-red-50 border border-red-100 rounded-lg">
                                    <h4 className="flex items-center gap-2 text-red-700 font-bold text-sm mb-2">
                                        <AlertTriangle className="w-4 h-4" /> Red Flags Detected:
                                    </h4>
                                    <ul className="list-disc pl-5 text-sm text-red-700">
                                        {result.red_flags.map((flag, i) => (
                                            <li key={i}>{flag}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </ul>
                    </div>
                </div>

                <div className="px-6 py-3 bg-green-50 border-t border-green-200 text-green-800 text-xs font-semibold text-center">
                    🏥 Designed to Align with GAHAR Safety Requirements | مصمم وفقاً لمتطلبات سلامة الجهار
                </div>

                <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex justify-between items-center text-xs text-slate-400">
                    <span>Confidence: <span className="font-medium text-slate-600">{result.confidence}</span></span>
                    <span>ID: {Math.random().toString(36).substr(2, 9).toUpperCase()}</span>
                </div>
            </div>
        </div>
    );
}
