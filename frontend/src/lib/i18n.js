/**
 * i18n.js — minimal bilingual helper for Hospital Lite.
 *
 * Two languages only: English ('en') and Arabic ('ar', RTL).
 * Persists choice in localStorage so the iPad keeps it across reloads.
 */

const STORAGE_KEY = 'safeTriage.lang';
const DEFAULT_LANG = 'en';

export const SUPPORTED_LANGS = ['en', 'ar'];

export function getLang() {
    try {
        const v = localStorage.getItem(STORAGE_KEY);
        if (v && SUPPORTED_LANGS.includes(v)) return v;
    } catch {}
    return DEFAULT_LANG;
}

export function setLang(lang) {
    if (!SUPPORTED_LANGS.includes(lang)) return;
    try { localStorage.setItem(STORAGE_KEY, lang); } catch {}
    if (typeof document !== 'undefined') {
        document.documentElement.lang = lang;
        document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
    }
}

export const dirFor = (lang) => (lang === 'ar' ? 'rtl' : 'ltr');

export const STRINGS = {
    app_title:            { en: 'SAFE-Triage · Hospital Lite',          ar: 'سيف-فرز · نسخة المستشفى' },
    decision_support:     { en: 'Decision support only — clinician must confirm.', ar: 'أداة دعم قرار فقط — يجب على الطبيب التأكيد.' },
    new_case:             { en: 'New case',                              ar: 'حالة جديدة' },
    active_queue:         { en: 'Active queue',                          ar: 'طابور الفرز' },
    no_cases:             { en: 'No active cases',                       ar: 'لا توجد حالات نشطة' },
    sign_in_local:        { en: 'Continue',                              ar: 'متابعة' },
    clinician_name:       { en: 'Clinician name',                        ar: 'اسم الطبيب/الممرض' },
    role:                 { en: 'Role',                                  ar: 'الدور' },
    role_nurse:           { en: 'Triage nurse',                          ar: 'ممرض فرز' },
    role_doctor:          { en: 'Doctor',                                ar: 'طبيب' },
    role_supervisor:      { en: 'Supervisor',                            ar: 'مشرف' },
    section_patient:      { en: 'Patient',                               ar: 'بيانات المريض' },
    section_complaint:    { en: 'Chief complaint',                       ar: 'الشكوى الرئيسية' },
    section_vitals:       { en: 'Vital signs',                           ar: 'العلامات الحيوية' },
    section_risks:        { en: 'Risk factors',                          ar: 'عوامل الخطر' },
    patient_id:           { en: 'Patient ID',                            ar: 'رقم المريض' },
    generate_id:          { en: 'Generate',                              ar: 'توليد' },
    patient_name:         { en: 'Full name',                             ar: 'الاسم الكامل' },
    age:                  { en: 'Age',                                   ar: 'العمر' },
    gender:               { en: 'Gender',                                ar: 'النوع' },
    male:                 { en: 'Male',                                  ar: 'ذكر' },
    female:               { en: 'Female',                                ar: 'أنثى' },
    chief_complaint_ph:   { en: 'e.g. severe chest pain for 30 minutes', ar: 'مثال: ألم شديد في الصدر منذ ٣٠ دقيقة' },
    hr:                   { en: 'Heart rate (bpm)',                      ar: 'النبض (نبضة/دقيقة)' },
    rr:                   { en: 'Resp. rate (/min)',                     ar: 'التنفس (مرة/دقيقة)' },
    sbp:                  { en: 'Systolic BP (mmHg)',                    ar: 'الضغط الانقباضي' },
    dbp:                  { en: 'Diastolic BP (mmHg)',                   ar: 'الضغط الانبساطي' },
    spo2:                 { en: 'SpO₂ (%)',                              ar: 'تشبع الأكسجين' },
    temp:                 { en: 'Temperature (°C)',                      ar: 'الحرارة (°م)' },
    consciousness:        { en: 'Consciousness (AVPU)',                  ar: 'مستوى الوعي' },
    pain:                 { en: 'Pain (0–10)',                           ar: 'الألم (٠–١٠)' },
    on_oxygen:            { en: 'On supplemental O₂',                    ar: 'يستخدم أكسجين' },
    is_copd:              { en: 'Known COPD',                            ar: 'مريض انسداد رئوي' },
    is_pregnant:          { en: 'Pregnant',                              ar: 'حامل' },
    immunocompromised:    { en: 'Immunocompromised',                     ar: 'مناعة ضعيفة' },
    run_triage:           { en: 'Suggest triage',                        ar: 'اقتراح الفرز' },
    suggested_triage:     { en: 'Suggested triage',                      ar: 'الفرز المقترح' },
    rules_used:           { en: 'Rules used',                            ar: 'القواعد المستخدمة' },
    red_flags:            { en: 'Red flags',                             ar: 'علامات الخطر' },
    confirm_level:        { en: 'Confirm this level',                    ar: 'تأكيد هذا المستوى' },
    override_level:       { en: 'Override',                              ar: 'تعديل' },
    override_reason_label:{ en: 'Reason for override (required)',        ar: 'سبب التعديل (مطلوب)' },
    override_new_level:   { en: 'New triage level',                      ar: 'المستوى الجديد' },
    save_override:        { en: 'Save override',                         ar: 'حفظ التعديل' },
    cancel:               { en: 'Cancel',                                ar: 'إلغاء' },
    sent_to_queue:        { en: 'Sent to queue',                         ar: 'تم الإرسال للطابور' },
    queue_open:           { en: 'Open patient',                          ar: 'عرض المريض' },
    print_handoff:        { en: 'Print handoff',                         ar: 'طباعة التحويل' },
    export_json:          { en: 'Export JSON',                           ar: 'تصدير JSON' },
    start_new:            { en: 'Start new case',                        ar: 'حالة جديدة' },
    audit_trail:          { en: 'Audit trail',                           ar: 'سجل الإجراءات' },
    audit_suggested:      { en: 'Suggested',                             ar: 'مقترح' },
    audit_confirmed:      { en: 'Confirmed',                             ar: 'مؤكَّد' },
    audit_overridden:     { en: 'Overridden',                            ar: 'مُعدَّل' },
    handoff_title:        { en: 'Triage Handoff Record',                 ar: 'تذكرة تحويل المريض' },
    handoff_generated:    { en: 'Generated',                             ar: 'تاريخ الإصدار' },
    handoff_clinician:    { en: 'Clinician',                             ar: 'الطبيب/الممرض' },
    handoff_final:        { en: 'Final triage level',                    ar: 'مستوى الفرز النهائي' },
    handoff_suggested:    { en: 'System suggested',                      ar: 'اقتراح النظام' },
    missing_complaint:    { en: 'Please enter the chief complaint.',     ar: 'من فضلك أدخل الشكوى الرئيسية.' },
    missing_age:          { en: 'Please enter the patient age.',         ar: 'من فضلك أدخل عمر المريض.' },
    missing_vitals_note:  { en: 'Some vitals are missing — the suggestion is conservative. Please complete them.', ar: 'بعض العلامات الحيوية ناقصة — الاقتراح متحفظ. من فضلك أكمل البيانات.' },
    en_short:             { en: 'EN',                                    ar: 'EN' },
    ar_short:             { en: 'AR',                                    ar: 'AR' },

    // Engine source
    engine_python:        { en: 'Online · backend engine',                ar: 'متصل · المحرك الرسمي' },
    engine_fallback:      { en: 'Offline fallback · clinician must verify', ar: 'وضع غير متصل · يجب التحقق من قِبَل الطبيب' },
    engine_python_help:   { en: 'Validated SAFE-Triage engine (Python).', ar: 'محرك سيف-فرز الموثق (Python).' },
    engine_fallback_help: { en: 'Backend unreachable — this suggestion came from the browser fallback engine. It is best-effort, not benchmark-validated. Confirm with caution.', ar: 'تعذّر الوصول للخادم — هذا الاقتراح من المحرك الاحتياطي في المتصفح. اقتراح أولي غير مُختبر إكلينيكياً، يرجى التحقق بحرص.' },
    running_triage:       { en: 'Running deterministic triage…',          ar: 'جارٍ تشغيل الفرز...' },
    engine_source_label:  { en: 'Engine source',                          ar: 'مصدر المحرك' },
};

export function t(key, lang) {
    const entry = STRINGS[key];
    if (!entry) return key;
    return entry[lang] ?? entry.en ?? key;
}
