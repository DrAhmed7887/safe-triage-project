// SignIn — the most "designed" surface in the product.
// Animated -45deg gradient (slate / teal / indigo / slate) + 3 blurred orbs.
// Glass card with si-fade-in entry, big logo, bilingual CTA.

const SignIn = ({ onSignIn }) => (
  <div style={siStyles.bg}>
    <div style={siStyles.orb1} aria-hidden="true"></div>
    <div style={siStyles.orb2} aria-hidden="true"></div>
    <div style={siStyles.orb3} aria-hidden="true"></div>
    <div style={siStyles.card}>
      <div style={siStyles.logo}>
        <i data-lucide="activity" style={{ width: 28, height: 28, color: '#fff' }}></i>
      </div>
      <div style={siStyles.brandLine}>
        <span style={siStyles.wordmark}>SAFE-Triage</span>
        <span style={siStyles.beta}>BETA</span>
      </div>
      <p style={siStyles.tagline}>
        Clinical decision support for Egyptian Emergency Departments.
      </p>
      <p style={siStyles.taglineAr} dir="rtl">
        نظام دعم القرار السريري لأقسام الطوارئ في المستشفيات المصرية.
      </p>

      <button style={siStyles.googleBtn} onClick={onSignIn}>
        <span style={siStyles.googleIcon}>G</span>
        <span style={siStyles.googleEn}>Sign in with Google</span>
        <span style={siStyles.btnSep}>|</span>
        <span style={siStyles.googleAr} dir="rtl">تسجيل الدخول</span>
      </button>

      <div style={siStyles.complianceRow}>
        <span style={siStyles.compPill}>🛡 GAHAR</span>
        <span style={siStyles.compPill}>🏥 HIPAA-grade audit</span>
        <span style={siStyles.compPill}>📊 BigQuery audit trail</span>
      </div>

      <div style={siStyles.footer}>
        <span style={siStyles.disclaimer}>
          Clinical Decision Support Tool — not a substitute for professional medical judgment.
        </span>
        <span style={siStyles.disclaimerAr} dir="rtl">
          أداة دعم قرار سريري — لا تغني عن الحكم الطبي المتخصص.
        </span>
      </div>
    </div>
  </div>
);

const siStyles = {
  bg: {
    position: 'relative', minHeight: 720,
    background: 'linear-gradient(-45deg, #0f172a, #134e4a, #1e1b4b, #0f172a)',
    backgroundSize: '400% 400%',
    animation: 'si-gradient 18s ease-in-out infinite',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    padding: 24, overflow: 'hidden',
  },
  orb1: {
    position: 'absolute', top: '10%', left: '8%', width: 320, height: 320,
    background: 'radial-gradient(circle, rgba(13,148,136,0.55), transparent 60%)',
    filter: 'blur(60px)', animation: 'st-float 10s ease-in-out infinite',
    pointerEvents: 'none',
  },
  orb2: {
    position: 'absolute', bottom: '12%', right: '6%', width: 360, height: 360,
    background: 'radial-gradient(circle, rgba(99,102,241,0.45), transparent 60%)',
    filter: 'blur(60px)', animation: 'st-float 13s ease-in-out infinite reverse',
    pointerEvents: 'none',
  },
  orb3: {
    position: 'absolute', top: '40%', right: '38%', width: 220, height: 220,
    background: 'radial-gradient(circle, rgba(94,234,212,0.30), transparent 60%)',
    filter: 'blur(50px)', animation: 'st-float 9s ease-in-out infinite',
    pointerEvents: 'none',
  },
  card: {
    position: 'relative', zIndex: 2, width: '100%', maxWidth: 460,
    background: 'rgba(255,255,255,0.06)', backdropFilter: 'blur(18px)',
    WebkitBackdropFilter: 'blur(18px)',
    border: '1px solid rgba(255,255,255,0.12)', borderRadius: 24,
    padding: '40px 36px',
    boxShadow: '0 30px 80px rgba(0,0,0,0.45)',
    color: '#fff',
    textAlign: 'center',
    animation: 'si-fade-in 0.7s ease-out',
  },
  logo: {
    width: 54, height: 54, borderRadius: 14, background: '#0d9488',
    margin: '0 auto 18px',
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
    boxShadow: '0 14px 30px rgba(13,148,136,0.45)',
  },
  brandLine: { display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, marginBottom: 12 },
  wordmark: { fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: 28, fontWeight: 800, letterSpacing: -0.6 },
  beta: { fontFamily: "'IBM Plex Mono', monospace", fontSize: 10, fontWeight: 700, letterSpacing: 0.16, color: '#5eead4', border: '1px solid rgba(94,234,212,0.4)', borderRadius: 4, padding: '2px 6px' },
  tagline: { fontFamily: "'Inter', sans-serif", fontSize: 14, lineHeight: 1.6, color: 'rgba(226,232,240,0.85)', margin: '0 0 6px' },
  taglineAr: { fontFamily: "'Cairo', sans-serif", fontSize: 14, color: 'rgba(226,232,240,0.7)', margin: '0 0 28px', lineHeight: 1.7 },

  googleBtn: {
    width: '100%', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 10,
    background: '#fff', color: '#0f172a', border: 'none', borderRadius: 12,
    padding: '14px 20px', cursor: 'pointer',
    fontFamily: "'Inter', sans-serif", fontSize: 15, fontWeight: 600,
    boxShadow: '0 18px 40px rgba(0,0,0,0.2)',
    marginBottom: 24,
  },
  googleIcon: { width: 22, height: 22, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', background: 'conic-gradient(from 90deg, #4285F4, #34A853, #FBBC05, #EA4335)', borderRadius: 999, color: '#fff', fontWeight: 800, fontSize: 12, fontFamily: "'Plus Jakarta Sans', sans-serif" },
  googleEn: {},
  btnSep: { color: '#cbd5e1', fontWeight: 400 },
  googleAr: { fontFamily: "'Cairo', sans-serif", fontWeight: 600 },

  complianceRow: { display: 'flex', justifyContent: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 24 },
  compPill: { fontFamily: "'Inter', sans-serif", fontSize: 11, fontWeight: 600, color: 'rgba(255,255,255,0.86)', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.12)', padding: '5px 11px', borderRadius: 999 },

  footer: { borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: 16, display: 'flex', flexDirection: 'column', gap: 4 },
  disclaimer: { fontFamily: "'Inter', sans-serif", fontSize: 11, color: 'rgba(203,213,225,0.7)', lineHeight: 1.5 },
  disclaimerAr: { fontFamily: "'Cairo', sans-serif", fontSize: 11, color: 'rgba(203,213,225,0.55)', lineHeight: 1.7 },
};

window.SignIn = SignIn;
