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
import ConfirmationDialog from './ConfirmationDialog';
import { getIdToken } from '../lib/firebaseClient';
import '../styles/vitals.css';

const API_URL = import.meta.env.VITE_API_URL || import.meta.env.REACT_APP_API_URL || 'http://localhost:8000';
const MONITOR_POLL_MS = 10000;

const CHIEF_COMPLAINT_VALIDATION = {
    MIN_LENGTH: 3,
    MAX_LENGTH: 500,
    REQUIRES_LETTERS: /[a-zA-Zأ-ي]/,
    ONLY_NUMBERS: /^\d+$/,
    ONLY_SPECIAL_CHARS: /^[^a-zA-Zأ-ي0-9]+$/
};

const REQUIRED_VITALS = ['hr', 'sbp', 'dbp', 'rr', 'spo2', 'temp', 'consciousness'];

const ESI1_BYPASS_KEYWORDS = [
    'cardiac arrest',
    'respiratory arrest',
    'not breathing',
    'unconscious',
    'active seizure',
    'massive hemorrhage',
    'severe trauma',
    'anaphylaxis',
    'توقف القلب',
    'توقف التنفس',
    'مش بيتنفس',
    'فاقد الوعي',
    'تشنج',
    'نزيف شديد',
    'إصابة شديدة',
];

const VITAL_RANGES = {
    hr: { min: 20, max: 250, unit: 'bpm', name: 'Heart Rate', nameAr: 'معدل القلب' },
    sbp: { min: 50, max: 250, unit: 'mmHg', name: 'Systolic BP', nameAr: 'الضغط الانقباضي' },
    dbp: { min: 20, max: 150, unit: 'mmHg', name: 'Diastolic BP', nameAr: 'الضغط الانبساطي' },
    rr: { min: 4, max: 60, unit: '/min', name: 'Respiratory Rate', nameAr: 'معدل التنفس' },
    spo2: { min: 50, max: 100, unit: '%', name: 'SpO2', nameAr: 'تشبع الأكسجين' },
    temp: { min: 30, max: 45, unit: '°C', name: 'Temperature', nameAr: 'الحرارة' },
    blood_glucose: { min: 20, max: 1000, unit: 'mg/dL', name: 'Blood Glucose', nameAr: 'سكر الدم' },
};

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
        vitals: { hr: '', rr: '', spo2: '', temp: '', sbp: '', dbp: '', blood_glucose: '' },
        
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
    const [vitalsSource, setVitalsSource] = useState('manual');
    const [vitalsTimestamp, setVitalsTimestamp] = useState(null);
    const [monitorDevice, setMonitorDevice] = useState(null);
    const [monitorBed, setMonitorBed] = useState(null);
    const [monitorNews2Score, setMonitorNews2Score] = useState(null);
    const [loadingVitals, setLoadingVitals] = useState(false);
    const [manualVitalsUnlocked, setManualVitalsUnlocked] = useState(false);
    const [showConfirmDialog, setShowConfirmDialog] = useState(false);
    const [unusualVitals, setUnusualVitals] = useState([]);
    const [mrnError, setMrnError] = useState('');
    const [nameError, setNameError] = useState('');
    
    // Voice Recording State
    const [isRecording, setIsRecording] = useState(false);
    const [isTranscribing, setIsTranscribing] = useState(false);
    const [voiceLanguage, setVoiceLanguage] = useState('auto');
    const [savedVoiceNotes, setSavedVoiceNotes] = useState([]);
    const [recordingSeconds, setRecordingSeconds] = useState(0);
    const [audioLevel, setAudioLevel] = useState(0);
    const [pendingAudioBlob, setPendingAudioBlob] = useState(null);
    const [pendingAudioUrl, setPendingAudioUrl] = useState(null);
    const mediaRecorderRef = useRef(null);
    const audioChunksRef = useRef([]);
    const recordingTimerRef = useRef(null);
    const audioContextRef = useRef(null);
    const analyserRef = useRef(null);
    const animationFrameRef = useRef(null);
    const MAX_RECORDING_SECONDS = 60;

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

    /**
     * Auto-load vitals from bedside monitor cache when a patient ID is available.
     * Falls back to manual entry when monitor cache is unavailable.
     */
    useEffect(() => {
        const patientId = (formData.patient_id || '').trim();
        if (!patientId) {
            setLoadingVitals(false);
            setVitalsSource('manual');
            setVitalsTimestamp(null);
            setMonitorDevice(null);
            setMonitorBed(null);
            setMonitorNews2Score(null);
            setManualVitalsUnlocked(false);
            return undefined;
        }

        let cancelled = false;

        const fetchMonitorVitals = async () => {
            setLoadingVitals(true);
            try {
                const response = await fetch(`${API_URL}/monitor/vitals/${encodeURIComponent(patientId)}`);
                if (!response.ok) {
                    if (!cancelled) {
                        setVitalsSource('manual');
                    }
                    return;
                }

                const data = await response.json();
                if (cancelled) return;

                setFormData((prev) => ({
                    ...prev,
                    vitals: {
                        ...prev.vitals,
                        hr: data?.vitals?.hr ?? '',
                        sbp: data?.vitals?.sbp ?? '',
                        dbp: data?.vitals?.dbp ?? '',
                        rr: data?.vitals?.rr ?? '',
                        spo2: data?.vitals?.spo2 ?? '',
                        temp: data?.vitals?.temp ?? '',
                        blood_glucose: data?.vitals?.blood_glucose ?? '',
                    },
                }));

                setConsciousness(data?.vitals?.consciousness || 'A');
                setVitalsSource('monitor');
                setVitalsTimestamp(data?.timestamp ? new Date(data.timestamp) : null);
                setMonitorDevice(data?.device || null);
                setMonitorBed(data?.bed || null);
                setMonitorNews2Score(
                    typeof data?.news2?.total_score === 'number' ? data.news2.total_score : null
                );
                setManualVitalsUnlocked(false);
            } catch (_err) {
                if (!cancelled) {
                    setVitalsSource('manual');
                    setMonitorNews2Score(null);
                }
            } finally {
                if (!cancelled) {
                    setLoadingVitals(false);
                }
            }
        };

        fetchMonitorVitals();
        const intervalId = window.setInterval(fetchMonitorVitals, MONITOR_POLL_MS);
        return () => {
            cancelled = true;
            window.clearInterval(intervalId);
        };
    }, [formData.patient_id]);

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

    const handleMrnChange = (event) => {
        const rawValue = event.target.value || '';
        const numericOnly = rawValue.replace(/\D/g, '');
        setFormData((prev) => ({ ...prev, patient_id: numericOnly }));
        if (rawValue !== numericOnly) {
            setMrnError('MRN must contain numbers only / الرقم الطبي يجب أن يحتوي على أرقام فقط');
        } else {
            setMrnError('');
        }
    };

    const NAME_REGEX = /^[\p{L}\s\-']+$/u;
    const handleNameChange = (event) => {
        const value = event.target.value;
        setFormData((prev) => ({ ...prev, patient_name: value }));
        if (value && !NAME_REGEX.test(value)) {
            setNameError('Name must contain letters only / الاسم يجب أن يحتوي على حروف فقط');
        } else {
            setNameError('');
        }
    };

    // ==================== VOICE RECORDING ====================
    
    /**
     * Start audio recording for voice-to-text transcription
     * Uses Web Audio API with noise suppression + echo cancellation for noisy ED environments
     */
    const startRecording = async () => {
        try {
            // Audio constraints optimized for noisy emergency department environments
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    noiseSuppression: true,
                    echoCancellation: true,
                    autoGainControl: true,
                    channelCount: 1,
                    sampleRate: 48000,
                }
            });

            // Set up audio level visualization via Web Audio API
            const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const source = audioCtx.createMediaStreamSource(stream);
            const analyser = audioCtx.createAnalyser();
            analyser.fftSize = 256;
            analyser.smoothingTimeConstant = 0.5;
            source.connect(analyser);
            audioContextRef.current = audioCtx;
            analyserRef.current = analyser;

            const updateLevel = () => {
                if (!analyserRef.current) return;
                const data = new Uint8Array(analyserRef.current.frequencyBinCount);
                analyserRef.current.getByteFrequencyData(data);
                const avg = data.reduce((sum, v) => sum + v, 0) / data.length;
                setAudioLevel(Math.min(avg / 128, 1)); // normalize 0-1
                animationFrameRef.current = requestAnimationFrame(updateLevel);
            };
            updateLevel();

            // Negotiate MIME type: Safari/iOS doesn't support audio/webm
            const mimePreference = ['audio/webm', 'audio/mp4', 'audio/ogg', 'audio/wav'];
            const selectedMime = mimePreference.find(m => MediaRecorder.isTypeSupported(m)) || '';
            const recorderOptions = selectedMime ? { mimeType: selectedMime } : {};
            mediaRecorderRef.current = new MediaRecorder(stream, recorderOptions);
            audioChunksRef.current = [];
            // Store the actual MIME for blob creation and upload
            const actualMime = mediaRecorderRef.current.mimeType || 'audio/webm';

            mediaRecorderRef.current.ondataavailable = (e) => {
                if (e.data.size > 0) audioChunksRef.current.push(e.data);
            };

            mediaRecorderRef.current.onstop = () => {
                const audioBlob = new Blob(audioChunksRef.current, { type: actualMime });
                const url = URL.createObjectURL(audioBlob);
                setPendingAudioBlob(audioBlob);
                setPendingAudioUrl(url);
                stream.getTracks().forEach(track => track.stop());
            };

            mediaRecorderRef.current.start();
            setIsRecording(true);
            setPendingAudioBlob(null);
            setPendingAudioUrl(null);
            setRecordingSeconds(0);

            // Recording timer with auto-stop at MAX_RECORDING_SECONDS
            recordingTimerRef.current = setInterval(() => {
                setRecordingSeconds(prev => {
                    if (prev + 1 >= MAX_RECORDING_SECONDS) {
                        stopRecording();
                        return MAX_RECORDING_SECONDS;
                    }
                    return prev + 1;
                });
            }, 1000);
        } catch (err) {
            setError('Microphone access denied. Please allow microphone permission. | تم رفض صلاحية الميكروفون. يرجى السماح بالوصول.');
        }
    };

    /**
     * Stop recording — shows playback preview before transcription
     */
    const stopRecording = () => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
            mediaRecorderRef.current.stop();
        }
        setIsRecording(false);
        clearInterval(recordingTimerRef.current);
        recordingTimerRef.current = null;
        // Clean up audio level monitoring
        if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
        if (audioContextRef.current) {
            audioContextRef.current.close().catch(() => {});
            audioContextRef.current = null;
        }
        analyserRef.current = null;
        setAudioLevel(0);
    };

    /**
     * Submit pending audio for transcription (after playback preview)
     */
    const submitPendingAudio = async () => {
        if (!pendingAudioBlob) return;
        await transcribeAudio(pendingAudioBlob);
        if (pendingAudioUrl) URL.revokeObjectURL(pendingAudioUrl);
        setPendingAudioBlob(null);
        setPendingAudioUrl(null);
    };

    /**
     * Discard pending audio without transcribing
     */
    const discardPendingAudio = () => {
        if (pendingAudioUrl) URL.revokeObjectURL(pendingAudioUrl);
        setPendingAudioBlob(null);
        setPendingAudioUrl(null);
    };

    // Cleanup timer and audio context on unmount
    useEffect(() => {
        return () => {
            clearInterval(recordingTimerRef.current);
            if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
            if (audioContextRef.current) audioContextRef.current.close().catch(() => {});
            if (pendingAudioUrl) URL.revokeObjectURL(pendingAudioUrl);
        };
    }, []);

    /**
     * Send audio to backend for Gemini AI transcription
     * Supports Arabic and English
     */
    const transcribeAudio = async (audioBlob) => {
        setIsTranscribing(true);
        try {
            const formDataUpload = new FormData();
            // Derive file extension from blob MIME type for correct backend format detection
            const extMap = { 'audio/webm': '.webm', 'audio/mp4': '.m4a', 'audio/ogg': '.ogg', 'audio/wav': '.wav' };
            const ext = extMap[audioBlob.type] || '.webm';
            formDataUpload.append('audio', audioBlob, `recording${ext}`);
            formDataUpload.append('language', voiceLanguage || 'auto');
            formDataUpload.append('patient_id', formData.patient_id || '');
            formDataUpload.append('save_recording', 'true');

            const response = await axios.post(`${API_URL}/transcribe`, formDataUpload);

            if (response.data.success) {
                setFormData(prev => ({
                    ...prev,
                    chief_complaint_text: prev.chief_complaint_text
                        ? `${prev.chief_complaint_text} ${response.data.transcription}`
                        : response.data.transcription
                }));
                if (response.data.voice_note_id) {
                    setSavedVoiceNotes(prev => [...prev, {
                        id: response.data.voice_note_id,
                        transcription: response.data.transcription,
                        timestamp: new Date().toISOString(),
                    }]);
                }
            }
        } catch (err) {
            const backendDetail = err?.response?.data?.detail || err?.response?.data?.error;
            if (backendDetail && backendDetail.toLowerCase().includes('disabled')) {
                setError('Voice transcription is not enabled on the server. Please contact your administrator. | خاصية التفريغ الصوتي غير مفعّلة على الخادم. يرجى التواصل مع المسؤول.');
            } else if (backendDetail) {
                setError(`Transcription failed: ${backendDetail} | فشل التفريغ الصوتي: ${backendDetail}`);
            } else if (!err?.response) {
                setError('Transcription failed: cannot reach backend API. | فشل التفريغ الصوتي: تعذر الوصول إلى الخادم.');
            } else {
                setError('Transcription failed due to backend error. | فشل التفريغ الصوتي بسبب خطأ في الخادم.');
            }
        } finally {
            setIsTranscribing(false);
        }
    };


    // Computed pain value with default for slider
    const painScaleValue = formData.pain_scale ?? 0;
    const monitorLocked = vitalsSource === 'monitor' && !manualVitalsUnlocked;

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
    
    const validateChiefComplaint = (complaint) => {
        const text = (complaint || '').trim();
        if (!text || text.length < CHIEF_COMPLAINT_VALIDATION.MIN_LENGTH) {
            return {
                valid: false,
                error: 'Chief complaint too short - minimum 3 characters',
                errorAr: 'الشكوى قصيرة جدًا - 3 أحرف على الأقل'
            };
        }
        if (text.length > CHIEF_COMPLAINT_VALIDATION.MAX_LENGTH) {
            return {
                valid: false,
                error: 'Chief complaint too long - maximum 500 characters',
                errorAr: 'الشكوى طويلة جدًا - 500 حرف كحد أقصى'
            };
        }
        if (!CHIEF_COMPLAINT_VALIDATION.REQUIRES_LETTERS.test(text)) {
            return {
                valid: false,
                error: 'Chief complaint must contain letters (Arabic or English)',
                errorAr: 'يجب أن تحتوي الشكوى على حروف (عربية أو إنجليزية)'
            };
        }
        if (CHIEF_COMPLAINT_VALIDATION.ONLY_NUMBERS.test(text)) {
            return {
                valid: false,
                error: 'Invalid input - chief complaint cannot be only numbers',
                errorAr: 'إدخال غير صالح - لا يمكن أن تكون الشكوى أرقامًا فقط'
            };
        }
        if (CHIEF_COMPLAINT_VALIDATION.ONLY_SPECIAL_CHARS.test(text)) {
            return {
                valid: false,
                error: 'Invalid input - chief complaint must contain words',
                errorAr: 'إدخال غير صالح - يجب أن تحتوي الشكوى على كلمات'
            };
        }
        const wordCount = text.split(/\s+/).filter(Boolean).length;
        if (wordCount < 2 && text.length < 10) {
            return {
                valid: false,
                error: 'Please provide more detail about the patient\'s complaint',
                errorAr: 'يرجى تقديم المزيد من التفاصيل حول شكوى المريض'
            };
        }
        return { valid: true };
    };

    const validateVitalSigns = (vitals) => {
        const errors = [];
        const warnings = [];
        const payload = { ...vitals, consciousness };
        const complaintText = (formData.chief_complaint_text || '').toLowerCase();
        const bypassAllowed = ESI1_BYPASS_KEYWORDS.some((token) => complaintText.includes(token));

        const missing = REQUIRED_VITALS.filter((field) => {
            const value = payload[field];
            return value === null || value === undefined || value === '';
        });
        if (missing.length > 0 && !bypassAllowed) {
            errors.push({
                type: 'missing_vitals',
                message: `Missing required vital signs: ${missing.map((m) => (VITAL_RANGES[m]?.name || m)).join(', ')}`,
                messageAr: `قياسات حيوية مطلوبة مفقودة: ${missing.map((m) => (VITAL_RANGES[m]?.nameAr || m)).join('، ')}`,
                fields: missing
            });
        } else if (missing.length > 0 && bypassAllowed) {
            warnings.push({
                type: 'esi1_vitals_bypass',
                message: 'Life-threatening complaint detected - proceed now and complete vitals during resuscitation.',
                messageAr: 'تم اكتشاف حالة مهددة للحياة - تابع الآن واستكمل العلامات الحيوية أثناء الإنعاش.',
                severity: 'critical',
            });
        }

        Object.entries(VITAL_RANGES).forEach(([field, range]) => {
            const value = parseFloat(payload[field]);
            if (Number.isNaN(value)) return;
            if (value < range.min || value > range.max) {
                warnings.push({
                    type: 'out_of_range',
                    field,
                    value,
                    range: [range.min, range.max],
                    message: `${range.name} (${value}) is outside valid range (${range.min}-${range.max} ${range.unit})`,
                    messageAr: `${range.nameAr} (${value}) خارج النطاق الصحيح (${range.min}-${range.max} ${range.unit})`,
                });
            }
        });

        const hr = parseFloat(payload.hr);
        const sbp = parseFloat(payload.sbp);
        if (!Number.isNaN(hr) && !Number.isNaN(sbp) && hr > 120 && sbp < 90) {
            warnings.push({
                type: 'shock_indicators',
                message: 'CRITICAL: High HR + Low BP may indicate shock',
                messageAr: 'حرج: معدل قلب عالي + ضغط منخفض قد يشير إلى صدمة',
                severity: 'critical',
            });
        }

        return {
            valid: errors.length === 0,
            errors,
            warnings,
            requiresConfirmation: warnings.length > 0,
            bypassAllowed,
        };
    };

    const getGlucoseClass = (bg) => {
        if (bg === '' || bg === null || bg === undefined) return '';
        const value = parseFloat(bg);
        if (Number.isNaN(value)) return '';
        if (value < 54) return 'critical-low';
        if (value < 70) return 'warning-low';
        if (value > 600) return 'critical-high';
        if (value > 250) return 'warning-high';
        return 'normal';
    };

    const getGlucoseMessage = (bg) => {
        if (bg === '' || bg === null || bg === undefined) return '';
        const value = parseFloat(bg);
        if (Number.isNaN(value)) return '';
        if (value < 54) return 'Critical hypoglycemia - immediate action required | هبوط سكر حرج - تدخل فوري';
        if (value < 70) return 'Hypoglycemia - monitor closely | انخفاض سكر - مراقبة دقيقة';
        if (value > 600) return 'Extreme hyperglycemia - possible HHS | ارتفاع سكر شديد جدًا - احتمال HHS';
        if (value > 400) return 'Severe hyperglycemia - check for DKA | ارتفاع سكر شديد - افحص DKA';
        if (value > 250) return 'Hyperglycemia - further evaluation needed | ارتفاع سكر - يحتاج تقييم';
        if (value > 180) return 'Elevated glucose | سكر مرتفع';
        return 'Normal range | نطاق طبيعي';
    };

    // ==================== FORM SUBMISSION ====================
    
    /**
     * Handle form submission
     * - Validates unusual values with confirmation dialog
     * - Constructs API payload with all clinical data
     * - Sends to either standard or AI triage endpoint
     */
    const submitTriage = async () => {
        setLoading(true);
        setError(null);
        
        try {
            const mrnValue = (formData.patient_id || '').trim();
            if (mrnValue && !/^\d+$/.test(mrnValue)) {
                setMrnError('MRN must contain numbers only / الرقم الطبي يجب أن يحتوي على أرقام فقط');
                setError({
                    title: 'MRN must contain numbers only',
                    titleAr: 'الرقم الطبي يجب أن يحتوي على أرقام فقط'
                });
                return;
            }
            // Auto-generate Patient ID if empty
            const patientId = mrnValue || generateTempId();
            
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
                    blood_glucose: formData.vitals.blood_glucose ? parseFloat(formData.vitals.blood_glucose) : null,
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
            const token = await getIdToken().catch((e) => {
                console.warn('[auth] getIdToken failed — triage submitted without clinician identity:', e?.code);
                return null;
            });
            const headers = token ? { Authorization: `Bearer ${token}` } : {};
            const res = await axios.post(endpoint, payload, { headers });
            
            // Send result to parent component
            onResult({ result: { ...res.data, isAI: useAI }, input: payload });

            if (vitalsSource === 'monitor' && payload.patient_id) {
                axios.delete(`${API_URL}/monitor/vitals/${encodeURIComponent(payload.patient_id)}`).catch(() => {});
            }
            
        } catch (err) {
            // Parse structured error from backend validation
            if (err.response?.status === 422 && err.response?.data?.detail) {
                const detail = err.response.data.detail;
                const title = detail?.message || detail?.error || 'Validation error';
                setError({
                    title,
                    titleAr: detail?.message_ar || detail?.error_ar || null,
                    suggestion: detail?.action ? `Action: ${detail.action}` : null
                });
            } else if (err.response?.data?.detail) {
                const detail = err.response.data.detail;
                if (typeof detail === 'object' && detail.error) {
                    setError({
                        title: detail.error,
                        titleAr: detail.error_ar,
                        suggestion: detail.suggestion
                    });
                } else {
                    setError({ title: typeof detail === 'string' ? detail : JSON.stringify(detail) });
                }
            } else if (err.response?.status === 422) {
                setError({ title: "Invalid input data. Please check all required fields." });
            } else {
                setError({ title: "Failed to process triage request. Ensure backend is running." });
            }
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        const mrnValue = (formData.patient_id || '').trim();
        if (mrnValue && !/^\d+$/.test(mrnValue)) {
            setMrnError('MRN must contain numbers only / الرقم الطبي يجب أن يحتوي على أرقام فقط');
            setError({
                title: 'MRN must contain numbers only',
                titleAr: 'الرقم الطبي يجب أن يحتوي على أرقام فقط',
            });
            return;
        }

        const complaintValidation = validateChiefComplaint(formData.chief_complaint_text);
        if (!complaintValidation.valid) {
            setError({
                title: complaintValidation.error,
                titleAr: complaintValidation.errorAr
            });
            return;
        }

        const vitalsValidation = validateVitalSigns(formData.vitals);
        if (!vitalsValidation.valid) {
            const firstError = vitalsValidation.errors[0];
            setError({
                title: firstError?.message || 'Missing required vital signs',
                titleAr: firstError?.messageAr || 'قياسات حيوية مطلوبة مفقودة'
            });
            return;
        }

        if (vitalsValidation.requiresConfirmation) {
            setUnusualVitals(vitalsValidation.warnings);
            setShowConfirmDialog(true);
            return;
        }

        await submitTriage();
    };

    const handleConfirmUnusualVitals = async () => {
        setShowConfirmDialog(false);
        await submitTriage();
    };

    const handleCancelUnusualVitals = () => {
        setShowConfirmDialog(false);
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
                    <div className="mb-5 p-4 bg-red-50 rounded-lg border border-red-200">
                        <div className="flex items-start gap-3">
                            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                            <div className="flex-1">
                                <p className="font-semibold text-red-800">
                                    {typeof error === 'string' ? error : error.title}
                                </p>
                                {error.titleAr && (
                                    <p className="text-red-700 text-sm mt-1" dir="rtl">{error.titleAr}</p>
                                )}
                                {error.suggestion && (
                                    <p className="text-red-600 text-sm mt-2 bg-red-100 p-2 rounded">
                                        💡 {error.suggestion}
                                    </p>
                                )}
                            </div>
                        </div>
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
                        <div>
                            <InputField
                                label="Patient ID / MRN"
                                labelAr="رقم المريض"
                                type="text"
                                inputMode="numeric"
                                pattern="[0-9]*"
                                value={formData.patient_id}
                                onChange={handleMrnChange}
                                placeholder="e.g., 123456 (numbers only / أرقام فقط)"
                            />
                            {mrnError && (
                                <p className="text-red-500 text-xs mt-1">{mrnError}</p>
                            )}
                        </div>
                        <div>
                            <InputField
                                label="Patient Name"
                                labelAr="اسم المريض"
                                type="text"
                                value={formData.patient_name}
                                onChange={handleNameChange}
                                placeholder="Full Name"
                                dir="auto"
                            />
                            {nameError && (
                                <p className="text-red-500 text-xs mt-1">{nameError}</p>
                            )}
                        </div>
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
                        <div className="flex items-center gap-2">
                            {isRecording && (
                                <span className="text-xs font-mono text-red-600 tabular-nums">
                                    {Math.floor(recordingSeconds / 60).toString().padStart(2, '0')}:{(recordingSeconds % 60).toString().padStart(2, '0')}
                                    <span className="text-red-400 ml-1">/ {Math.floor(MAX_RECORDING_SECONDS / 60)}:{(MAX_RECORDING_SECONDS % 60).toString().padStart(2, '0')}</span>
                                </span>
                            )}
                            <button
                                type="button"
                                onClick={isRecording ? stopRecording : startRecording}
                                disabled={isTranscribing || !!pendingAudioBlob}
                                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                                    isRecording
                                        ? 'bg-red-500 text-white animate-pulse'
                                        : isTranscribing
                                            ? 'bg-amber-100 text-amber-700'
                                            : pendingAudioBlob
                                                ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                                                : 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200'
                                }`}
                            >
                                {isTranscribing ? (
                                    <><Loader2 className="w-3.5 h-3.5 animate-spin" />Transcribing... | جاري التفريغ...</>
                                ) : isRecording ? (
                                    <><MicOff className="w-3.5 h-3.5" />Stop | إيقاف</>
                                ) : (
                                    <><Mic className="w-3.5 h-3.5" />Voice Input | إدخال صوتي</>
                                )}
                            </button>
                        </div>
                    </div>

                    <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-600">
                        <span className="font-medium">Voice Language | لغة الصوت:</span>
                        <select
                            value={voiceLanguage}
                            onChange={(e) => setVoiceLanguage(e.target.value)}
                            className="px-2 py-1 rounded-md border border-slate-200 bg-white text-xs"
                        >
                            <option value="auto">🌐 Auto | تلقائي</option>
                            <option value="ar-EG">🇪🇬 Arabic | عربي</option>
                            <option value="en-US">🇬🇧 English | إنجليزي</option>
                        </select>
                    </div>

                    {/* Recording Indicator with Audio Level */}
                    {isRecording && (
                        <div className="mb-3 p-2.5 bg-red-50 border border-red-200 rounded-lg">
                            <div className="flex items-center gap-2 text-red-700 text-sm mb-2">
                                <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                                Recording... Speak now | جاري التسجيل...
                            </div>
                            {/* Audio Level Meter */}
                            <div className="flex items-center gap-2">
                                <Mic className="w-3.5 h-3.5 text-red-400" />
                                <div className="flex-1 h-2 bg-red-100 rounded-full overflow-hidden">
                                    <div
                                        className="h-full rounded-full transition-all duration-100"
                                        style={{
                                            width: `${Math.max(audioLevel * 100, 2)}%`,
                                            backgroundColor: audioLevel > 0.7 ? '#ef4444' : audioLevel > 0.3 ? '#f59e0b' : '#22c55e',
                                        }}
                                    />
                                </div>
                                <span className="text-xs text-red-400 w-6 text-right">{Math.round(audioLevel * 100)}%</span>
                            </div>
                        </div>
                    )}

                    {/* Playback Preview — shown after recording, before transcription */}
                    {pendingAudioBlob && !isRecording && !isTranscribing && (
                        <div className="mb-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                            <p className="text-xs font-semibold text-blue-700 mb-2">
                                Review recording before transcription | راجع التسجيل قبل التفريغ
                            </p>
                            <audio
                                src={pendingAudioUrl}
                                controls
                                className="w-full h-8 mb-2"
                                style={{ colorScheme: 'light' }}
                            />
                            <div className="flex gap-2">
                                <button
                                    type="button"
                                    onClick={submitPendingAudio}
                                    className="flex-1 flex items-center justify-center gap-1 px-3 py-1.5 bg-emerald-500 text-white rounded-lg text-xs font-medium hover:bg-emerald-600 transition-colors"
                                >
                                    <ChevronRight className="w-3.5 h-3.5" />
                                    Transcribe | تفريغ
                                </button>
                                <button
                                    type="button"
                                    onClick={discardPendingAudio}
                                    className="flex items-center justify-center gap-1 px-3 py-1.5 bg-slate-200 text-slate-600 rounded-lg text-xs font-medium hover:bg-slate-300 transition-colors"
                                >
                                    Discard | تجاهل
                                </button>
                            </div>
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
                        🎤 Voice transcription (Auto Arabic/English) | تفريغ صوتي تلقائي (عربي/إنجليزي)
                    </p>

                    {savedVoiceNotes.length > 0 && (
                        <div className="mt-3 p-2.5 bg-emerald-50 border border-emerald-200 rounded-lg">
                            <p className="text-xs font-semibold text-emerald-700 mb-1.5">
                                Saved Voice Notes ({savedVoiceNotes.length}) | الملاحظات الصوتية المحفوظة
                            </p>
                            <ul className="space-y-1">
                                {savedVoiceNotes.map((note, idx) => (
                                    <li key={note.id || idx} className="text-xs text-emerald-800 flex items-start gap-1.5">
                                        <span className="text-emerald-500 mt-0.5">🎙</span>
                                        <span className="truncate" dir="auto">{note.transcription}</span>
                                        <span className="text-emerald-400 whitespace-nowrap ml-auto">
                                            {new Date(note.timestamp).toLocaleTimeString()}
                                        </span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </SectionCard>

                {/* ===== SECTION 3: Vital Signs (NEWS2) ===== */}
                <SectionCard 
                    icon={Heart} 
                    title="Vital Signs" 
                    titleAr="العلامات الحيوية"
                    accentColor="rose"
                >
                    {loadingVitals && (
                        <div className="mb-4 rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
                            Checking for monitor vitals... | جاري فحص اتصال المونيتور...
                        </div>
                    )}

                    {!loadingVitals && vitalsSource === 'monitor' && (
                        <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
                            <div className="font-semibold">Vitals auto-loaded from bedside monitor | تم تحميل العلامات الحيوية من المونيتور</div>
                            <div className="mt-1 text-xs text-emerald-700">
                                Device: {monitorDevice || 'Unknown'} | Bed: {monitorBed || 'N/A'} | Time:{' '}
                                {vitalsTimestamp ? vitalsTimestamp.toLocaleTimeString('ar-EG') : 'N/A'}
                            </div>
                            {monitorNews2Score !== null && (
                                <div className="mt-1 text-xs font-semibold text-emerald-800">
                                    NEWS2: {monitorNews2Score}
                                </div>
                            )}
                        </div>
                    )}

                    {!loadingVitals && vitalsSource === 'manual' && (
                        <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                            No monitor vitals found. Please enter manually. | لا توجد علامات حيوية من المونيتور، يرجى الإدخال اليدوي.
                        </div>
                    )}

                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                        <VitalInput icon={Heart} label="HR" unit="bpm" name="hr" value={formData.vitals.hr} onChange={handleVitalChange} disabled={monitorLocked} />
                        <VitalInput icon={Wind} label="RR" unit="/min" name="rr" value={formData.vitals.rr} onChange={handleVitalChange} disabled={monitorLocked} />
                        <VitalInput icon={Droplets} label="SpO2" unit="%" name="spo2" value={formData.vitals.spo2} onChange={handleVitalChange} disabled={monitorLocked} />
                        <VitalInput icon={Thermometer} label="Temp" unit="°C" name="temp" value={formData.vitals.temp} onChange={handleVitalChange} disabled={monitorLocked} />
                        <VitalInput icon={Activity} label="SBP" unit="mmHg" name="sbp" value={formData.vitals.sbp} onChange={handleVitalChange} disabled={monitorLocked} />
                        <VitalInput icon={Activity} label="DBP" unit="mmHg" name="dbp" value={formData.vitals.dbp} onChange={handleVitalChange} disabled={monitorLocked} />
                    </div>

                    <div className="mt-4 bg-slate-50 rounded-lg p-3 border border-slate-200 glucose-input-card">
                        <label className="block text-sm font-medium text-slate-700 mb-1.5">
                            Blood Glucose <span className="text-slate-500">(Optional)</span> | سكر الدم <span className="text-slate-500">(اختياري)</span>
                        </label>
                        <div className="flex items-center gap-2">
                            <input
                                type="number"
                                min="20"
                                max="1000"
                                step="1"
                                name="blood_glucose"
                                value={formData.vitals.blood_glucose}
                                onChange={handleVitalChange}
                                disabled={monitorLocked}
                                placeholder="e.g. 95"
                                className={`w-full border rounded px-3 py-2 text-sm focus:ring-2 focus:ring-teal-500 focus:border-teal-500 ${
                                    getGlucoseClass(formData.vitals.blood_glucose)
                                }`}
                            />
                            <span className="text-xs text-slate-500 whitespace-nowrap">mg/dL</span>
                        </div>
                        {formData.vitals.blood_glucose !== '' && (
                            <small className="block mt-2 text-xs text-slate-600">
                                {getGlucoseMessage(formData.vitals.blood_glucose)}
                            </small>
                        )}
                        <small className="block mt-1 text-[11px] text-slate-500">
                            Recommended for altered mental status, weakness, diabetes, or sepsis concern. |
                            يوصى بقياس السكر عند اضطراب الوعي أو الضعف أو السكري أو الاشتباه بالإنتان.
                        </small>
                    </div>

                    {monitorLocked && (
                        <div className="mt-3">
                            <button
                                type="button"
                                onClick={() => setManualVitalsUnlocked(true)}
                                className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100"
                            >
                                Unlock for manual override | فتح الإدخال اليدوي
                            </button>
                        </div>
                    )}
                    
                    {/* Consciousness Level (ACVPU) */}
                    <div className="mt-4 pt-4 border-t border-slate-200">
                        <SelectField
                            label="Consciousness (ACVPU)"
                            labelAr="مستوى الوعي"
                            value={consciousness}
                            onChange={(e) => setConsciousness(e.target.value)}
                            disabled={monitorLocked}
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
                            <SelectField
                                label="Pain Context"
                                labelAr="سياق الألم"
                                value={formData.pain_context}
                                onChange={(e) => setFormData({ ...formData, pain_context: e.target.value })}
                            >
                                <option value="">Select context... | اختر السياق...</option>
                                <option value="systemic">Systemic / Generalized | ألم عام</option>
                                <option value="chest_pain">Chest Pain | ألم الصدر</option>
                                <option value="abdominal_pain">Abdominal Pain | ألم البطن</option>
                                <option value="renal_colic">Renal Colic | مغص كلوي</option>
                                <option value="sickle_cell_crisis">Sickle Cell Crisis | أزمة منجلية</option>
                                <option value="cancer_pain">Cancer Pain | ألم السرطان</option>
                                <option value="orthopedic">Musculoskeletal / Ortho | ألم عضلي هيكلي</option>
                                <option value="headache">Headache | صداع</option>
                                <option value="other">Other / غير ذلك</option>
                            </SelectField>
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
                        <div className="flex-1">
                            <p className="font-semibold text-red-800">
                                {typeof error === 'string' ? 'Triage Error' : 'Validation Error | خطأ في التحقق'}
                            </p>
                            <p className="text-sm text-red-700 mt-1">
                                {typeof error === 'string' ? error : error.title}
                            </p>
                            {error.titleAr && (
                                <p className="text-sm text-red-600 mt-1" dir="rtl">{error.titleAr}</p>
                            )}
                            {error.suggestion && (
                                <p className="text-sm text-red-600 mt-2 bg-red-100 p-2 rounded">
                                    💡 {error.suggestion}
                                </p>
                            )}
                        </div>
                    </div>
                )}
            </form>
            <ConfirmationDialog
                open={showConfirmDialog}
                title="Confirm Unusual Vital Signs | تأكيد العلامات الحيوية غير المعتادة"
                items={unusualVitals}
                onConfirm={handleConfirmUnusualVitals}
                onCancel={handleCancelUnusualVitals}
            />
        </div>
    );
}
