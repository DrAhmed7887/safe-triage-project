// SectionCard — the canonical "form section" component from the in-product app.
// White, 12px radius, left accent border (4px) in one of {teal, blue, amber, rose,
// purple, emerald}, header strip with icon + bilingual title, body padding 20px.
// This is the ONE place left-accent borders are allowed in the system.

const SECTION_TONES = {
  teal:    { accent: '#159895', bg: '#f0fdfa', icon: '#0d9488' },
  blue:    { accent: '#3b82f6', bg: '#eff6ff', icon: '#2563eb' },
  amber:   { accent: '#f59e0b', bg: '#fffbeb', icon: '#b45309' },
  rose:    { accent: '#f43f5e', bg: '#fff1f2', icon: '#be123c' },
  purple:  { accent: '#8b5cf6', bg: '#f5f3ff', icon: '#6d28d9' },
  emerald: { accent: '#10b981', bg: '#ecfdf5', icon: '#047857' },
};

const SectionCard = ({ tone = 'teal', icon, en, ar, children, action }) => {
  const t = SECTION_TONES[tone] || SECTION_TONES.teal;
  return (
    <section style={{ ...sectionCardStyles.card, borderLeftColor: t.accent }}>
      <header style={{ ...sectionCardStyles.head, background: t.bg }}>
        <div style={sectionCardStyles.headLeft}>
          {icon && (
            <span style={{ ...sectionCardStyles.iconBox, color: t.icon }}>
              <i data-lucide={icon} style={{ width: 18, height: 18 }}></i>
            </span>
          )}
          <div>
            <div style={sectionCardStyles.titleEn}>{en}</div>
            {ar && <div style={sectionCardStyles.titleAr} dir="rtl">{ar}</div>}
          </div>
        </div>
        {action && <div style={sectionCardStyles.action}>{action}</div>}
      </header>
      <div style={sectionCardStyles.body}>{children}</div>
    </section>
  );
};

const sectionCardStyles = {
  card: {
    background: '#fff',
    border: '1px solid #e7edf1',
    borderLeft: '4px solid #159895',
    borderRadius: 12,
    boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
    overflow: 'hidden',
  },
  head: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '12px 18px',
    borderBottom: '1px solid rgba(15,23,42,0.04)',
  },
  headLeft: { display: 'flex', alignItems: 'center', gap: 12 },
  iconBox: {
    width: 32, height: 32, borderRadius: 8,
    background: '#fff',
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
    border: '1px solid rgba(15,23,42,0.06)',
  },
  titleEn: {
    fontFamily: "'Inter', sans-serif", fontWeight: 600, fontSize: 14, color: '#0f172a',
  },
  titleAr: {
    fontFamily: "'Cairo', sans-serif", fontWeight: 500, fontSize: 12.5, color: '#475569',
    marginTop: 1,
  },
  action: {},
  body: { padding: 20 },
};

window.SectionCard = SectionCard;
window.SECTION_TONES = SECTION_TONES;
