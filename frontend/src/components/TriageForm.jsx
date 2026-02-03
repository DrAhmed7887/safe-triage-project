/**
 * TriageForm.jsx - SAFE-Triage Main Input Form
 * 
 * This component handles patient data entry for the AI-powered triage system.
 * Features:
 * - Bilingual support (English/Arabic)
 * - Voice input with Gemini AI transcription
 * - NEWS2-compliant vital signs collection
 * - ESI v5 pain assessment
 * - Clinical risk factors for accurate triage
 * - Pregnancy and pediatric special assessments
 * 
 * @version 2.2
 * @author SAFE-Triage Avengers Team
 */

import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { 
    Mic, MicOff, AlertCircle, ChevronRight, Loader2, 
    Heart, Thermometer, Wind, Droplets, Activity, 
    Brain, Baby, Shield, Stethoscope 
} from 'lucide-react';

// Import reusable UI components
import { 
    SectionCard, 
    InputField, 
    SelectField, 
    VitalInput, 
    CheckboxCard 
} from './ui/FormComponents';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function TriageForm({ onResult }) {
    // ==================== STATE MANAGEMENT ====================
    
    /**
     * Main form state - Contains all patient data fields
     * Organized by category for clarity
     */
    const [formData, setFormData] = useState({
        // Patient Demographics
        patient_id: '',
        patient_name: '',
        age: '',
        gender: 'male',
        
        // Chief Complaint
        chief_complaint_text: '',
        
        // Vital Signs (NEWS2)
        vitals: { hr: '', rr: '', spo2: '', temp: '', sbp: '', dbp: '' },
        
        // Legacy red flags (kept for API compatibility)
        red_flags: { history_cardiac: false, history_stroke: false, immuno_compromised: false },
        
        // Clinical Risk Factors (NEWS2 Compliance)
        is_copd: false,              // Use SpO2 Scale 2 (target 88-92%)
        on_supplemental_o2: false,   // Add +2 NEWS2 points
        
        // ESI v5 Pain Assessment
        pain_scale: 0,
        pain_context: '',
        
        // Immunocompromised Status
        is_immunocompromised: false,
        immunocompromised_reason: '',
        
        // Pediatric Fields (age < 18)
        immunizations_complete: null,
        
        // Pregnancy Fields (female, age 12-55)
        is_pregnant: false,
        gestational_weeks: null,
        pregnancy_complaint: ''
    });

    // ACVPU Consciousness Level (NEWS2)
    const [consciousness, setConsciousness] = useState("A");
    
    // UI State
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [useAI, setUseAI] = useState(false);
    
    // Voice Recording State
    const [isRecording, setIsRecording] = useState(false);
    const [isTranscribing, setIsTranscribing] = useState(false);
    const mediaRecorderRef = useRef(null);
    const audioChunksRef = useRef([]);

    // ==================== COMPUTED VALUES ====================
    
    const ageNumber = formData.age ? parseFloat(formData.age) : NaN;
    const isPediatric = !Number.isNaN(ageNumber) && ageNumber < 18;
    const isPregnancyEligible = (
        formData.gender === 'female' && 
        !Number.isNaN(ageNumber) && 
        ageNumber >= 12 && 
        ageNumber <= 55
    );

    // ==================== EFFECTS ====================
    
    /**
     * Reset pregnancy fields when patient becomes ineligible
     * (e.g., gender changed to male, or age outside 12-55)
     */
    useEffect(() => {
        if (!isPregnancyEligible && formData.is_pregnant) {
            setFormData(prev => ({
                ...prev,
                is_pregnant: false,
                gestational_weeks: null,
                pregnancy_complaint: ''
            }));
        }
    }, [formData.gender, formData.age, isPregnancyEligible, formData.is_pregnant]);

    // ==================== EVENT HANDLERS ====================
    
    /**
     * Handle vital sign input changes
     * Converts string to float for numeric values
     */
    const handleVitalChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({
            ...prev,
            vitals: { ...prev.vitals, [name]: value ? parseFloat(value) : '' }
        }));
    };

    // ==================== VOICE RECORDING ====================
    
    /**
     * Start audio recording for voice-to-text transcription
     * Uses Web Audio API with Gemini AI backend
     */
    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorderRef.current = new MediaRecorder(stream, { mimeType: 'audio/webm' });
            audioChunksRef.current = [];
            
            mediaRecorderRef.current.ondataavailable = (e) => {
                if (e.data.size > 0) audioChunksRef.current.push(e.data);
            };
            
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

    /**
     * Stop recording and trigger transcription
     */
    const stopRecording = () => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
            setIsRecording(false);
        }
    };

    /**
     * Send audio to backend for Gemini AI transcription
     * Supports Arabic and English
     */
    const transcribeAudio = async (audioBlob) => {
        setIsTranscribing(true);
        try {
            const formDataUpload = new FormData();
            formDataUpload.append('audio', audioBlob, 'recording.webm');
            
            const response = await axios.post(`${API_URL}/transcribe`, formDataUpload);
            
            if (response.data.success) {
                setFormData(prev => ({
                    ...prev,
                    chief_complaint_text: prev.chief_complaint_text 
                        ? `${prev.chief_complaint_text} ${response.data.transcription}` 
                        : response.data.transcription
                }));
            }
        } catch (err) {
            setError('Transcription failed. Ensure backend is running.');
        } finally {
            setIsTranscribing(false);
        }
    };


    // Computed pain value with default for slider
    const painScaleValue = formData.pain_scale ?? 0;

    // ==================== RISK FACTOR HANDLERS ====================
    
    /**
     * Handle Clinical Risk Factor checkbox changes
     * Used for COPD, Supplemental O2, etc.
     */
    const handleRiskFactorChange = (e) => {
        const { name, checked } = e.target;
        setFormData(prev => ({ ...prev, [name]: checked }));
    };

    // ==================== HELPERS ====================
    
    /**
     * Generate temporary Patient ID if none provided
     * Format: TEMP-YYYYMMDD-XXXX (4 random chars)
     */
    const generateTempId = () => {
        const now = new Date();
        const dateStr = now.toISOString().slice(0, 10).replace(/-/g, '');
        const randomPart = Math.random().toString(36).substring(2, 6).toUpperCase();
        return `TEMP-${dateStr}-${randomPart}`;
    };

    // ==================== VALIDATION ====================
    
    /**
     * Validate form values and return warnings for unusual inputs
     * Prevents accidental data entry errors (e.g., age 250 instead of 25)
     * Returns array of warning messages to show in confirmation dialog
     */
    const validateWithConfirmation = () => {
        const warnings = [];
        const age = parseFloat(formData.age);
        const hr = formData.vitals.hr ? parseInt(formData.vitals.hr) : null;
        const rr = formData.vitals.rr ? parseInt(formData.vitals.rr) : null;
        const spo2 = formData.vitals.spo2 ? parseFloat(formData.vitals.spo2) : null;
        const sbp = formData.vitals.sbp ? parseInt(formData.vitals.sbp) : null;
        const temp = formData.vitals.temp ? parseFloat(formData.vitals.temp) : null;

        // Age validation (oldest recorded human was 122)
        if (age > 120) {
            warnings.push(`⚠️ Age ${age} years is above 120. Did you mean ${Math.floor(age / 10)}?`);
        } else if (age > 100) {
            warnings.push(`⚠️ Age ${age} years - Please confirm this is correct.`);
        } else if (age < 0) {
            warnings.push(`⚠️ Age cannot be negative.`);
        }

        // Heart Rate validation (normal: 60-100 bpm)
        if (hr !== null) {
            if (hr > 250) warnings.push(`⚠️ Heart Rate ${hr} bpm is extremely high (>250). Please verify.`);
            if (hr < 20) warnings.push(`⚠️ Heart Rate ${hr} bpm is extremely low (<20). Please verify.`);
        }

        // Respiratory Rate validation (normal: 12-20/min)
        if (rr !== null) {
            if (rr > 60) warnings.push(`⚠️ Respiratory Rate ${rr}/min is extremely high (>60). Please verify.`);
            if (rr < 4) warnings.push(`⚠️ Respiratory Rate ${rr}/min is extremely low (<4). Please verify.`);
        }

        // SpO2 validation (normal: 95-100%)
        if (spo2 !== null) {
            if (spo2 > 100) warnings.push(`⚠️ SpO2 ${spo2}% cannot exceed 100%. Please correct.`);
            if (spo2 < 50) warnings.push(`⚠️ SpO2 ${spo2}% is critically low. Please verify.`);
        }

        // Blood Pressure validation (normal: 90-140 mmHg systolic)
        if (sbp !== null) {
            if (sbp > 300) warnings.push(`⚠️ Systolic BP ${sbp} mmHg is extremely high (>300). Please verify.`);
            if (sbp < 40) warnings.push(`⚠️ Systolic BP ${sbp} mmHg is extremely low (<40). Please verify.`);
        }

        // Temperature validation (normal: 36.1-37.2°C)
        if (temp !== null) {
            if (temp > 45) warnings.push(`⚠️ Temperature ${temp}°C is above survivable range (>45°C). Please verify.`);
            if (temp < 25) warnings.push(`⚠️ Temperature ${temp}°C is below survivable range (<25°C). Please verify.`);
        }

        return warnings;
    };

    // ==================== FORM SUBMISSION ====================
    
    /**
     * Handle form submission
     * - Validates unusual values with confirmation dialog
     * - Constructs API payload with all clinical data
     * - Sends to either standard or AI triage endpoint
     */
    const handleSubmit = async (e) => {
        e.preventDefault();
        
        // Check for unusual values and ask for confirmation
        const warnings = validateWithConfirmation();
        if (warnings.length > 0) {
            const confirmMessage = warnings.join('\n\n') + '\n\nDo you want to proceed anyway?';
            if (!window.confirm(confirmMessage)) {
                return; // User cancelled
            }
        }

        setLoading(true);
        setError(null);
        
        try {
            // Auto-generate Patient ID if empty
            const patientId = formData.patient_id?.trim() || generateTempId();
            
            // ===== Construct API Payload =====
            // Includes all clinical data for NEWS2 and ESI v5 assessment
            const payload = {
                ...formData,
                patient_id: patientId,
                age: formData.age ? parseFloat(formData.age) : 0,
                
                // Vital Signs (parsed to correct types)
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
                
                // ESI v5 Pain Assessment
                pain_scale: formData.pain_scale,
                pain_context: formData.pain_context || null,
                
                // Immunocompromised Status
                is_immunocompromised: formData.is_immunocompromised,
                immunocompromised_reason: formData.is_immunocompromised
                    ? (formData.immunocompromised_reason || null)
                    : null,
                    
                // Pediatric Fields (only if age < 18)
                immunizations_complete: isPediatric ? formData.immunizations_complete : null,
                
                // Pregnancy Fields (only if pregnant)
                is_pregnant: formData.is_pregnant,
                gestational_weeks: formData.is_pregnant ? formData.gestational_weeks : null,
                pregnancy_complaint: formData.is_pregnant
                    ? (formData.pregnancy_complaint || null)
                    : null
            };
            
            // Select endpoint based on AI toggle
            const endpoint = useAI ? `${API_URL}/ai-triage` : `${API_URL}/triage`;
            const res = await axios.post(endpoint, payload);
            
            // Send result to parent component
            onResult({ result: { ...res.data, isAI: useAI }, input: payload });
            
        } catch (err) {
            setError("Failed to process triage request. Ensure backend is running.");
        } finally {
            setLoading(false);
        }
    };

    // ==================== RENDER ====================
    
    return (
        <div className="max-w-2xl mx-auto">
            {/* ===== HEADER with AI Toggle ===== */}
            <div className="bg-gradient-to-r from-teal-600 to-teal-700 text-white rounded-t-xl p-5 flex justify-between items-center">
                <div>
                    <h2 className="text-xl font-bold flex items-center gap-2">
                        <Stethoscope className="w-6 h-6" />
                        SAFE-Triage
                    </h2>
                    <p className="text-teal-100 text-sm mt-0.5">
                        AI-Powered Emergency Triage | نظام الفرز الذكي
                    </p>
                </div>
                
                {/* AI Mode Toggle */}
                <div className="flex items-center gap-2 bg-teal-800/50 p-2 rounded-lg border border-teal-500/30">
                    <span className={`text-xs font-semibold transition-colors ${!useAI ? 'text-white' : 'text-teal-300'}`}>
                        Standard
                    </span>
                    <button 
                        type="button" 
                        onClick={() => setUseAI(!useAI)}
                        className={`w-11 h-6 rounded-full relative transition-colors ${useAI ? 'bg-purple-500' : 'bg-slate-500'}`}
                    >
                        <div className={`w-4 h-4 bg-white rounded-full absolute top-1 transition-all shadow-sm ${useAI ? 'left-6' : 'left-1'}`} />
                    </button>
                    <span className={`text-xs font-semibold transition-colors ${useAI ? 'text-white' : 'text-teal-300'}`}>
                        AI
                    </span>
                </div>
            </div>

            {/* ===== FORM BODY ===== */}
            <form onSubmit={handleSubmit} className="bg-slate-50 rounded-b-xl p-5 space-y-0">
                
                {/* Error Display */}
                {error && (
                    <div className="mb-5 p-4 bg-red-50 text-red-700 rounded-lg flex items-center gap-3 border border-red-200">
                        <AlertCircle className="w-5 h-5 flex-shrink-0" />
                        <span>{error}</span>
                    </div>
                )}

                {/* ===== SECTION 1: Patient Information ===== */}
                <SectionCard 
                    icon={Activity} 
                    title="Patient Information" 
                    titleAr="بيانات المريض"
                    accentColor="teal"
                >
                    <div className="grid grid-cols-2 gap-4">
                        <InputField
                            label="Patient ID / MRN"
                            labelAr="رقم المريض"
                            type="text"
                            value={formData.patient_id}
                            onChange={e => setFormData({ ...formData, patient_id: e.target.value })}
                            placeholder="Auto-generated if empty"
                        />
                        <InputField
                            label="Patient Name"
                            labelAr="اسم المريض"
                            type="text"
                            value={formData.patient_name}
                            onChange={e => setFormData({ ...formData, patient_name: e.target.value })}
                            placeholder="Full Name"
                            dir="auto"
                        />
                    </div>
                    <div className="grid grid-cols-2 gap-4 mt-4">
                        <InputField
                            label="Age"
                            labelAr="العمر"
                            type="number"
                            value={formData.age}
                            onChange={e => setFormData({ ...formData, age: e.target.value })}
                            placeholder="Years"
                            required
                        />
                        <SelectField
                            label="Gender"
                            labelAr="الجنس"
                            value={formData.gender}
                            onChange={e => setFormData({ ...formData, gender: e.target.value })}
                        >
                            <option value="male">Male | ذكر</option>
                            <option value="female">Female | أنثى</option>
                        </SelectField>
                    </div>
                </SectionCard>

                {/* ===== SECTION 2: Chief Complaint with Voice Input ===== */}
                <SectionCard 
                    icon={Mic} 
                    title="Chief Complaint" 
                    titleAr="الشكوى الرئيسية"
                    accentColor="blue"
                >
                    <div className="flex justify-between items-center mb-3">
                        <label className="text-sm font-medium text-slate-700">
                            Describe symptoms | صف الأعراض
                        </label>
                        <button 
                            type="button" 
                            onClick={isRecording ? stopRecording : startRecording} 
                            disabled={isTranscribing}
                            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                                isRecording 
                                    ? 'bg-red-500 text-white animate-pulse'
                                    : isTranscribing 
                                        ? 'bg-amber-100 text-amber-700'
                                        : 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200'
                            }`}
                        >
                            {isTranscribing ? (
                                <><Loader2 className="w-3.5 h-3.5 animate-spin" />Transcribing...</>
                            ) : isRecording ? (
                                <><MicOff className="w-3.5 h-3.5" />Stop</>
                            ) : (
                                <><Mic className="w-3.5 h-3.5" />Voice Input</>
                            )}
                        </button>
                    </div>
                    
                    {/* Recording Indicator */}
                    {isRecording && (
                        <div className="mb-3 p-2.5 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700 text-sm">
                            <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                            Recording... Speak now | جاري التسجيل...
                        </div>
                    )}
                    
                    <textarea
                        required
                        value={formData.chief_complaint_text}
                        onChange={e => setFormData({ ...formData, chief_complaint_text: e.target.value })}
                        className="w-full px-3 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500 min-h-[100px] text-slate-800 placeholder-slate-400"
                        placeholder="Describe symptoms or use Voice Input... | صف الأعراض أو استخدم التسجيل الصوتي..."
                        dir="auto"
                    />
                    <p className="text-xs text-slate-500 mt-2">
                        🎤 Voice transcription powered by Gemini AI (Arabic + English)
                    </p>
                </SectionCard>

                {/* ===== SECTION 3: Vital Signs (NEWS2) ===== */}
                <SectionCard 
                    icon={Heart} 
                    title="Vital Signs" 
                    titleAr="العلامات الحيوية"
                    accentColor="rose"
                >
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                        <VitalInput icon={Heart} label="HR" unit="bpm" name="hr" value={formData.vitals.hr} onChange={handleVitalChange} />
                        <VitalInput icon={Wind} label="RR" unit="/min" name="rr" value={formData.vitals.rr} onChange={handleVitalChange} />
                        <VitalInput icon={Droplets} label="SpO2" unit="%" name="spo2" value={formData.vitals.spo2} onChange={handleVitalChange} />
                        <VitalInput icon={Thermometer} label="Temp" unit="°C" name="temp" value={formData.vitals.temp} onChange={handleVitalChange} />
                        <VitalInput icon={Activity} label="SBP" unit="mmHg" name="sbp" value={formData.vitals.sbp} onChange={handleVitalChange} />
                        <VitalInput icon={Activity} label="DBP" unit="mmHg" name="dbp" value={formData.vitals.dbp} onChange={handleVitalChange} />
                    </div>
                    
                    {/* Consciousness Level (ACVPU) */}
                    <div className="mt-4 pt-4 border-t border-slate-200">
                        <SelectField
                            label="Consciousness (ACVPU)"
                            labelAr="مستوى الوعي"
                            value={consciousness}
                            onChange={(e) => setConsciousness(e.target.value)}
                        >
                            <option value="A">A - Alert | واعي تماماً</option>
                            <option value="C">C - New Confusion | تشوش ذهني جديد</option>
                            <option value="V">V - Responds to Voice | يستجيب للصوت</option>
                            <option value="P">P - Responds to Pain | يستجيب للألم</option>
                            <option value="U">U - Unresponsive | غير مستجيب</option>
                        </SelectField>
                    </div>
                </SectionCard>

                {/* ===== SECTION 4: Clinical Risk Factors (NEWS2) ===== */}
                <SectionCard 
                    icon={Shield} 
                    title="Clinical Risk Factors" 
                    titleAr="عوامل الخطورة السريرية"
                    accentColor="emerald"
                >
                    <p className="text-sm text-slate-600 mb-4">
                        These factors affect NEWS2 scoring. Check all that apply.
                    </p>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <CheckboxCard
                            name="is_copd"
                            checked={formData.is_copd}
                            onChange={handleRiskFactorChange}
                            title="COPD / CO₂ Retainer"
                            subtitle="Uses SpO₂ Scale 2 (target 88-92%)"
                            accentColor="emerald"
                        />
                        <CheckboxCard
                            name="on_supplemental_o2"
                            checked={formData.on_supplemental_o2}
                            onChange={handleRiskFactorChange}
                            title="On Supplemental O₂"
                            subtitle="Adds +2 points to NEWS2 score"
                            accentColor="blue"
                        />
                    </div>
                    
                    {/* Active Risk Factors Display */}
                    {(formData.is_copd || formData.on_supplemental_o2) && (
                        <div className="mt-4 p-3 bg-emerald-50 rounded-lg border border-emerald-200">
                            <p className="text-xs font-semibold text-emerald-800 mb-2">Active Risk Factors:</p>
                            <div className="flex flex-wrap gap-2">
                                {formData.is_copd && (
                                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-emerald-200 text-emerald-800">
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
                </SectionCard>


                {/* ===== SECTION 5: Pain Assessment (ESI v5) ===== */}
                <SectionCard 
                    icon={Activity} 
                    title="Pain Assessment" 
                    titleAr="تقييم الألم"
                    accentColor="amber"
                >
                    <div className="space-y-4">
                        {/* Pain Scale Slider */}
                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-2">
                                Pain Level (0-10) | <span className="text-slate-400 font-normal">مستوى الألم</span>
                            </label>
                            <div className="flex items-center gap-4">
                                <input
                                    type="range"
                                    min="0"
                                    max="10"
                                    value={painScaleValue}
                                    onChange={(e) => setFormData({ ...formData, pain_scale: parseInt(e.target.value) })}
                                    className="flex-1 h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-amber-500"
                                />
                                <span className={`
                                    w-12 h-12 rounded-full flex items-center justify-center text-lg font-bold
                                    ${painScaleValue === 0 ? 'bg-green-100 text-green-700' : 
                                      painScaleValue <= 3 ? 'bg-yellow-100 text-yellow-700' : 
                                      painScaleValue <= 6 ? 'bg-orange-100 text-orange-700' : 
                                      'bg-red-100 text-red-700'}
                                `}>
                                    {painScaleValue}
                                </span>
                            </div>
                            <div className="flex justify-between text-xs text-slate-400 mt-1 px-1">
                                <span>No Pain | لا ألم</span>
                                <span>Worst Pain | أشد ألم</span>
                            </div>
                        </div>

                        {/* Pain Context - only show if pain > 0 */}
                        {painScaleValue > 0 && (
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                                    Pain Context | <span className="text-slate-400 font-normal">سياق الألم</span>
                                </label>
                                <textarea
                                    value={formData.pain_context}
                                    onChange={(e) => setFormData({ ...formData, pain_context: e.target.value })}
                                    placeholder="Location, duration, character... | الموقع، المدة، الطبيعة..."
                                    className="w-full px-3 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500 min-h-[80px] text-slate-800 placeholder-slate-400"
                                    dir="auto"
                                />
                            </div>
                        )}
                    </div>
                </SectionCard>

                {/* ===== SECTION 6: Immune Status ===== */}
                <SectionCard 
                    icon={Shield} 
                    title="Immune Status" 
                    titleAr="حالة المناعة"
                    accentColor="purple"
                >
                    <div className="space-y-4">
                        <CheckboxCard
                            name="is_immunocompromised"
                            checked={formData.is_immunocompromised}
                            onChange={handleRiskFactorChange}
                            title="Immunocompromised | ضعف المناعة"
                            subtitle="Check if patient has weakened immune system"
                            accentColor="purple"
                        />

                        {/* Reason dropdown - only show if immunocompromised */}
                        {formData.is_immunocompromised && (
                            <SelectField
                                label="Reason for Immunocompromise"
                                labelAr="سبب ضعف المناعة"
                                value={formData.immunocompromised_reason}
                                onChange={(e) => setFormData({ ...formData, immunocompromised_reason: e.target.value })}
                            >
                                <option value="">Select reason... | اختر السبب...</option>
                                <option value="chemotherapy">Chemotherapy | العلاج الكيميائي</option>
                                <option value="transplant">Organ Transplant | زراعة أعضاء</option>
                                <option value="hiv_aids">HIV/AIDS | نقص المناعة المكتسب</option>
                                <option value="chronic_steroids">Chronic Steroids | كورتيزون مزمن</option>
                                <option value="biologics">Biologics/Immunosuppressants | مثبطات المناعة</option>
                                <option value="congenital">Congenital Immunodeficiency | نقص مناعة خلقي</option>
                                <option value="other">Other | أخرى</option>
                            </SelectField>
                        )}
                    </div>
                </SectionCard>

                {/* ===== SECTION 7: Pediatric Assessment (Conditional: age < 18) ===== */}
                {isPediatric && (
                    <SectionCard 
                        icon={Baby} 
                        title="Pediatric Assessment" 
                        titleAr="تقييم الأطفال"
                        accentColor="blue"
                    >
                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
                            <p className="text-sm text-blue-800">
                                <strong>Patient is under 18.</strong> Additional pediatric-specific information helps ensure appropriate triage.
                            </p>
                        </div>
                        
                        <SelectField
                            label="Immunization Status"
                            labelAr="حالة التطعيمات"
                            value={formData.immunizations_complete ?? ''}
                            onChange={(e) => setFormData({ 
                                ...formData, 
                                immunizations_complete: e.target.value === '' ? null : e.target.value === 'true' 
                            })}
                        >
                            <option value="">Unknown | غير معروف</option>
                            <option value="true">Up to Date | مكتملة</option>
                            <option value="false">Not Complete | غير مكتملة</option>
                        </SelectField>
                    </SectionCard>
                )}

                {/* ===== SECTION 8: Pregnancy Assessment (Conditional: female, age 12-55) ===== */}
                {isPregnancyEligible && (
                    <SectionCard 
                        icon={Heart} 
                        title="Pregnancy Status" 
                        titleAr="حالة الحمل"
                        accentColor="rose"
                    >
                        <div className="space-y-4">
                            <CheckboxCard
                                name="is_pregnant"
                                checked={formData.is_pregnant}
                                onChange={handleRiskFactorChange}
                                title="Currently Pregnant | حامل حالياً"
                                subtitle="Check if patient is pregnant"
                                accentColor="rose"
                            />

                            {/* Pregnancy details - only show if pregnant */}
                            {formData.is_pregnant && (
                                <>
                                    <InputField
                                        label="Gestational Weeks"
                                        labelAr="أسابيع الحمل"
                                        type="number"
                                        min="1"
                                        max="45"
                                        value={formData.gestational_weeks || ''}
                                        onChange={(e) => setFormData({ 
                                            ...formData, 
                                            gestational_weeks: e.target.value ? parseInt(e.target.value) : null 
                                        })}
                                        placeholder="e.g., 28"
                                    />

                                    <SelectField
                                        label="Pregnancy-Related Complaint"
                                        labelAr="شكوى متعلقة بالحمل"
                                        value={formData.pregnancy_complaint}
                                        onChange={(e) => setFormData({ ...formData, pregnancy_complaint: e.target.value })}
                                    >
                                        <option value="">None / Not pregnancy-related | لا يوجد</option>
                                        <option value="vaginal_bleeding">Vaginal Bleeding | نزيف مهبلي</option>
                                        <option value="abdominal_pain">Abdominal Pain | ألم بالبطن</option>
                                        <option value="contractions">Contractions | انقباضات</option>
                                        <option value="decreased_fetal_movement">Decreased Fetal Movement | قلة حركة الجنين</option>
                                        <option value="leaking_fluid">Leaking Fluid | تسرب سوائل</option>
                                        <option value="headache_vision">Severe Headache + Vision Changes | صداع شديد + تغير الرؤية</option>
                                        <option value="swelling">Sudden Swelling (Face/Hands) | تورم مفاجئ</option>
                                    </SelectField>

                                    {/* High-risk pregnancy warning */}
                                    {(formData.pregnancy_complaint === 'vaginal_bleeding' || 
                                      formData.pregnancy_complaint === 'headache_vision' ||
                                      formData.pregnancy_complaint === 'decreased_fetal_movement') && (
                                        <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                                            <p className="text-sm text-red-800 flex items-center gap-2">
                                                <AlertCircle className="w-4 h-4" />
                                                <strong>High-Risk Pregnancy Symptom</strong> - Prioritize assessment
                                            </p>
                                        </div>
                                    )}
                                </>
                            )}
                        </div>
                    </SectionCard>
                )}

                {/* ===== SUBMIT BUTTON ===== */}
                <button
                    type="submit"
                    disabled={loading}
                    className={`
                        w-full py-4 px-6 rounded-xl font-semibold text-white text-lg
                        flex items-center justify-center gap-2 transition-all
                        ${loading 
                            ? 'bg-slate-400 cursor-not-allowed' 
                            : useAI 
                                ? 'bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 shadow-lg hover:shadow-purple-500/30' 
                                : 'bg-gradient-to-r from-teal-600 to-teal-700 hover:from-teal-700 hover:to-teal-800 shadow-lg hover:shadow-teal-500/30'
                        }
                    `}
                >
                    {loading ? (
                        <>
                            <Loader2 className="w-5 h-5 animate-spin" />
                            Processing Triage... | جاري المعالجة...
                        </>
                    ) : (
                        <>
                            {useAI ? (
                                <>
                                    <Brain className="w-5 h-5" />
                                    Submit AI Triage | إرسال للذكاء الاصطناعي
                                </>
                            ) : (
                                <>
                                    <ChevronRight className="w-5 h-5" />
                                    Submit Triage | إرسال الفرز
                                </>
                            )}
                        </>
                    )}
                </button>

                {/* ===== ERROR DISPLAY ===== */}
                {error && (
                    <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
                        <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                        <div>
                            <p className="font-semibold text-red-800">Triage Error</p>
                            <p className="text-sm text-red-700">{error}</p>
                        </div>
                    </div>
                )}
            </form>
        </div>
    );
}
