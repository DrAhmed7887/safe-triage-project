// WorkupCard — recommended diagnostics + ICD-10 / SNOMED-CT codes panel.

const WorkupCard = () => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <SectionCard tone="purple" icon="clipboard-list" en="Recommended Workup" ar="الفحوصات المطلوبة">
        <ul style={wkStyles.list}>
          {[
            { label: '12-lead ECG',           ar: 'تخطيط القلب',          urgency: 'STAT', icon: 'heart-pulse' },
            { label: 'High-sensitivity Troponin (T)', ar: 'تروبونين',     urgency: 'STAT', icon: 'syringe' },
            { label: 'CBC, U&E, glucose',     ar: 'تحاليل دم أساسية',     urgency: '< 30 min', icon: 'flask-conical' },
            { label: 'Portable chest X-ray',  ar: 'أشعة على الصدر',       urgency: '< 60 min', icon: 'scan-line' },
          ].map((r) => (
            <li key={r.label} style={wkStyles.row}>
              <span style={wkStyles.iconBox}>
                <i data-lucide={r.icon} style={{ width: 16, height: 16, color: '#6d28d9' }}></i>
              </span>
              <div style={wkStyles.body}>
                <div style={wkStyles.label}>{r.label}</div>
                <div style={wkStyles.labelAr} dir="rtl">{r.ar}</div>
              </div>
              <span style={{
                ...wkStyles.urgency,
                ...(r.urgency === 'STAT' ? wkStyles.urgencyStat : {}),
              }}>{r.urgency}</span>
            </li>
          ))}
        </ul>
        <div style={wkStyles.disclaimer}>
          🧪 Decision support only. Order according to local protocols.
        </div>
      </SectionCard>

      <SectionCard tone="rose" icon="stethoscope" en="Differential Diagnoses" ar="التشخيصات المحتملة"
        action={<span style={wkStyles.aiTag}>AI-suggested · MedGemma</span>}>
        <div style={wkStyles.dxList}>
          {[
            { name: 'Acute coronary syndrome', icd: 'I24.9', snomed: '394659003', conf: 86 },
            { name: 'Unstable angina',          icd: 'I20.0', snomed: '4557003',   conf: 64 },
            { name: 'Aortic dissection',        icd: 'I71.0', snomed: '308546005', conf: 12, redflag: true },
          ].map((d) => (
            <div key={d.icd} style={wkStyles.dxRow}>
              <div style={wkStyles.dxName}>
                {d.redflag && <span style={wkStyles.redflag}>🔴 RED FLAG</span>}
                <span>{d.name}</span>
              </div>
              <div style={wkStyles.dxCodes}>
                <span style={wkStyles.icdChip}>ICD-10 · {d.icd}</span>
                <span style={wkStyles.snomedChip}>SNOMED · {d.snomed}</span>
              </div>
              <div style={wkStyles.dxConfWrap}>
                <div style={wkStyles.dxBar}>
                  <div style={{ ...wkStyles.dxBarFill, width: `${d.conf}%` }}></div>
                </div>
                <span style={wkStyles.dxConf}>{d.conf}%</span>
              </div>
            </div>
          ))}
        </div>
      </SectionCard>

      <SectionCard tone="emerald" icon="message-circle-question" en="Ask Patient" ar="اسأل المريض">
        <div style={wkStyles.askList}>
          {[
            { en: 'Any pressure or tightness?',          ar: 'حاسس بضغط أو ضيق؟' },
            { en: 'Pain radiating to your arm or jaw?',  ar: 'الألم بيمتد للذراع أو الفك؟' },
            { en: 'Sweating, nausea, or shortness of breath?', ar: 'عرق أو غثيان أو ضيق في النفس؟' },
          ].map((q) => (
            <div key={q.en} style={wkStyles.askRow}>
              <i data-lucide="message-circle" style={{ width: 14, height: 14, color: '#047857', marginTop: 4 }}></i>
              <div>
                <div style={wkStyles.askEn}>{q.en}</div>
                <div style={wkStyles.askAr} dir="rtl">{q.ar}</div>
              </div>
            </div>
          ))}
        </div>
      </SectionCard>
    </div>
  );
};

const wkStyles = {
  list: { listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 8 },
  row: { display: 'flex', alignItems: 'center', gap: 12, padding: '10px 12px', background: '#faf5ff', border: '1px solid #ede9fe', borderRadius: 10 },
  iconBox: { width: 32, height: 32, borderRadius: 8, background: '#fff', border: '1px solid #ede9fe', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  body: { flex: 1, minWidth: 0 },
  label: { fontFamily: "'Inter', sans-serif", fontSize: 13.5, fontWeight: 600, color: '#0f172a' },
  labelAr: { fontFamily: "'Cairo', sans-serif", fontSize: 12.5, color: '#64748b', marginTop: 1 },
  urgency: { fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, fontWeight: 700, color: '#5b21b6', background: '#fff', border: '1px solid #ede9fe', borderRadius: 999, padding: '3px 10px' },
  urgencyStat: { background: '#fef2f2', color: '#b91c1c', border: '1px solid #fecaca' },
  disclaimer: { marginTop: 12, fontFamily: "'Inter', sans-serif", fontSize: 12, color: '#64748b' },

  aiTag: { fontFamily: "'Inter', sans-serif", fontSize: 11, fontWeight: 600, color: '#be123c', background: '#fff1f2', padding: '3px 8px', borderRadius: 999, border: '1px solid #fecdd3' },
  dxList: { display: 'flex', flexDirection: 'column', gap: 12 },
  dxRow: { display: 'grid', gridTemplateColumns: 'minmax(0, 1.4fr) minmax(0, 1fr) minmax(0, 1fr)', gap: 10, alignItems: 'center' },
  dxName: { fontFamily: "'Inter', sans-serif", fontSize: 13.5, fontWeight: 600, color: '#0f172a', display: 'inline-flex', alignItems: 'center', gap: 6, flexWrap: 'wrap', minWidth: 0 },
  redflag: { fontFamily: "'Inter', sans-serif", fontSize: 10, fontWeight: 700, letterSpacing: 0.08, color: '#fff', background: '#dc2626', padding: '2px 7px', borderRadius: 4 },
  dxCodes: { display: 'flex', gap: 6, flexWrap: 'wrap', minWidth: 0 },
  icdChip: { fontFamily: "'IBM Plex Mono', monospace", fontSize: 10.5, fontWeight: 600, background: '#6d28d9', color: '#fff', padding: '2px 8px', borderRadius: 999 },
  snomedChip: { fontFamily: "'IBM Plex Mono', monospace", fontSize: 10.5, fontWeight: 600, background: '#0f766e', color: '#fff', padding: '2px 8px', borderRadius: 999 },
  dxConfWrap: { display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 },
  dxBar: { position: 'relative', height: 8, background: '#fff1f2', borderRadius: 999, overflow: 'hidden', flex: 1 },
  dxBarFill: { height: '100%', background: 'linear-gradient(90deg, #f43f5e, #be123c)', borderRadius: 999 },
  dxConf: { fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: '#475569', fontWeight: 600, flexShrink: 0 },

  askList: { display: 'flex', flexDirection: 'column', gap: 10 },
  askRow: { display: 'flex', gap: 10, padding: '8px 12px', background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 10 },
  askEn: { fontFamily: "'Inter', sans-serif", fontSize: 13, color: '#0f172a' },
  askAr: { fontFamily: "'Cairo', sans-serif", fontSize: 13, color: '#475569', marginTop: 1 },
};

window.WorkupCard = WorkupCard;
