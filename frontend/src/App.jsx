import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import OfflineIndicator from './components/OfflineIndicator';
import Dashboard from './pages/Dashboard';
import SignIn from './pages/SignIn';
import SignUp from './pages/SignUp';
import LandingPage from './pages/LandingPage';
import AnalyticsDashboard from './pages/AnalyticsDashboard';
import MedGemmaDashboard from './pages/MedGemmaDashboard';
import QueuePage from './pages/QueuePage';
import KnowledgePage from './pages/KnowledgePage';
import HospitalLitePage from './pages/HospitalLite/HospitalLitePage';
import { IS_HOSPITAL_LITE } from './lib/hospitalLite';
import { getLang, setLang as applyLang } from './lib/i18n';

function AppRoutes() {
  const { user } = useAuth();

  return (
    <Router>
      <Routes>
        <Route path="/" element={user ? <Navigate to="/dashboard" replace /> : <LandingPage />} />
        <Route path="/signin" element={user ? <Navigate to="/dashboard" replace /> : <SignIn />} />
        <Route path="/signup" element={<SignUp />} />

        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/queue" element={<QueuePage />} />
          <Route path="/knowledge" element={<KnowledgePage />} />
          <Route path="/analytics/dashboard" element={<AnalyticsDashboard />} />
          <Route path="/medgemma/dashboard" element={<MedGemmaDashboard />} />
        </Route>
      </Routes>
    </Router>
  );
}

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
    document.title = 'SAFE-Triage · Hospital Lite';
  }, []);

  return (
    <>
      <OfflineIndicator />
      <HospitalLitePage />
    </>
  );
}

function App() {
  if (IS_HOSPITAL_LITE) {
    return <HospitalLiteApp />;
  }
  return (
    <AuthProvider>
      <OfflineIndicator />
      <AppRoutes />
    </AuthProvider>
  );
}

export default App;
