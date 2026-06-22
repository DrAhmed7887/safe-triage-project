import React, { Suspense, lazy, useEffect } from 'react';
import OfflineIndicator from './components/OfflineIndicator';
import HospitalLitePage from './pages/HospitalLite/HospitalLitePage';
import { getLang, setLang as applyLang } from './lib/i18n';

const IS_HOSPITAL_LITE_BUILD =
  (import.meta.env.VITE_APP_MODE || 'standard').toLowerCase() === 'hospital_lite';

const StandardApp = lazy(() => import('./StandardApp.jsx'));

/**
 * Hospital Lite shell — bypasses Firebase / Auth entirely. Designed for a
 * standalone hospital pilot or hackathon demo. Single route, no router state
 * is needed because the page manages its own stages internally.
 */
function HospitalLiteApp() {
  useEffect(() => {
    // Ensure RTL/LTR is applied on first paint.
    applyLang(getLang());
    // Reflect mode in the document title so the browser tab is honest.
    document.title = 'SAFE-Triage Lite';
  }, []);

  return (
    <>
      <OfflineIndicator />
      <HospitalLitePage />
    </>
  );
}

function App() {
  if (IS_HOSPITAL_LITE_BUILD) {
    return <HospitalLiteApp />;
  }
  return (
    <Suspense fallback={<OfflineIndicator />}>
      <StandardApp />
    </Suspense>
  );
}

export default App;
