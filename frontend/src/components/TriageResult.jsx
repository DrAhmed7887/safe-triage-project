import React from 'react';
import { AlertTriangle, Clock, Activity, ArrowLeft } from 'lucide-react';

export default function TriageResult({ result, onReset }) {
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
            <button onClick={onReset} className="flex items-center text-sm text-slate-500 hover:text-slate-800 transition-colors">
                <ArrowLeft className="w-4 h-4 mr-1" /> Back to Form
            </button>

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

                    {/* Reasoning */}
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
                            {result.ai_data && (
                                <li className="block mt-2 p-3 bg-purple-50 rounded-lg border border-purple-100">
                                    <div className="text-sm font-arabic text-right text-purple-900 mb-2 font-medium">
                                        💡 {result.ai_data.reasoning_ar}
                                    </div>
                                    <div className="text-xs text-purple-700 pt-2 border-t border-purple-100">
                                        <span className="font-bold uppercase">Ask Patient:</span> {result.ai_data.followup_question}
                                        <div className="font-arabic text-right mt-1 opacity-90">{result.ai_data.followup_question_ar}</div>
                                    </div>
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

                <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex justify-between items-center text-xs text-slate-400">
                    <span>Confidence: <span className="font-medium text-slate-600">{result.confidence}</span></span>
                    <span>ID: {Math.random().toString(36).substr(2, 9).toUpperCase()}</span>
                </div>
            </div>
        </div>
    );
}
