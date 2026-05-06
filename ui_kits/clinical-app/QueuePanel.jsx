// QueuePanel — left rail showing active cases sorted by acuity.

const QUEUE_DEMO = [
  { id: 'P-2841', age: 58, sex: 'M', complaint: 'Chest pain, radiating', complaintAr: 'ألم في الصدر', esi: 2, wait: '2 min', flags: ['Diabetic'] },
  { id: 'P-2839', age: 34, sex: 'F', complaint: 'Severe abdominal pain', complaintAr: 'ألم بطن شديد', esi: 3, wait: '14 min', flags: ['Pregnant'] },
  { id: 'P-2837', age: 71, sex: 'M', complaint: 'Confused, slurred speech', complaintAr: 'تشوش وكلام متلعثم', esi: 1, wait: '0 min', flags: ['Stroke?'], pulse: true },
  { id: 'P-2836', age: 22, sex: 'M', complaint: 'Twisted ankle, limping', complaintAr: 'التواء في الكاحل', esi: 4, wait: '38 min' },
  { id: 'P-2834', age: 45, sex: 'F', complaint: 'Sore throat, mild fever', complaintAr: 'التهاب حلق', esi: 5, wait: '52 min' },
];

const QueuePanel = ({ activeId, onSelect }) => {
  return (
    <aside style={qpStyles.aside}>
      <div style={qpStyles.head}>
        <div style={qpStyles.title}>
          Active Queue
          <span style={qpStyles.titleSep}>|</span>
          <span dir="rtl" style={qpStyles.titleAr}>طابور الفرز</span>
        </div>
        <span style={qpStyles.count}>{QUEUE_DEMO.length}</span>
      </div>
      <div style={qpStyles.filters}>
        <button style={{ ...qpStyles.filter, ...qpStyles.filterOn }}>All</button>
        <button style={qpStyles.filter}>1–2 critical</button>
        <button style={qpStyles.filter}>Awaiting confirm</button>
      </div>
      <div style={qpStyles.list}>
        {QUEUE_DEMO.map((p) => {
          const g = ESI_GRADIENTS[p.esi];
          const isActive = activeId === p.id;
          return (
            <button key={p.id} onClick={() => onSelect && onSelect(p.id)}
              style={{ ...qpStyles.row, ...(isActive ? qpStyles.rowActive : {}) }}>
              <span style={{
                ...qpStyles.esiBadge,
                background: `linear-gradient(135deg, ${g.from}, ${g.to})`,
                animation: p.pulse ? 'st-pulse-red 2s ease-out infinite' : undefined,
              }}>{p.esi}</span>
              <div style={qpStyles.body}>
                <div style={qpStyles.idRow}>
                  <span style={qpStyles.id}>{p.id}</span>
                  <span style={qpStyles.demo}>{p.age}{p.sex}</span>
                  <span style={qpStyles.wait}>{p.wait}</span>
                </div>
                <div style={qpStyles.complaint}>{p.complaint}</div>
                <div style={qpStyles.complaintAr} dir="rtl">{p.complaintAr}</div>
                {p.flags && (
                  <div style={qpStyles.flags}>
                    {p.flags.map((f) => <span key={f} style={qpStyles.flag}>{f}</span>)}
                  </div>
                )}
              </div>
            </button>
          );
        })}
      </div>
      <div style={qpStyles.foot}>
        <button style={qpStyles.newCase}>
          <i data-lucide="plus" style={{ width: 16, height: 16 }}></i>
          New case <span style={{ color: '#cbd5e1', fontWeight: 400 }}>|</span>
          <span dir="rtl" style={{ fontFamily: "'Cairo', sans-serif" }}>حالة جديدة</span>
        </button>
      </div>
    </aside>
  );
};

const qpStyles = {
  aside: {
    background: '#fff', borderRadius: 16, border: '1px solid #e7edf1',
    boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
    display: 'flex', flexDirection: 'column',
    height: 'fit-content',
    overflow: 'hidden',
  },
  head: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 18px', borderBottom: '1px solid #e7edf1' },
  title: { fontFamily: "'Inter', sans-serif", fontWeight: 700, fontSize: 14, color: '#0f172a', display: 'inline-flex', alignItems: 'baseline', gap: 6 },
  titleSep: { color: '#cbd5e1', fontWeight: 400 },
  titleAr: { fontFamily: "'Cairo', sans-serif", fontWeight: 600, fontSize: 13, color: '#475569' },
  count: { fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, fontWeight: 700, background: '#f1f5f9', color: '#475569', padding: '3px 9px', borderRadius: 999 },
  filters: { display: 'flex', gap: 6, padding: '10px 14px', borderBottom: '1px solid #e7edf1', flexWrap: 'wrap' },
  filter: { background: '#fff', border: '1px solid #e7edf1', color: '#475569', padding: '5px 10px', borderRadius: 999, fontSize: 11.5, fontWeight: 500, fontFamily: "'Inter', sans-serif", cursor: 'pointer' },
  filterOn: { background: '#0f172a', color: '#fff', borderColor: '#0f172a' },
  list: { display: 'flex', flexDirection: 'column' },
  row: {
    display: 'flex', gap: 12, padding: '14px 16px',
    background: '#fff', border: 'none', borderTop: '1px solid #f1f5f9',
    textAlign: 'left', cursor: 'pointer',
    fontFamily: "'Inter', sans-serif",
  },
  rowActive: { background: '#f0fdfa', borderLeft: '3px solid #0d9488', paddingLeft: 13 },
  esiBadge: {
    width: 32, height: 32, borderRadius: 10,
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
    color: '#fff', fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 800, fontSize: 16,
    flexShrink: 0,
    boxShadow: '0 4px 10px rgba(15,23,42,0.12)',
  },
  body: { flex: 1, minWidth: 0 },
  idRow: { display: 'flex', gap: 8, alignItems: 'baseline' },
  id: { fontFamily: "'IBM Plex Mono', monospace", fontWeight: 600, fontSize: 12, color: '#0f172a' },
  demo: { fontSize: 11, color: '#64748b' },
  wait: { marginLeft: 'auto', fontSize: 11, color: '#64748b', fontFamily: "'IBM Plex Mono', monospace" },
  complaint: { fontSize: 13, color: '#0f172a', marginTop: 2, fontWeight: 500 },
  complaintAr: { fontFamily: "'Cairo', sans-serif", fontSize: 12, color: '#64748b', marginTop: 1 },
  flags: { marginTop: 6, display: 'flex', gap: 4, flexWrap: 'wrap' },
  flag: { background: '#fff7ed', color: '#9a3412', border: '1px solid #fed7aa', borderRadius: 999, padding: '1px 8px', fontSize: 10.5, fontWeight: 600 },

  foot: { padding: 12, borderTop: '1px solid #e7edf1' },
  newCase: {
    width: '100%', display: 'inline-flex', justifyContent: 'center', alignItems: 'center', gap: 8,
    background: '#0d9488', color: '#fff', border: 'none', borderRadius: 10,
    padding: '11px 14px', cursor: 'pointer',
    fontFamily: "'Inter', sans-serif", fontSize: 13, fontWeight: 600,
  },
};

window.QueuePanel = QueuePanel;
