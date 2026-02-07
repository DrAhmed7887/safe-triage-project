import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Activity } from 'lucide-react';
import './SignIn.css';

export default function SignIn() {
    const [role, setRole] = useState('Nurse');
    const [rememberMe, setRememberMe] = useState(false);
    const [error, setError] = useState('');
    const { loginWithGoogle, authError, isFirebaseConfigured } = useAuth();
    const navigate = useNavigate();

    const handleGoogleSignIn = async (e) => {
        e.preventDefault();
        setError('');
        const result = await loginWithGoogle(role, rememberMe);
        if (result.success && !result.redirected) {
            navigate('/dashboard');
            return;
        }
        if (result.redirected) {
            setError('Redirecting to Google sign-in...');
            return;
        } else {
            setError(result.message);
        }
    };

    return (
        <div className="si-page">
            <div className="si-orb si-orb-1" aria-hidden="true" />
            <div className="si-orb si-orb-2" aria-hidden="true" />
            <div className="si-orb si-orb-3" aria-hidden="true" />

            <div className="si-card">
                <div className="si-top">
                    <div className="si-icon-wrap">
                        <Activity className="si-icon" />
                    </div>
                    <h1 className="si-title">Sign in to SAFE-Triage AI</h1>
                    <p className="si-subtitle">Use your hospital Google account to continue</p>
                    <p className="si-subtitle si-ar">استخدم حساب المستشفى على جوجل للمتابعة</p>
                </div>

                <form className="si-form" onSubmit={handleGoogleSignIn}>
                    {(error || authError) && (
                        <div className="si-alert si-alert-error">
                            {error || authError}
                        </div>
                    )}
                    {!isFirebaseConfigured && (
                        <div className="si-alert si-alert-warn">
                            Firebase configuration missing. Add the web app config to enable sign-in.
                        </div>
                    )}

                    <div className="si-field">
                        <label htmlFor="role" className="si-label">
                            Select Your Role | اختر دورك
                        </label>
                        <select
                            id="role"
                            name="role"
                            className="si-select"
                            value={role}
                            onChange={(e) => setRole(e.target.value)}
                        >
                            <option value="Doctor">Doctor | طبيب/ة</option>
                            <option value="Nurse">Nurse | ممرض/ة</option>
                            <option value="Supervisor">Supervisor | مشرف/ة</option>
                            <option value="Admin">Admin | مسؤول/ة</option>
                        </select>
                    </div>

                    <div className="si-check-row">
                        <label htmlFor="remember-me" className="si-check-wrap">
                            <input
                                id="remember-me"
                                name="remember-me"
                                type="checkbox"
                                className="si-checkbox"
                                checked={rememberMe}
                                onChange={(e) => setRememberMe(e.target.checked)}
                            />
                            <span>Remember me</span>
                        </label>
                    </div>

                    <button
                        type="submit"
                        disabled={!isFirebaseConfigured}
                        className="si-google-btn"
                    >
                        Sign in with Google <span aria-hidden="true">→</span>
                    </button>
                </form>

                <button className="si-back-link" type="button" onClick={() => navigate('/')}>
                    ← Back to Home
                </button>

                <div className="si-badges">
                    <span className="si-badge">🔒 HIPAA Compliant</span>
                    <span className="si-badge">🏥 GAHAR-Aligned</span>
                    <span className="si-badge">☁️ Google Cloud</span>
                </div>
            </div>

            <div className="si-disclaimer">
                Research prototype for academic purposes only. Not a certified medical device.
            </div>
        </div>
    );
}
