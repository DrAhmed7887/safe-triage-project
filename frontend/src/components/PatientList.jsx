import React, { useEffect, useState } from 'react';
import { Users, RotateCw, AlertTriangle, Eye, X, Activity, Download, Trash2 } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';

export default function PatientList({ refreshTrigger = 0 }) {
    const [patients, setPatients] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedPatient, setSelectedPatient] = useState(null);
    const [showAll, setShowAll] = useState(false);

    const [searchTerm, setSearchTerm] = useState('');

    const loadPatients = () => {
        setLoading(true);
        try {
            let stored = JSON.parse(localStorage.getItem('triageHistory') || '[]');

            // Filter by search term
            if (searchTerm) {
                const lowerTerm = searchTerm.toLowerCase();
                stored = stored.filter(p =>
                    (p.name && p.name.toLowerCase().includes(lowerTerm)) ||
                    (p.patient_id && p.patient_id.toLowerCase().includes(lowerTerm)) ||
                    (p.id && String(p.id).toLowerCase().includes(lowerTerm))
                );
            }

            // If showAll is false, limit to 10 (unless searching)
            setPatients((showAll || searchTerm) ? stored : stored.slice(0, 10));
        } catch (err) {
            console.error("Failed to load history", err);
        } finally {
            setLoading(false);
        }
    };

    const clearHistory = () => {
        if (window.confirm("Are you sure you want to clear all history? This cannot be undone.")) {
            localStorage.removeItem('triageHistory');
            loadPatients();
        }
    };

    const exportCSV = () => {
        const stored = JSON.parse(localStorage.getItem('triageHistory') || '[]');
        if (!stored.length) return;

        // Simple flatten for CSV
        const headers = ["RecordID", "PatientID", "Name", "Date", "Age", "Gender", "Complaint", "Level", "Label", "RedFlags"];
        const rows = stored.map(p => [
            p.id,
            `"${p.patient_id || ''}"`,
            `"${p.name || 'Anonymous'}"`,
            p.created_at,
            p.age,
            p.gender,
            `"${(p.chief_complaint || '').replace(/"/g, '""')}"`, // Escape quotes
            p.triage_level,
            p.triage_label_en,
            `"${(p.triage_red_flags || []).join(';')}"`
        ]);

        const csvContent = [
            headers.join(','),
            ...rows.map(r => r.join(','))
        ].join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `triage_export_${new Date().toISOString()}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    useEffect(() => {
        loadPatients();
    }, [refreshTrigger, showAll, searchTerm]);

    const getLevelColor = (level) => {
        switch (level) {
            case 1: return "bg-red-100 text-red-800 border-red-200";
            case 2: return "bg-orange-100 text-orange-800 border-orange-200";
            case 3: return "bg-yellow-100 text-yellow-800 border-yellow-200";
            case 4: return "bg-green-100 text-green-800 border-green-200";
            case 5: return "bg-blue-100 text-blue-800 border-blue-200";
            default: return "bg-slate-100 text-slate-800";
        }
    };

    return (
        <>
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-full max-h-[800px]">
                <div className="p-4 border-b border-slate-100 bg-slate-50 flex flex-col gap-3 sticky top-0 z-10">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <h3 className="font-semibold text-slate-700 flex items-center gap-2">
                                <Users className="w-4 h-4" /> {showAll ? 'All History' : 'Recent'}
                            </h3>
                            <button onClick={loadPatients} className="text-slate-400 hover:text-blue-600 transition-colors" title="Reload">
                                <RotateCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-blue-600' : ''}`} />
                            </button>
                        </div>
                        <div className="flex gap-2">
                            <button onClick={exportCSV} className="text-[10px] bg-blue-50 text-blue-600 px-2 py-1 rounded hover:bg-blue-100 flex items-center gap-1 border border-blue-100" title="Download CSV">
                                <Download className="w-3 h-3" /> Export
                            </button>
                            <button onClick={clearHistory} className="text-[10px] bg-red-50 text-red-600 px-2 py-1 rounded hover:bg-red-100 flex items-center gap-1 border border-red-100" title="Clear All">
                                <Trash2 className="w-3 h-3" /> Clear
                            </button>
                        </div>
                    </div>

                    {/* Search Bar */}
                    <div>
                        <input
                            type="text"
                            placeholder="Search by Name or Patient ID (MRN)..."
                            className="w-full text-xs p-2 rounded border border-slate-200 focus:border-blue-500 focus:outline-none"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                        />
                    </div>

                    <div className="flex justify-end">
                        <button
                            onClick={() => setShowAll(!showAll)}
                            className="text-xs text-blue-600 hover:text-blue-800 font-medium underline"
                        >
                            {showAll ? 'Show Recent' : 'View All History'}
                        </button>
                    </div>
                </div>

                <div className="overflow-y-auto flex-1 divide-y divide-slate-100">
                    {loading && <div className="p-4 text-center text-sm text-slate-500">Loading...</div>}

                    {!loading && patients.length === 0 && (
                        <div className="p-8 text-center text-slate-400 text-sm">No history found.</div>
                    )}

                    {patients.map(patient => (
                        <div
                            key={patient.id}
                            onClick={() => setSelectedPatient(patient)}
                            className="p-4 hover:bg-slate-50 cursor-pointer transition-colors flex items-center justify-between group"
                        >
                            <div className="space-y-1">
                                <div className="flex items-center gap-2">
                                    <span className={`px-2 py-0.5 rounded text-xs font-bold uppercase border ${getLevelColor(patient.triage_level)}`}>
                                        {patient.triage_level}
                                    </span>
                                    <div className="flex flex-col">
                                        <span className="text-sm font-bold text-slate-900">
                                            {patient.name || 'Anonymous'}
                                        </span>
                                        {patient.patient_id && (
                                            <span className={`text-[10px] font-mono px-1 rounded ${
                                                patient.patient_id.startsWith('TEMP-') 
                                                    ? 'text-amber-600 bg-amber-50' 
                                                    : 'text-blue-600 bg-blue-50'
                                            }`}>
                                                {patient.patient_id}
                                            </span>
                                        )}
                                    </div>
                                </div>
                                <div className="flex items-center gap-2 text-xs text-slate-500">
                                    <span>{patient.gender === 'male' ? 'M' : 'F'} / {Math.round(patient.age)}y</span>
                                </div>
                                <p className="text-xs text-slate-500 line-clamp-1 max-w-[180px]" title={patient.chief_complaint}>
                                    {patient.chief_complaint}
                                </p>
                            </div>
                            <div className="text-right">
                                <div className="text-xs font-bold text-slate-700">
                                    {new Date(patient.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                </div>
                                {patient.triage_red_flags && patient.triage_red_flags.length > 0 ? (
                                    <div className="flex items-center justify-end gap-1 text-[10px] text-red-600 font-medium">
                                        <AlertTriangle className="w-3 h-3" /> Warning
                                    </div>
                                ) : (
                                    <div className="opacity-0 group-hover:opacity-100 transition-opacity text-[10px] text-blue-500 font-medium flex items-center justify-end gap-1">
                                        View <Eye className="w-3 h-3" />
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Detail Modal */}
            <AnimatePresence>
                {selectedPatient && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm" onClick={() => setSelectedPatient(null)}>
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.95 }}
                            className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden"
                            onClick={e => e.stopPropagation()}
                        >
                            <div className={`p-6 text-white bg-gradient-to-r ${selectedPatient.triage_level === 1 ? 'from-red-600 to-red-700' : selectedPatient.triage_level === 2 ? 'from-orange-500 to-orange-600' : selectedPatient.triage_level === 3 ? 'from-yellow-500 to-yellow-600' : selectedPatient.triage_level === 4 ? 'from-green-500 to-green-600' : 'from-blue-500 to-blue-600'}`}>
                                <div className="flex justify-between items-start mb-4">
                                    <div>
                                        <h2 className="text-xl font-bold">{selectedPatient.name || 'Anonymous'}</h2>
                                        {selectedPatient.patient_id && (
                                            <p className={`text-sm font-mono inline-block px-2 py-0.5 rounded mt-1 ${
                                                selectedPatient.patient_id.startsWith('TEMP-')
                                                    ? 'bg-amber-500/30 text-amber-100'
                                                    : 'bg-white/20 text-white/90'
                                            }`}>
                                                {selectedPatient.patient_id.startsWith('TEMP-') ? '⏱ ' : 'MRN: '}
                                                {selectedPatient.patient_id}
                                            </p>
                                        )}
                                    </div>
                                    <button onClick={() => setSelectedPatient(null)} className="p-1 hover:bg-white/20 rounded-full transition-colors">
                                        <X className="w-6 h-6" />
                                    </button>
                                </div>
                                <div className="flex gap-4 text-sm font-medium">
                                    <div className="bg-white/20 px-3 py-1 rounded-lg backdrop-blur-md">
                                        {selectedPatient.gender === "male" ? "Male" : "Female"}, {selectedPatient.age} Years
                                    </div>
                                    <div className="bg-white/20 px-3 py-1 rounded-lg backdrop-blur-md">
                                        {new Date(selectedPatient.created_at).toLocaleString()}
                                    </div>
                                </div>
                            </div>

                            <div className="p-6 space-y-6 max-h-[70vh] overflow-y-auto">
                                {/* Complaint */}
                                <section>
                                    <h3 className="text-xs font-bold uppercase text-slate-500 mb-2">Chief Complaint</h3>
                                    <p className="text-slate-900 bg-slate-50 p-3 rounded-lg border border-slate-100">
                                        {selectedPatient.chief_complaint}
                                    </p>
                                </section>

                                {/* Vitals */}
                                <section>
                                    <h3 className="text-xs font-bold uppercase text-slate-500 mb-2 flex items-center gap-1">
                                        <Activity className="w-3 h-3" /> Vitals Recorded
                                    </h3>
                                    <div className="grid grid-cols-3 gap-3">
                                        {Object.entries(selectedPatient.vitals || {}).map(([key, val]) => (
                                            val && (
                                                <div key={key} className="bg-slate-50 p-2 rounded border border-slate-100 text-center">
                                                    <div className="text-[10px] text-slate-500 uppercase">{key}</div>
                                                    <div className="font-mono font-bold text-slate-800">{val}</div>
                                                </div>
                                            )
                                        ))}
                                    </div>
                                </section>

                                {/* Triage Decision */}
                                <section>
                                    <h3 className="text-xs font-bold uppercase text-slate-500 mb-2">Triage Analysis</h3>
                                    <div className="space-y-3">
                                        <div className="flex items-center gap-2">
                                            <div className={`w-3 h-3 rounded-full ${selectedPatient.triage_level === 1 ? 'bg-red-500' : selectedPatient.triage_level === 2 ? 'bg-orange-500' : selectedPatient.triage_level === 3 ? 'bg-yellow-400' : selectedPatient.triage_level === 4 ? 'bg-green-500' : 'bg-blue-500'}`} />
                                            <span className="font-bold text-slate-900">{selectedPatient.triage_label_en} / {selectedPatient.triage_label_ar}</span>
                                        </div>

                                        <div className="space-y-2">
                                            {selectedPatient.triage_reasoning?.map((r, i) => (
                                                <div key={i} className="flex items-start gap-2 text-sm text-slate-600">
                                                    <span className="mt-1.5 w-1 h-1 rounded-full bg-slate-400 shrink-0" />
                                                    {r}
                                                </div>
                                            ))}
                                        </div>

                                        {/* AI Extra Data */}
                                        {selectedPatient.ai_data && (
                                            <div className="mt-2 block p-3 bg-purple-50 rounded-lg border border-purple-100 text-xs">
                                                <div className="font-bold text-purple-700 mb-1">AI Insights:</div>
                                                <div className="font-arabic text-right text-purple-900 mb-1">{selectedPatient.ai_data.reasoning_ar}</div>
                                                <div className="text-purple-600">Q: {selectedPatient.ai_data.followup_question}</div>
                                            </div>
                                        )}

                                        {selectedPatient.triage_red_flags?.length > 0 && (
                                            <div className="mt-2 text-xs text-red-600 bg-red-50 p-2 rounded border border-red-100">
                                                <span className="font-bold">🚩 Red Flags:</span> {selectedPatient.triage_red_flags.join(", ")}
                                            </div>
                                        )}
                                    </div>
                                </section>
                            </div>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>
        </>
    );
}
