// TriageForm — left column of the dashboard.
// Patient meta, chief complaint (bilingual textarea), vitals row.

const TriageForm = ({ form, onChange }) => {
  const set = (k) => (e) => onChange({ ...form, [k]: e.target.value });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <SectionCard tone="teal" icon="user-round" en="Patient" ar="بيانات المريض">
        <div style={tfStyles.grid2}>
          <Field label="Patient ID" ar="رقم المريض">
            <input style={tfStyles.input} value={form.id} onChange={set('id')} />
          </Field>
          <Field label="Age" ar="العمر">
            <input style={tfStyles.input} value={form.age} onChange={set('age')} />
          </Field>
          <Field label="Sex" ar="الجنس">
            <Segmented value={form.sex} options={[{v:'M',l:'Male'},{v:'F',l:'Female'}]} onChange={(v)=>onChange({...form, sex:v})} />
          </Field>
          <Field label="Pregnant" ar="حامل" hideOn={form.sex !== 'F'}>
            <Segmented value={form.pregnant} options={[{v:'no',l:'No'},{v:'yes',l:'Yes'},{v:'unk',l:'Unknown'}]} onChange={(v)=>onChange({...form, pregnant:v})}/>
          </Field>
        </div>
        <div style={{ marginTop: 12 }}>
          <Field label="Comorbidities" ar="أمراض مزمنة">
            <div style={tfStyles.chipRow}>
              {['Diabetes','Hypertension','CKD','COPD','CHF','Asthma'].map((c)=>{
                const on = form.comorbid?.includes(c);
                return (
                  <button key={c} type="button"
                    onClick={()=> onChange({ ...form, comorbid: on ? form.comorbid.filter(x=>x!==c) : [...(form.comorbid||[]), c] })}
                    style={{ ...tfStyles.chip, ...(on ? tfStyles.chipOn : {}) }}>
                    {on && '✓ '}{c}
                  </button>
                );
              })}
            </div>
          </Field>
        </div>
      </SectionCard>

      <SectionCard tone="blue" icon="message-square" en="Chief Complaint" ar="الشكوى الرئيسية"
        action={<span style={tfStyles.helpHint}>Type in English or العربية</span>}>
        <textarea
          style={tfStyles.textarea}
          value={form.complaint}
          onChange={set('complaint')}
          aria-label="Chief complaint — enter in English or العربية"
          placeholder="e.g. Chest pain radiating to left arm for 30 minutes  ·  ألم في الصدر يمتد للذراع اليسرى" />
        <div style={tfStyles.detected}>
          <span style={tfStyles.detLabel}>Extracted concepts</span>
          <span style={tfStyles.snomed}>SNOMED · 29857009 · Chest pain</span>
          <span style={tfStyles.snomed}>SNOMED · 53057004 · Diaphoresis</span>
          <span style={tfStyles.snomed}>SNOMED · 8765009 · Radiation to arm</span>
        </div>
      </SectionCard>

      <SectionCard tone="amber" icon="heart-pulse" en="Vitals" ar="العلامات الحيوية">
        <div style={tfStyles.vitals}>
          <Vital label="HR"   unit="bpm"  value={form.hr}    onChange={set('hr')}    flag={Number(form.hr)>110}/>
          <Vital label="BP"   unit="mmHg" value={form.bp}    onChange={set('bp')}/>
          <Vital label="SpO₂" unit="%"    value={form.spo2}  onChange={set('spo2')}  flag={Number(form.spo2)<93}/>
          <Vital label="Temp" unit="°C"   value={form.temp}  onChange={set('temp')}/>
          <Vital label="RR"   unit="/min" value={form.rr}    onChange={set('rr')}/>
          <Vital label="GCS"  unit="/15"  value={form.gcs}   onChange={set('gcs')}/>
        </div>
        <div style={tfStyles.news2}>
          <span style={tfStyles.news2Label}>NEWS2</span>
          <span style={tfStyles.news2Score}>6 · Medium risk</span>
          <span style={tfStyles.news2Hint}>Score auto-computes from vitals.</span>
        </div>
      </SectionCard>
    </div>
  );
};

const Field = ({ label, ar, hideOn, children }) => {
  if (hideOn) return null;
  return (
    <label style={tfStyles.field}>
      <span style={tfStyles.label}>
        {label}
        {ar && <>
          <span style={tfStyles.labelSep}>|</span>
          <span style={tfStyles.labelAr} dir="rtl">{ar}</span>
        </>}
      </span>
      {children}
    </label>
  );
};

const Segmented = ({ value, options, onChange }) => (
  <div style={tfStyles.seg}>
    {options.map((o)=>(
      <button key={o.v} type="button" onClick={()=>onChange(o.v)}
        style={{ ...tfStyles.segBtn, ...(value === o.v ? tfStyles.segBtnOn : {}) }}>
        {o.l}
      </button>
    ))}
  </div>
);

const Vital = ({ label, unit, value, onChange, flag }) => (
  <label style={tfStyles.vital}>
    <span style={tfStyles.vitalLabel}>{label} <span style={tfStyles.vitalUnit}>{unit}</span></span>
    <input
      value={value}
      onChange={onChange}
      aria-label={`${label} (${unit})`}
      aria-invalid={flag ? 'true' : undefined}
      style={{ ...tfStyles.vitalInput, ...(flag ? tfStyles.vitalFlag : {}) }} />
    {flag && <span style={tfStyles.vitalFlagText}>⚠ Outside normal</span>}
  </label>
);

const tfStyles = {
  grid2: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 },
  field: { display: 'flex', flexDirection: 'column', gap: 6 },
  label: {
    display: 'inline-flex', alignItems: 'baseline', gap: 6,
    fontFamily: "'Inter', sans-serif", fontSize: 12, fontWeight: 600, color: '#334155',
  },
  labelSep: { color: '#cbd5e1', fontWeight: 400 },
  labelAr: { fontFamily: "'Cairo', sans-serif", fontSize: 12, color: '#64748b' },
  input: {
    width: '100%', padding: '10px 12px',
    border: '1px solid #cbd5e1', borderRadius: 10,
    fontFamily: "'Inter', sans-serif", fontSize: 14, color: '#0f172a',
    background: '#fff', outline: 'none',
  },
  textarea: {
    width: '100%', minHeight: 96, padding: '12px 14px',
    border: '1px solid #cbd5e1', borderRadius: 10,
    fontFamily: "'Inter', sans-serif", fontSize: 14, lineHeight: 1.55, color: '#0f172a',
    background: '#fff', outline: 'none', resize: 'vertical',
  },
  helpHint: { fontFamily: "'Inter', sans-serif", fontSize: 11, color: '#64748b' },
  detected: { display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 12, alignItems: 'center' },
  detLabel: {
    fontFamily: "'Inter', sans-serif", fontSize: 11, fontWeight: 700,
    letterSpacing: 0.12, textTransform: 'uppercase', color: '#64748b',
  },
  snomed: {
    fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, fontWeight: 600,
    background: '#0f766e', color: '#fff', padding: '3px 8px', borderRadius: 999,
  },
  chipRow: { display: 'flex', flexWrap: 'wrap', gap: 6 },
  chip: {
    background: '#fff', color: '#475569',
    border: '1px solid #cbd5e1', borderRadius: 999,
    padding: '6px 12px', fontSize: 12.5, fontWeight: 500, cursor: 'pointer',
    fontFamily: "'Inter', sans-serif",
  },
  chipOn: { background: '#0d9488', color: '#fff', borderColor: '#0d9488' },
  seg: {
    display: 'inline-flex', background: '#f1f5f9', padding: 3, borderRadius: 10,
    border: '1px solid #e2e8f0',
  },
  segBtn: {
    background: 'transparent', border: 'none', cursor: 'pointer',
    padding: '6px 12px', borderRadius: 8,
    fontFamily: "'Inter', sans-serif", fontSize: 12.5, fontWeight: 600, color: '#475569',
  },
  segBtnOn: { background: '#fff', color: '#0f172a', boxShadow: '0 1px 2px rgba(0,0,0,0.06)' },
  vitals: { display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 12 },
  vital: { display: 'flex', flexDirection: 'column', gap: 6 },
  vitalLabel: {
    fontFamily: "'Inter', sans-serif", fontSize: 12, fontWeight: 600, color: '#334155',
    display: 'flex', justifyContent: 'space-between',
  },
  vitalUnit: { color: '#94a3b8', fontWeight: 500, fontFamily: "'IBM Plex Mono', monospace", fontSize: 11 },
  vitalInput: {
    padding: '10px 12px', border: '1px solid #cbd5e1', borderRadius: 10,
    fontFamily: "'IBM Plex Mono', monospace", fontSize: 14, fontWeight: 600, color: '#0f172a',
    background: '#fff', outline: 'none', textAlign: 'center',
  },
  vitalFlag: { borderColor: '#ef4444', background: '#fef2f2', color: '#b91c1c' },
  vitalFlagText: { fontSize: 11, color: '#b91c1c', fontFamily: "'Inter', sans-serif" },
  news2: {
    marginTop: 14,
    display: 'flex', alignItems: 'center', gap: 10,
    background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 10, padding: '10px 14px',
  },
  news2Label: {
    fontFamily: "'Inter', sans-serif", fontSize: 11, fontWeight: 700,
    letterSpacing: 0.12, color: '#92400e', textTransform: 'uppercase',
  },
  news2Score: {
    fontFamily: "'IBM Plex Mono', monospace", fontSize: 13, fontWeight: 700, color: '#92400e',
  },
  news2Hint: { fontFamily: "'Inter', sans-serif", fontSize: 12, color: '#92400e', opacity: 0.85 },
};

window.TriageForm = TriageForm;
