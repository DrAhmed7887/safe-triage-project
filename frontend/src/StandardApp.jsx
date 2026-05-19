import React from 'react';
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

export default function StandardApp() {
  return (
    <AuthProvider>
      <OfflineIndicator />
      <AppRoutes />
    </AuthProvider>
  );
}
