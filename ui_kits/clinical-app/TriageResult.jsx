// TriageResult — the ESI result hero. Full-width gradient block, 6xl level number,
// EN/AR labels stacked, confidence + audit chips below.

const ESI_GRADIENTS = {
  1: { from: '#ef4444', to: '#dc2626', name: 'Resuscitation', ar: 'إنعاش', desc: 'Immediate, life-threatening. Resuscitation room now.' },
  2: { from: '#f97316', to: '#ea580c', name: 'Emergent',      ar: 'طوارئ',  desc: 'High-risk presentation. Treat within 10 minutes.' },
  3: { from: '#eab308', to: '#ca8a04', name: 'Urgent',        ar: 'عاجل',   desc: 'Multiple resources expected. Within 30 minutes.' },
  4: { from: '#22c55e', to: '#16a34a', name: 'Less Urgent',   ar: 'أقل إلحاحاً', desc: 'One resource. Within 60 minutes.' },
  5: { from: '#3b82f6', to: '#2563eb', name: 'Non-Urgent',    ar: 'غير عاجل', desc: 'No resources expected. Schedule appropriately.' },
};

const TriageResult = ({ level = 2, confidence = 92, onConfirm, onOverride, confirmed }) => {
  const g = ESI_GRADIENTS[level];
  return (
    <div style={trStyles.wrap}>
      <div style={{ ...trStyles.hero, background: `linear-gradient(135deg, ${g.from} 0%, ${g.to} 100%)` }}>
        <div style={trStyles.heroLeft}>
          <div style={trStyles.eyebrow}>RECOMMENDED ESI LEVEL</div>
          <div style={trStyles.bigNum}>{level}</div>
          <div style={trStyles.names}>
            <span style={trStyles.nameEn}>{g.name}</span>
            <span style={trStyles.nameAr} dir="rtl">{g.ar}</span>
          </div>
          <p style={trStyles.desc}>{g.desc}</p>
        </div>
        <div style={trStyles.heroRight}>
          <div style={trStyles.confBox}>
            <div style={trStyles.confLabel}>AI Confidence</div>
            <div style={trStyles.confVal}>{confidence}%</div>
            <div style={trStyles.confBar}>
              <div style={{ ...trStyles.confFill, width: `${confidence}%` }}></div>
            </div>
          </div>
          <div style={trStyles.metaRow}>
            <span style={trStyles.metaChip}>NEWS2 · 6</span>
            <span style={trStyles.metaChip}>RR-flag</span>
            <span style={trStyles.metaChip}>Det. engine v2.4</span>
          </div>
        </div>
      </div>

      <div style={trStyles.actionBar}>
        {confirmed ? (
          <div style={trStyles.confirmedRow}>
            <span style={trStyles.confirmedTag}>✅ Confirmed by Dr. Hassan · 14:32</span>
            <span style={trStyles.confirmedHint}>
              Dispatch alert sent to on-call physician.
              <span style={{ color: '#cbd5e1', margin: '0 6px' }}>|</span>
              <span dir="rtl" style={{ fontFamily: "'Cairo', sans-serif" }}>تم إرسال التنبيه</span>
            </span>
          </div>
        ) : (
          <>
            <button style={trStyles.btnConfirm} onClick={onConfirm}>
              <i data-lucide="check" style={{ width: 16, height: 16 }}></i>
              Confirm ESI {level}
              <span style={trStyles.btnSep}>|</span>
              <span style={trStyles.btnAr} dir="rtl">تأكيد</span>
            </button>
            <button style={trStyles.btnOverride} onClick={onOverride}>
              Override
              <span style={trStyles.btnSep}>|</span>
              <span style={trStyles.btnAr} dir="rtl">تجاوز</span>
            </button>
            <span style={trStyles.supervisorNote}>
              ⚠ Downgrades require supervisor approval.
            </span>
          </>
        )}
      </div>

      <div style={trStyles.gahar}>
        🛡 Designed to Align with GAHAR Safety Requirements
        <span style={{ color: '#94a3b8', margin: '0 8px' }}>|</span>
        <span dir="rtl" style={{ fontFamily: "'Cairo', sans-serif", fontWeight: 600 }}>مصمم وفقاً لمتطلبات سلامة الجهار</span>
      </div>
    </div>
  );
};

const trStyles = {
  wrap: {
    background: '#fff', border: '1px solid #e7edf1', borderRadius: 16,
    overflow: 'hidden',
    boxShadow: '0 18px 36px rgba(15,23,42,0.06)',
  },
  hero: {
    color: '#fff', padding: '28px 32px',
    display: 'flex', flexWrap: 'wrap', gap: 24,
    alignItems: 'center', justifyContent: 'space-between',
  },
  heroLeft: { flex: '1 1 260px', minWidth: 0 },
  eyebrow: {
    fontFamily: "'Inter', sans-serif", fontSize: 11, fontWeight: 700,
    letterSpacing: 0.18, textTransform: 'uppercase', opacity: 0.92,
  },
  bigNum: {
    fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: 96, fontWeight: 800,
    lineHeight: 1, marginTop: 4, letterSpacing: -3,
  },
  names: { display: 'flex', alignItems: 'baseline', gap: 12, marginTop: 4 },
  nameEn: { fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: 26, fontWeight: 800, letterSpacing: -0.5 },
  nameAr: { fontFamily: "'Cairo', sans-serif", fontSize: 22, fontWeight: 700, opacity: 0.92 },
  desc: { fontFamily: "'Inter', sans-serif", fontSize: 14, lineHeight: 1.6, marginTop: 12, maxWidth: 360, opacity: 0.95 },

  heroRight: { display: 'flex', flexDirection: 'column', gap: 14, alignItems: 'stretch', flex: '0 1 240px', minWidth: 200 },
  confBox: {
    width: '100%', background: 'rgba(255,255,255,0.14)', backdropFilter: 'blur(10px)',
    border: '1px solid rgba(255,255,255,0.22)', borderRadius: 14,
    padding: '14px 16px', boxSizing: 'border-box',
  },
  confLabel: { fontSize: 11, fontWeight: 700, letterSpacing: 0.14, textTransform: 'uppercase', opacity: 0.9 },
  confVal: { fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: 32, fontWeight: 800, lineHeight: 1, marginTop: 4 },
  confBar: { marginTop: 10, height: 6, background: 'rgba(255,255,255,0.2)', borderRadius: 999, overflow: 'hidden' },
  confFill: { height: '100%', background: '#fff', borderRadius: 999 },

  metaRow: { display: 'flex', flexWrap: 'wrap', gap: 6, justifyContent: 'flex-end' },
  metaChip: {
    fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, fontWeight: 600,
    color: '#fff', background: 'rgba(0,0,0,0.16)',
    padding: '3px 10px', borderRadius: 999,
    border: '1px solid rgba(255,255,255,0.18)',
  },

  actionBar: {
    display: 'flex', alignItems: 'center', gap: 12,
    padding: '16px 24px',
    background: '#fff',
    borderTop: '1px solid #e7edf1',
    flexWrap: 'wrap',
  },
  btnConfirm: {
    display: 'inline-flex', alignItems: 'center', gap: 8,
    background: '#0f172a', color: '#fff', border: 'none', borderRadius: 10,
    padding: '11px 20px', cursor: 'pointer',
    fontFamily: "'Inter', sans-serif", fontWeight: 600, fontSize: 14,
  },
  btnOverride: {
    background: '#fff', color: '#475569', border: '1px solid #cbd5e1',
    borderRadius: 10, padding: '11px 18px', cursor: 'pointer',
    fontFamily: "'Inter', sans-serif", fontWeight: 600, fontSize: 14,
  },
  btnSep: { color: 'rgba(255,255,255,0.4)', margin: '0 4px', fontWeight: 400 },
  btnAr: { fontFamily: "'Cairo', sans-serif", fontWeight: 600 },
  supervisorNote: {
    marginLeft: 'auto', fontSize: 12, color: '#92400e',
    fontFamily: "'Inter', sans-serif",
  },
  confirmedRow: { display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' },
  confirmedTag: {
    background: '#ecfdf5', color: '#065f46',
    border: '1px solid #a7f3d0', borderRadius: 10,
    padding: '8px 14px',
    fontFamily: "'Inter', sans-serif", fontSize: 13, fontWeight: 600,
  },
  confirmedHint: { fontFamily: "'Inter', sans-serif", fontSize: 12, color: '#475569' },

  gahar: {
    background: '#0f766e', color: '#fff',
    padding: '8px 24px',
    fontFamily: "'Inter', sans-serif", fontSize: 12, fontWeight: 500, textAlign: 'center',
  },
};

window.TriageResult = TriageResult;
window.ESI_GRADIENTS = ESI_GRADIENTS;
