import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Activity, LogIn } from 'lucide-react';

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
        if (result.success) {
            navigate('/');
        } else {
            setError(result.message);
        }
    };

    return (
        <div className="min-h-screen bg-slate-50 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
            <div className="max-w-md w-full space-y-8 bg-white p-8 rounded-xl shadow-lg">
                <div className="text-center">
                    <div className="mx-auto h-12 w-12 bg-blue-600 rounded-lg flex items-center justify-center">
                        <Activity className="h-8 w-8 text-white" />
                    </div>
                    <h2 className="mt-6 text-3xl font-extrabold text-slate-900">
                        Sign in to SAFE-Triage AI
                    </h2>
                    <p className="mt-2 text-sm text-slate-600">
                        Use your hospital Google account to continue.
                    </p>
                </div>
                <form className="mt-8 space-y-6" onSubmit={handleGoogleSignIn}>
                    {(error || authError) && (
                        <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-md text-sm">
                            {error || authError}
                        </div>
                    )}
                    {!isFirebaseConfigured && (
                        <div className="bg-amber-50 border border-amber-200 text-amber-700 px-4 py-3 rounded-md text-sm">
                            Firebase configuration missing. Add the web app config to enable sign-in.
                        </div>
                    )}
                    <div className="rounded-md shadow-sm">
                        <label htmlFor="role" className="sr-only">
                            Role
                        </label>
                        <select
                            id="role"
                            name="role"
                            className="appearance-none rounded-lg relative block w-full px-3 py-2 border border-slate-300 text-slate-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                            value={role}
                            onChange={(e) => setRole(e.target.value)}
                        >
                            <option value="Doctor">Doctor</option>
                            <option value="Nurse">Nurse</option>
                            <option value="Supervisor">Supervisor</option>
                        </select>
                    </div>

                    <div className="flex items-center justify-between">
                        <div className="flex items-center">
                            <input
                                id="remember-me"
                                name="remember-me"
                                type="checkbox"
                                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-slate-300 rounded"
                                checked={rememberMe}
                                onChange={(e) => setRememberMe(e.target.checked)}
                            />
                            <label htmlFor="remember-me" className="ml-2 block text-sm text-slate-900">
                                Remember me
                            </label>
                        </div>
                    </div>

                    <div>
                        <button
                            type="submit"
                            disabled={!isFirebaseConfigured}
                            className="group relative w-full flex items-center justify-center gap-2 py-2 px-4 border border-transparent text-sm font-medium rounded-lg text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors duration-200 disabled:opacity-60 disabled:cursor-not-allowed"
                        >
                            <LogIn className="w-4 h-4" />
                            Sign in with Google
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
