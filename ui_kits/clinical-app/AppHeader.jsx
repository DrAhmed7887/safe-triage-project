// AppShell — top header for the clinical dashboard.
// 64px sticky header, white, hairline border. Logo block (40×40) + bilingual title +
// nav tabs + on-call clinician avatar.

const AppHeader = ({ active = 'triage' }) => {
  const tabs = [
    { id: 'triage',     en: 'Triage',           ar: 'فرز' },
    { id: 'queue',      en: 'Queue',            ar: 'الطابور', badge: 14 },
    { id: 'analytics',  en: 'Analytics',        ar: 'التحليلات' },
    { id: 'kb',         en: 'Knowledge',        ar: 'المعرفة' },
  ];
  return (
    <header style={appHeaderStyles.bar}>
      <div style={appHeaderStyles.inner}>
        <div style={appHeaderStyles.brand}>
          <span style={appHeaderStyles.logo}>
            <i data-lucide="activity" style={{ width: 22, height: 22, color: '#fff' }}></i>
          </span>
          <div>
            <div style={appHeaderStyles.brandName}>SAFE-Triage</div>
            <div style={appHeaderStyles.brandSub}>
              ED · Cairo University Hospital
              <span style={{ color: '#cbd5e1', margin: '0 6px' }}>|</span>
              <span dir="rtl" style={{ fontFamily: "'Cairo', sans-serif" }}>قسم الطوارئ</span>
            </div>
          </div>
        </div>

        <nav style={appHeaderStyles.tabs}>
          {tabs.map((t) => (
            <a key={t.id} href="#"
               style={{ ...appHeaderStyles.tab, ...(active === t.id ? appHeaderStyles.tabActive : {}) }}>
              <span>{t.en}</span>
              <span style={appHeaderStyles.tabAr} dir="rtl">{t.ar}</span>
              {t.badge && <span style={appHeaderStyles.badge}>{t.badge}</span>}
            </a>
          ))}
        </nav>

        <div style={appHeaderStyles.right}>
          <button style={appHeaderStyles.iconBtn} aria-label="alerts">
            <i data-lucide="bell" style={{ width: 18, height: 18, color: '#475569' }}></i>
            <span style={appHeaderStyles.notifDot}></span>
          </button>
          <div style={appHeaderStyles.user}>
            <div style={appHeaderStyles.avatar} role="img" aria-label="Dr. Salma Hassan">SH</div>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={appHeaderStyles.userName}>Dr. Salma Hassan</span>
              <span style={appHeaderStyles.userRole}>Triage Nurse · On call</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

const appHeaderStyles = {
  bar: {
    position: 'sticky', top: 0, zIndex: 30,
    background: '#fff',
    borderBottom: '1px solid #e7edf1',
    boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
  },
  inner: {
    maxWidth: 1280, margin: '0 auto', padding: '0 24px', minHeight: 64,
    display: 'flex', alignItems: 'center', flexWrap: 'wrap', rowGap: 8, gap: 16,
  },
  brand: { display: 'flex', alignItems: 'center', gap: 12, minWidth: 0, flex: '0 1 auto' },
  logo: {
    width: 40, height: 40, borderRadius: 12, background: '#0d9488',
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
    boxShadow: '0 6px 14px rgba(13,148,136,0.25)',
  },
  brandName: {
    fontFamily: "'Inter', sans-serif", fontWeight: 700, fontSize: 16, color: '#0f172a',
    letterSpacing: -0.2,
  },
  brandSub: { fontFamily: "'Inter', sans-serif", fontSize: 11, color: '#64748b', marginTop: 1 },

  tabs: {
    display: 'flex', alignItems: 'center', gap: 4, marginLeft: 8,
    overflowX: 'auto', minWidth: 0, scrollbarWidth: 'thin',
    WebkitOverflowScrolling: 'touch',
  },
  tab: {
    display: 'inline-flex', alignItems: 'center', gap: 6,
    padding: '8px 12px', borderRadius: 10,
    fontFamily: "'Inter', sans-serif", fontWeight: 500, fontSize: 13.5,
    color: '#475569', textDecoration: 'none',
    flexShrink: 0, whiteSpace: 'nowrap',
  },
  tabActive: { background: '#f1f5f9', color: '#0f172a', fontWeight: 600 },
  tabAr: { fontFamily: "'Cairo', sans-serif", fontSize: 12, color: '#94a3b8', fontWeight: 500 },
  badge: {
    fontFamily: "'IBM Plex Mono', monospace", fontSize: 10, fontWeight: 700,
    background: '#fef2f2', color: '#b91c1c',
    padding: '2px 7px', borderRadius: 999, border: '1px solid #fecaca',
  },

  right: { marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 12 },
  iconBtn: {
    position: 'relative',
    width: 36, height: 36, borderRadius: 10,
    background: '#f8fafc', border: '1px solid #e7edf1',
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer',
  },
  notifDot: {
    position: 'absolute', top: 6, right: 6,
    width: 8, height: 8, borderRadius: 4, background: '#ef4444',
    boxShadow: '0 0 0 2px #fff',
  },
  user: { display: 'flex', alignItems: 'center', gap: 10 },
  avatar: {
    width: 36, height: 36, borderRadius: 999,
    background: 'linear-gradient(135deg, #0d9488, #0f766e)', color: '#fff',
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
    fontFamily: "'Inter', sans-serif", fontWeight: 700, fontSize: 13,
  },
  userName: { fontFamily: "'Inter', sans-serif", fontWeight: 600, fontSize: 13, color: '#0f172a' },
  userRole: { fontFamily: "'Inter', sans-serif", fontSize: 11, color: '#64748b' },
};

window.AppHeader = AppHeader;
