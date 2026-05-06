import React, { useState } from 'react';
import TriageForm from '../components/TriageForm';
import TriageResult from '../components/TriageResult';
import PatientList from '../components/PatientList';
import TriageStatsWidget from '../components/TriageStatsWidget';
import NotificationBell from '../components/NotificationBell';
import { Activity, ClipboardList, LogOut, BarChart3 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';

export default function Dashboard() {
    const [currentResult, setCurrentResult] = useState(null);
    const [refreshTrigger, setRefreshTrigger] = useState(0);
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const normalizedRole = (user?.role || '').toString().toLowerCase();
    const isSupervisor = normalizedRole === 'supervisor' || normalizedRole === 'admin';

    // Handle data from TriageForm (contains { result, input })
    const handleResult = (data) => {
        // Determine structure
        const result = data.result || data;
        const input = data.input || {};
        const mergedResult = { ...result, patient_id: input.patient_id || result.patient_id };

        // 1. Update UI
        setCurrentResult(mergedResult);

        // 2. Save to LocalStorage if input data is present
        if (data.input) {
            const newRecord = {
                id: Date.now(),
                created_at: new Date().toISOString(),
                patient_id: input.patient_id || null,
                name: input.patient_name || "Anonymous",
                age: input.age,
                gender: input.gender,
                chief_complaint: input.chief_complaint_text, // Ensure mapping matches TriageForm state
                vitals: input.vitals,
                triage_level: result.level,
                triage_color: result.color_code,
                triage_label_en: result.label_en,
                triage_label_ar: result.label_ar,
                triage_reasoning: result.reasoning,
                triage_red_flags: result.red_flags,
                ai_data: result.ai_data
            };

            try {
                const existing = JSON.parse(localStorage.getItem('triageHistory') || '[]');
                const updated = [newRecord, ...existing];
                localStorage.setItem('triageHistory', JSON.stringify(updated));
                // Trigger Sidebar Refresh
                setRefreshTrigger(prev => prev + 1);
            } catch (e) {
                console.error("Storage Error", e);
            }
        }
    };

    return (
        <div className="min-h-screen bg-slate-50 font-sans" dir="ltr">
            <header className="bg-white shadow-sm border-b border-slate-200 sticky top-0 z-10">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 min-h-16 flex flex-wrap items-center justify-between gap-y-2 gap-x-4 py-2">
                    <div className="flex items-center gap-3 min-w-0">
                        <div className="bg-teal-600 p-2 rounded-xl shadow-sm shadow-teal-600/20">
                            <Activity className="w-6 h-6 text-white" aria-hidden="true" />
                        </div>
                        <div className="min-w-0">
                            <h1 className="text-base sm:text-lg font-bold text-slate-900 leading-tight tracking-tight">
                                SAFE-Triage AI
                            </h1>
                            <p className="text-[11px] text-slate-500 leading-tight flex items-center gap-1.5 flex-wrap">
                                <span>ED · {user?.name ? `Dr. ${user.name}` : 'Clinician'}</span>
                                <span className="text-slate-300" aria-hidden="true">|</span>
                                <span dir="rtl" className="font-arabic">قسم الطوارئ</span>
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
                        <NotificationBell />
                        <button
                            onClick={() => navigate('/analytics/dashboard')}
                            disabled={!isSupervisor}
                            className={`text-sm font-medium px-3 py-1.5 rounded-md flex items-center gap-1 transition-colors ${
                                isSupervisor
                                    ? 'text-white bg-[#1a5f7a] hover:bg-[#164d63]'
                                    : 'text-slate-500 bg-slate-200 cursor-not-allowed'
                            }`}
                            title={isSupervisor ? 'View analytics dashboard' : 'Supervisor role required'}
                            aria-label={isSupervisor ? 'View analytics dashboard' : 'Supervisor role required to view analytics'}
                        >
                            <BarChart3 className="w-4 h-4" aria-hidden="true" />
                            <span className="hidden sm:inline">View Analytics Dashboard | عرض لوحة التحليلات</span>
                            <span className="sm:hidden">Analytics</span>
                        </button>
                        <button
                            onClick={() => window.location.reload()}
                            className="text-sm font-medium text-teal-700 hover:text-teal-800 flex items-center gap-1"
                            aria-label="Start new patient"
                        >
                            <ClipboardList className="w-4 h-4" aria-hidden="true" />
                            New Patient
                        </button>
                        <button
                            onClick={logout}
                            className="text-sm font-medium text-slate-500 hover:text-red-600 flex items-center gap-1 ml-2"
                            title="Sign Out"
                            aria-label="Sign out"
                        >
                            <LogOut className="w-4 h-4" aria-hidden="true" />
                            Sign Out
                        </button>
                    </div>
                </div>
                {!isSupervisor && (
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-2 text-xs text-slate-500">
                        Analytics access restricted to supervisors | الوصول إلى التحليلات متاح للمشرفين فقط
                    </div>
                )}
            </header>

            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    {/* Left Column: Triage Interface */}
                    <div className="lg:col-span-2">
                        {!currentResult ? (
                            <TriageForm onResult={handleResult} />
                        ) : (
                            <TriageResult result={currentResult} onReset={() => setCurrentResult(null)} />
                        )}
                    </div>

                    {/* Right Column: Live Dashboard */}
                    <div className="lg:col-span-1">
                        <PatientList refreshTrigger={refreshTrigger} />
                    </div>
                </div>

                {/* Statistics Dashboard */}
                <div className="mt-8">
                    <TriageStatsWidget />
                </div>
            </main>

            <footer className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 text-center text-slate-400 text-sm">
                <p>Clinical Decision Support Tool - Not a substitute for professional medical judgment.</p>
            </footer>
        </div>
    );
}
