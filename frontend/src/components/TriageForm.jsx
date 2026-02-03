import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Mic, MicOff, AlertCircle, ChevronRight, Activity, Loader2, AlertTriangle } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function TriageForm({ onResult }) {
    const [formData, setFormData] = useState({
        patient_id: '',
        patient_name: '',
        age: '',
        gender: 'male',
        chief_complaint_text: '',
        vitals: { hr: '', rr: '', spo2: '', temp: '', sbp: '', dbp: '' },
        red_flags: { history_cardiac: false, history_stroke: false, immuno_compromised: false },
        // ===== PHASE 2: Clinical Risk Factors for NEWS2 Compliance =====
        is_copd: false,           // Use SpO2 Scale 2 (target 88-92%)
        on_supplemental_o2: false, // Add +2 NEWS2 points
        is_pregnant: false,        // Enable obstetric emergency detection
        // ===== ESI v5 Fields =====
        pain_scale: null,
        pain_context: '',
        is_immunocompromised: false,
        immunocompromised_reason: '',
        immunizations_complete: null,
        gestational_weeks: null,
        pregnancy_complaint: ''
    });

    const [consciousness, setConsciousness] = useState("A");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [useAI, setUseAI] = useState(false);
    const [isRecording, setIsRecording] = useState(false);
    const [isTranscribing, setIsTranscribing] = useState(false);
    const mediaRecorderRef = useRef(null);
    const audioChunksRef = useRef([]);

    const ageNumber = formData.age ? parseFloat(formData.age) : NaN;
    const isPediatric = !Number.isNaN(ageNumber) && ageNumber < 18;
    const isPregnancyEligible = formData.gender === 'female'
        && !Number.isNaN(ageNumber)
        && ageNumber >= 12
        && ageNumber <= 55;
    const painScaleValue = formData.pain_scale ?? 0;

    // ===== PHASE 2: Reset pregnancy fields when ineligible =====
    useEffect(() => {
        if (!isPregnancyEligible && formData.is_pregnant) {
            setFormData(prev => ({
                ...prev,
                is_pregnant: false,
                gestational_weeks: null,
                pregnancy_complaint: ''
            }));
        }
    }, [formData.gender, formData.age]);

    const handleVitalChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, vitals: { ...prev.vitals, [name]: value ? parseFloat(value) : '' } }));
    };

    // ===== PHASE 2: Handle Clinical Risk Factor checkbox changes =====
    const handleRiskFactorChange = (e) => {
        const { name, checked } = e.target;
        setFormData(prev => ({ ...prev, [name]: checked }));
    };

    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorderRef.current = new MediaRecorder(stream, { mimeType: 'audio/webm' });
            audioChunksRef.current = [];
            mediaRecorderRef.current.ondataavailable = (e) => { if (e.data.size > 0) audioChunksRef.current.push(e.data); };
            mediaRecorderRef.current.onstop = async () => {
                const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
                await transcribeAudio(audioBlob);
                stream.getTracks().forEach(track => track.stop());
            };
            mediaRecorderRef.current.start();
            setIsRecording(true);
        } catch (err) {
            setError('Microphone access denied. Please allow microphone permission.');
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
            setIsRecording(false);
        }
    };

    const transcribeAudio = async (audioBlob) => {
        setIsTranscribing(true);
        try {
            const formDataUpload = new FormData();
            formDataUpload.append('audio', audioBlob, 'recording.webm');
            const response = await axios.post(`${API_URL}/transcribe`, formDataUpload);
            if (response.data.success) {
                setFormData(prev => ({
                    ...prev,
                    chief_complaint_text: prev.chief_complaint_text ? `${prev.chief_complaint_text} ${response.data.transcription}` : response.data.transcription
                }));
            }
        } catch (err) {
            setError('Transcription failed. Ensure backend is running.');
        } finally {
            setIsTranscribing(false);
        }
    };

    // Generate temporary Patient ID if none provided
    const generateTempId = () => {
        const now = new Date();
        const dateStr = now.toISOString().slice(0, 10).replace(/-/g, ''); // YYYYMMDD
        const randomPart = Math.random().toString(36).substring(2, 6).toUpperCase(); // 4 random chars
        return `TEMP-${dateStr}-${randomPart}`;
    };

    // Validation warnings for unusual values
    const validateWithConfirmation = () => {
        const warnings = [];
        const age = parseFloat(formData.age);
        const hr = formData.vitals.hr ? parseInt(formData.vitals.hr) : null;
        const rr = formData.vitals.rr ? parseInt(formData.vitals.rr) : null;
        const spo2 = formData.vitals.spo2 ? parseFloat(formData.vitals.spo2) : null;
        const sbp = formData.vitals.sbp ? parseInt(formData.vitals.sbp) : null;
        const temp = formData.vitals.temp ? parseFloat(formData.vitals.temp) : null;

        // Age validation
        if (age > 120) {
            warnings.push(`⚠️ Age ${age} years is above 120 (oldest recorded human was 122). Did you mean ${Math.floor(age / 10)}?`);
        } else if (age > 100) {
            warnings.push(`⚠️ Age ${age} years - Please confirm this is correct.`);
        } else if (age < 0) {
            warnings.push(`⚠️ Age cannot be negative.`);
        }

        // Heart Rate validation
        if (hr !== null) {
            if (hr > 250) warnings.push(`⚠️ Heart Rate ${hr} bpm is extremely high (>250). Please verify.`);
            if (hr < 20) warnings.push(`⚠️ Heart Rate ${hr} bpm is extremely low (<20). Please verify.`);
        }

        // Respiratory Rate validation
        if (rr !== null) {
            if (rr > 60) warnings.push(`⚠️ Respiratory Rate ${rr}/min is extremely high (>60). Please verify.`);
            if (rr < 4) warnings.push(`⚠️ Respiratory Rate ${rr}/min is extremely low (<4). Please verify.`);
        }

        // SpO2 validation
        if (spo2 !== null) {
            if (spo2 > 100) warnings.push(`⚠️ SpO2 ${spo2}% cannot exceed 100%. Please correct.`);
            if (spo2 < 50) warnings.push(`⚠️ SpO2 ${spo2}% is critically low. Please verify.`);
        }

        // Blood Pressure validation
        if (sbp !== null) {
            if (sbp > 300) warnings.push(`⚠️ Systolic BP ${sbp} mmHg is extremely high (>300). Please verify.`);
            if (sbp < 40) warnings.push(`⚠️ Systolic BP ${sbp} mmHg is extremely low (<40). Please verify.`);
        }

        // Temperature validation  
        if (temp !== null) {
            if (temp > 45) warnings.push(`⚠️ Temperature ${temp}°C is above survivable range (>45°C). Please verify.`);
            if (temp < 25) warnings.push(`⚠️ Temperature ${temp}°C is below survivable range (<25°C). Please verify.`);
        }

        return warnings;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        
        // Check for unusual values and ask for confirmation
        const warnings = validateWithConfirmation();
        if (warnings.length > 0) {
            const confirmMessage = warnings.join('\n\n') + '\n\nDo you want to proceed anyway?';
            if (!window.confirm(confirmMessage)) {
                return; // User cancelled, don't submit
            }
        }

        setLoading(true);
        setError(null);
        try {
            // Auto-generate Patient ID if empty
            const patientId = formData.patient_id?.trim() || generateTempId();
            
            // ===== PHASE 2: Include clinical risk factors in payload =====
            const payload = {
                ...formData,
                patient_id: patientId,
                age: formData.age ? parseFloat(formData.age) : 0,
                vitals: {
                    ...formData.vitals,
                    hr: formData.vitals.hr ? parseInt(formData.vitals.hr) : null,
                    rr: formData.vitals.rr ? parseInt(formData.vitals.rr) : null,
                    sbp: formData.vitals.sbp ? parseInt(formData.vitals.sbp) : null,
                    dbp: formData.vitals.dbp ? parseInt(formData.vitals.dbp) : null,
                    spo2: formData.vitals.spo2 ? parseFloat(formData.vitals.spo2) : null,
                    temp: formData.vitals.temp ? parseFloat(formData.vitals.temp) : null,
                },
                // Clinical Risk Factors (NEWS2 compliance)
                is_copd: formData.is_copd,
                on_supplemental_o2: formData.on_supplemental_o2,
                consciousness: consciousness,
                // ESI v5 fields
                pain_scale: formData.pain_scale,
                pain_context: formData.pain_context || null,
                is_immunocompromised: formData.is_immunocompromised,
                immunocompromised_reason: formData.is_immunocompromised
                    ? (formData.immunocompromised_reason || null)
                    : null,
                immunizations_complete: isPediatric ? formData.immunizations_complete : null,
                is_pregnant: formData.is_pregnant,
                gestational_weeks: formData.is_pregnant ? formData.gestational_weeks : null,
                pregnancy_complaint: formData.is_pregnant
                    ? (formData.pregnancy_complaint || null)
                    : null
            };
            const endpoint = useAI ? `${API_URL}/ai-triage` : `${API_URL}/triage`;
            const res = await axios.post(endpoint, payload);
            onResult({ result: { ...res.data, isAI: useAI }, input: payload });
        } catch (err) {
            setError("Failed to process triage request. Ensure backend is running.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-2xl mx-auto bg-white rounded-xl shadow-lg border border-slate-100 overflow-hidden">
            <div className="p-6 bg-gradient-to-r from-blue-600 to-blue-700 text-white flex justify-between items-center">
                <div>
                    <h2 className="text-lg font-bold">SAFE-Triage AI</h2>
                    <p className="text-blue-100 text-sm">Powered by Gemini AI</p>
                </div>
                <div className="flex items-center gap-2 bg-blue-800/50 p-1.5 rounded-lg border border-blue-500/50">
                    <span className={`text-xs font-bold ${!useAI ? 'text-white' : 'text-blue-300'}`}>Standard</span>
                    <button type="button" onClick={() => setUseAI(!useAI)} className={`w-10 h-5 rounded-full relative transition-colors ${useAI ? 'bg-purple-400' : 'bg-slate-400'}`}>
                        <div className={`w-3.5 h-3.5 bg-white rounded-full absolute top-0.5 transition-all ${useAI ? 'left-[22px]' : 'left-0.5'}`} />
                    </button>
                    <span className={`text-xs font-bold ${useAI ? 'text-white' : 'text-blue-300'}`}>AI</span>
                </div>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-6">
                {error && <div className="p-4 bg-red-50 text-red-700 rounded-lg flex items-center gap-2"><AlertCircle className="w-5 h-5" /> {error}</div>}

                {/* Patient Identification Section */}
                <div className="space-y-4 pb-4 border-b border-slate-200">
                    <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                        <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-blue-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                            <circle cx="12" cy="7" r="4"></circle>
                        </svg>
                        Patient Identification
                    </h3>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">
                                Patient ID / MRN
                                <span className="text-xs text-slate-400 font-normal ml-1">(auto-generated if empty)</span>
                            </label>
                            <input 
                                type="text" 
                                value={formData.patient_id} 
                                onChange={e => setFormData({ ...formData, patient_id: e.target.value })} 
                                className="w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 py-2 px-3 border" 
                                placeholder="Leave empty for auto-ID" 
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">Patient Name</label>
                            <input 
                                type="text" 
                                value={formData.patient_name} 
                                onChange={e => setFormData({ ...formData, patient_name: e.target.value })} 
                                className="w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 py-2 px-3 border" 
                                placeholder="Full Name" 
                                dir="auto"
                            />
                        </div>
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">Age</label>
                        <input required type="number" value={formData.age} onChange={e => setFormData({ ...formData, age: e.target.value })} className="w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 py-2 px-3 border" placeholder="Years" />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">Gender</label>
                        <select value={formData.gender} onChange={e => setFormData({ ...formData, gender: e.target.value })} className="w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 py-2 px-3 border">
                            <option value="male">Male</option>
                            <option value="female">Female</option>
                        </select>
                    </div>
                </div>

                <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1 flex justify-between items-center">
                        <span>Chief Complaint</span>
                        <button type="button" onClick={isRecording ? stopRecording : startRecording} disabled={isTranscribing}
                            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                                isRecording ? 'bg-red-500 text-white animate-pulse' 
                                : isTranscribing ? 'bg-yellow-100 text-yellow-700'
                                : 'bg-green-100 text-green-700 hover:bg-green-200'
                            }`}>
                            {isTranscribing ? <><Loader2 className="w-3.5 h-3.5 animate-spin" />Transcribing...</>
                             : isRecording ? <><MicOff className="w-3.5 h-3.5" />Stop</>
                             : <><Mic className="w-3.5 h-3.5" />Voice Input</>}
                        </button>
                    </label>
                    {isRecording && (
                        <div className="mb-2 p-2 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700 text-sm">
                            <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
                            Recording... Speak now
                        </div>
                    )}
                    <textarea required value={formData.chief_complaint_text} onChange={e => setFormData({ ...formData, chief_complaint_text: e.target.value })}
                        className="w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 py-2 px-3 border min-h-[100px]"
                        placeholder="Describe symptoms or use Voice Input button above..." dir="auto" />
                    <p className="text-xs text-slate-500 mt-1">Voice transcription powered by Gemini AI (Arabic + English)</p>
                </div>

                <div className="space-y-4 border-t pt-4">
                    <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                        <Activity className="w-4 h-4 text-blue-600" /> Vital Signs
                    </h3>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                        <div><label className="block text-xs text-slate-500">HR (bpm)</label><input type="number" name="hr" value={formData.vitals.hr} onChange={handleVitalChange} className="w-full rounded border-slate-300 border py-1.5 px-2 text-sm" placeholder="--" /></div>
                        <div><label className="block text-xs text-slate-500">RR (bpm)</label><input type="number" name="rr" value={formData.vitals.rr} onChange={handleVitalChange} className="w-full rounded border-slate-300 border py-1.5 px-2 text-sm" placeholder="--" /></div>
                        <div><label className="block text-xs text-slate-500">SpO2 (%)</label><input type="number" name="spo2" value={formData.vitals.spo2} onChange={handleVitalChange} className="w-full rounded border-slate-300 border py-1.5 px-2 text-sm" placeholder="--" /></div>
                        <div><label className="block text-xs text-slate-500">Temp (C)</label><input type="number" name="temp" value={formData.vitals.temp} onChange={handleVitalChange} className="w-full rounded border-slate-300 border py-1.5 px-2 text-sm" placeholder="--" /></div>
                        <div><label className="block text-xs text-slate-500">SBP</label><input type="number" name="sbp" value={formData.vitals.sbp} onChange={handleVitalChange} className="w-full rounded border-slate-300 border py-1.5 px-2 text-sm" placeholder="--" /></div>
                        <div><label className="block text-xs text-slate-500">DBP</label><input type="number" name="dbp" value={formData.vitals.dbp} onChange={handleVitalChange} className="w-full rounded border-slate-300 border py-1.5 px-2 text-sm" placeholder="--" /></div>
                    </div>
                    <div className="form-group">
                        <label>Consciousness (ACVPU) | مستوى الوعي</label>
                        <select
                            value={consciousness}
                            onChange={(e) => setConsciousness(e.target.value)}
                        >
                            <option value="A">A - Alert | واعي تماماً</option>
                            <option value="C">C - New Confusion | تشوش ذهني جديد</option>
                            <option value="V">V - Responds to Voice | يستجيب للصوت</option>
                            <option value="P">P - Responds to Pain | يستجيب للألم</option>
                            <option value="U">U - Unresponsive | غير مستجيب</option>
                        </select>
                    </div>
                </div>

                {/* === PAIN ASSESSMENT === */}
                <div className="form-section">
                    <h3>Pain Assessment | تقييم الألم</h3>
                    <div className="form-group">
                        <label>Pain Level (0-10) | مستوى الألم</label>
                        <input
                            type="range"
                            min="0"
                            max="10"
                            value={painScaleValue}
                            onChange={(e) => {
                                const value = parseInt(e.target.value, 10);
                                setFormData(prev => ({ ...prev, pain_scale: Number.isNaN(value) ? null : value }));
                            }}
                        />
                        <span className="pain-value">{painScaleValue}/10</span>
                        <div className="pain-labels">
                            <span>No Pain | لا ألم</span>
                            <span>Worst Pain | أسوأ ألم</span>
                        </div>
                    </div>
                    {painScaleValue > 0 && (
                        <div className="form-group">
                            <label>Pain Type | نوع الألم</label>
                            <select
                                value={formData.pain_context}
                                onChange={(e) => setFormData(prev => ({ ...prev, pain_context: e.target.value }))}
                            >
                                <option value="">Select... | اختر...</option>
                                <option value="chest_pain">Chest Pain | ألم الصدر</option>
                                <option value="abdominal_pain">Abdominal Pain | ألم البطن</option>
                                <option value="renal_colic">Renal Colic | مغص كلوي</option>
                                <option value="sickle_cell_crisis">Sickle Cell Crisis | أزمة أنيميا منجلية</option>
                                <option value="cancer_pain">Cancer Pain | ألم السرطان</option>
                                <option value="orthopedic">Orthopedic/Injury | عظام/إصابة</option>
                                <option value="headache">Headache | صداع</option>
                                <option value="other">Other | أخرى</option>
                            </select>
                        </div>
                    )}
                </div>

                {/* === IMMUNOCOMPROMISED STATUS === */}
                <div className="form-section">
                    <h3>Immune Status | حالة المناعة</h3>
                    <div className="form-group checkbox-group">
                        <label>
                            <input
                                type="checkbox"
                                checked={formData.is_immunocompromised}
                                onChange={(e) => {
                                    const checked = e.target.checked;
                                    setFormData(prev => ({
                                        ...prev,
                                        is_immunocompromised: checked,
                                        immunocompromised_reason: checked ? prev.immunocompromised_reason : ''
                                    }));
                                }}
                            />
                            Immunocompromised Patient | مريض ضعيف المناعة
                        </label>
                    </div>
                    {formData.is_immunocompromised && (
                        <div className="form-group">
                            <label>Reason | السبب</label>
                            <select
                                value={formData.immunocompromised_reason}
                                onChange={(e) => setFormData(prev => ({ ...prev, immunocompromised_reason: e.target.value }))}
                            >
                                <option value="">Select... | اختر...</option>
                                <option value="chemotherapy">Chemotherapy | علاج كيماوي</option>
                                <option value="transplant">Organ Transplant | زراعة أعضاء</option>
                                <option value="hiv_aids">HIV/AIDS | فيروس نقص المناعة</option>
                                <option value="chronic_steroids">Chronic Steroids | كورتيزون مزمن</option>
                                <option value="biologics">Biologics/Immunotherapy | علاج بيولوجي</option>
                                <option value="congenital">Congenital Immunodeficiency | نقص مناعة خلقي</option>
                                <option value="other">Other | أخرى</option>
                            </select>
                        </div>
                    )}
                </div>

                {/* === PEDIATRIC IMMUNIZATIONS === */}
                {isPediatric && (
                    <div className="form-section">
                        <h3>Pediatric | الأطفال</h3>
                        <div className="form-group">
                            <label>Immunizations | التطعيمات</label>
                            <select
                                value={
                                    formData.immunizations_complete === null
                                        || formData.immunizations_complete === undefined
                                        ? ""
                                        : (formData.immunizations_complete ? "true" : "false")
                                }
                                onChange={(e) => {
                                    const value = e.target.value;
                                    setFormData(prev => ({
                                        ...prev,
                                        immunizations_complete:
                                            value === "" ? null : value === "true"
                                    }));
                                }}
                            >
                                <option value="">Unknown | غير معروف</option>
                                <option value="true">Up to Date | مكتملة</option>
                                <option value="false">Not Complete | غير مكتملة</option>
                            </select>
                        </div>
                    </div>
                )}

                {/* === PREGNANCY STATUS === */}
                {isPregnancyEligible && (
                    <div className="form-section">
                        <h3>Pregnancy Status | حالة الحمل</h3>
                        <div className="form-group checkbox-group">
                            <label>
                                <input
                                    type="checkbox"
                                    checked={formData.is_pregnant}
                                    onChange={(e) => {
                                        const checked = e.target.checked;
                                        setFormData(prev => ({
                                            ...prev,
                                            is_pregnant: checked,
                                            gestational_weeks: checked ? prev.gestational_weeks : null,
                                            pregnancy_complaint: checked ? prev.pregnancy_complaint : ''
                                        }));
                                    }}
                                />
                                Patient is Pregnant | المريضة حامل
                            </label>
                        </div>
                        {formData.is_pregnant && (
                            <>
                                <div className="form-group">
                                    <label>Weeks Pregnant | أسابيع الحمل</label>
                                    <input
                                        type="number"
                                        min="1"
                                        max="42"
                                        value={formData.gestational_weeks ?? ''}
                                        onChange={(e) => {
                                            const value = e.target.value ? parseInt(e.target.value, 10) : null;
                                            setFormData(prev => ({ ...prev, gestational_weeks: value }));
                                        }}
                                        placeholder="1-42"
                                    />
                                </div>
                                <div className="form-group">
                                    <label>Pregnancy Complaint | شكوى متعلقة بالحمل</label>
                                    <select
                                        value={formData.pregnancy_complaint}
                                        onChange={(e) => setFormData(prev => ({ ...prev, pregnancy_complaint: e.target.value }))}
                                    >
                                        <option value="">None | لا يوجد</option>
                                        <option value="vaginal_bleeding">Vaginal Bleeding | نزيف مهبلي</option>
                                        <option value="abdominal_pain">Abdominal Pain | ألم بطن</option>
                                        <option value="contractions">Contractions | انقباضات/طلق</option>
                                        <option value="decreased_fetal_movement">Decreased Fetal Movement | قلة حركة الجنين</option>
                                        <option value="leaking_fluid">Leaking Fluid | نزول ماء</option>
                                        <option value="headache_visual_changes">Headache + Vision Changes | صداع + تغير بالنظر</option>
                                        <option value="swelling">Swelling | تورم</option>
                                    </select>
                                </div>
                            </>
                        )}
                    </div>
                )}

                {/* ===== PHASE 2: Clinical Risk Factors & NEWS2 Section ===== */}
                <div className="space-y-4 border-t pt-4">
                    <div className="p-4 bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-lg">
                        <h3 className="text-sm font-semibold text-amber-800 flex items-center gap-2 mb-3">
                            <AlertTriangle className="w-4 h-4 text-amber-600" />
                            ⚠️ Clinical Risk Factors & NEWS2
                        </h3>
                        <p className="text-xs text-amber-700 mb-4">
                            These factors affect NEWS2 scoring and triage level. Please check all that apply.
                        </p>
                        
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            {/* COPD / CO2 Retainer */}
                            <label className="flex items-start gap-3 p-3 bg-white rounded-lg border border-amber-100 hover:border-amber-300 cursor-pointer transition-colors">
                                <input 
                                    type="checkbox" 
                                    name="is_copd"
                                    checked={formData.is_copd}
                                    onChange={handleRiskFactorChange}
                                    className="mt-0.5 w-4 h-4 text-amber-600 border-slate-300 rounded focus:ring-amber-500"
                                />
                                <div>
                                    <span className="text-sm font-medium text-slate-700 block">
                                        COPD / CO₂ Retainer
                                    </span>
                                    <span className="text-xs text-slate-500">
                                        Uses SpO₂ Scale 2 (target 88-92%)
                                    </span>
                                </div>
                            </label>

                            {/* On Supplemental Oxygen */}
                            <label className="flex items-start gap-3 p-3 bg-white rounded-lg border border-amber-100 hover:border-amber-300 cursor-pointer transition-colors">
                                <input 
                                    type="checkbox" 
                                    name="on_supplemental_o2"
                                    checked={formData.on_supplemental_o2}
                                    onChange={handleRiskFactorChange}
                                    className="mt-0.5 w-4 h-4 text-amber-600 border-slate-300 rounded focus:ring-amber-500"
                                />
                                <div>
                                    <span className="text-sm font-medium text-slate-700 block">
                                        On Supplemental O₂
                                    </span>
                                    <span className="text-xs text-slate-500">
                                        Adds +2 points to NEWS2 score
                                    </span>
                                </div>
                            </label>

                        </div>

                        {/* Active Risk Factor Indicators */}
                        {(formData.is_copd || formData.on_supplemental_o2) && (
                            <div className="mt-4 p-3 bg-amber-100 rounded-lg border border-amber-300">
                                <p className="text-xs font-semibold text-amber-800 mb-2">Active Risk Factors:</p>
                                <div className="flex flex-wrap gap-2">
                                    {formData.is_copd && (
                                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-amber-200 text-amber-800">
                                            COPD (Scale 2)
                                        </span>
                                    )}
                                    {formData.on_supplemental_o2 && (
                                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-200 text-blue-800">
                                            O₂ Supplementation (+2)
                                        </span>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
                {/* ===== END PHASE 2 ===== */}

                <button type="submit" disabled={loading} className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-4 rounded-lg flex items-center justify-center gap-2 disabled:opacity-70">
                    {loading ? 'Processing...' : 'Run Triage Assessment'}
                    {!loading && <ChevronRight className="w-5 h-5" />}
                </button>
            </form>
        </div>
    );
}
