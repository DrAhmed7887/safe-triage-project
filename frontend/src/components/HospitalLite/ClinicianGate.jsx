import React, { useState } from 'react';
import { UserCircle2 } from 'lucide-react';
import { setClinician } from '../../lib/hospitalLite';
import { t } from '../../lib/i18n';

/**
 * Local clinician sign-in for Hospital Lite. No Firebase. Just stores the
 * name + role so we can attach them to audit events. The "session" persists
 * in localStorage until the clinician signs out — practical for a single
 * triage desk computer / shared iPad.
 */
export default function ClinicianGate({ lang, onSignedIn }) {
    const [name, setName] = useState('');
    const [role, setRole] = useState('nurse');

    const submit = (e) => {
        e.preventDefault();
        if (!name.trim()) return;
        const profile = setClinician({ name: name.trim(), role });
        onSignedIn(profile);
    };

    return (
        <div className="min-h-[60vh] flex items-center justify-center px-4">
            <form
                onSubmit={submit}
                className="w-full max-w-md bg-white rounded-2xl shadow-md border border-slate-200 p-6 sm:p-8 space-y-5"
            >
                <div className="flex items-center gap-3">
                    <div className="bg-teal-50 p-2 rounded-xl text-teal-700">
                        <UserCircle2 className="w-7 h-7" aria-hidden="true" />
                    </div>
                    <div>
                        <h2 className="text-lg font-bold leading-tight">{t('app_title', lang)}</h2>
                        <p className="text-[12px] text-slate-500">{t('decision_support', lang)}</p>
                    </div>
                </div>

                <div className="space-y-2">
                    <label className="block text-[13px] font-semibold text-slate-700">
                        {t('clinician_name', lang)}
                    </label>
                    <input
                        type="text"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        autoFocus
                        autoComplete="name"
                        className="w-full px-3 py-2.5 rounded-lg border border-slate-300 focus:border-teal-500 focus:ring-2 focus:ring-teal-100 outline-none text-[15px]"
                        placeholder="Dr. / RN"
                        required
                    />
                </div>

                <div className="space-y-2">
                    <label className="block text-[13px] font-semibold text-slate-700">
                        {t('role', lang)}
                    </label>
                    <div className="grid grid-cols-3 gap-2">
                        {['nurse', 'doctor', 'supervisor'].map((r) => (
                            <button
                                type="button"
                                key={r}
                                onClick={() => setRole(r)}
                                aria-pressed={role === r}
                                className={`px-2 py-2 rounded-lg text-[12.5px] font-semibold border transition-colors ${
                                    role === r
                                        ? 'bg-teal-600 border-teal-600 text-white'
                                        : 'bg-white border-slate-300 text-slate-700 hover:bg-slate-50'
                                }`}
                            >
                                {t(`role_${r}`, lang)}
                            </button>
                        ))}
                    </div>
                </div>

                <button
                    type="submit"
                    disabled={!name.trim()}
                    className="w-full inline-flex items-center justify-center gap-2 bg-teal-600 hover:bg-teal-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white rounded-lg px-4 py-2.5 text-[14px] font-semibold transition-colors"
                >
                    {t('sign_in_local', lang)}
                </button>
            </form>
        </div>
    );
}
