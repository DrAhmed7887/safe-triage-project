import React from 'react';
import { Activity, ShieldCheck, LogOut, FlaskConical } from 'lucide-react';
import LangToggle from './LangToggle';
import { t } from '../../lib/i18n';

/**
 * Top app chrome for Hospital Lite. Keeps the clinical look from AppHeader
 * but drops Firebase, supervisor analytics, MedGemma, and the queue badge —
 * the queue lives in a side rail in this mode.
 */
export default function HospitalShell({ lang, onLangChange, clinician, onSignOut, children }) {
    return (
        <div className="min-h-screen bg-slate-50 font-sans text-slate-900">
            <header className="bg-white sticky top-0 z-30 border-b border-slate-200 shadow-sm print:hidden">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 min-h-14 flex items-center justify-between gap-3 py-2">
                    <div className="flex items-center gap-2 min-w-0">
                        <div className="bg-teal-600 p-2 rounded-xl shadow-sm shadow-teal-600/20 flex-shrink-0">
                            <Activity className="w-5 h-5 text-white" aria-hidden="true" />
                        </div>
                        <div className="min-w-0">
                            <h1 className="text-[15px] sm:text-base font-bold leading-tight tracking-tight">
                                {t('app_title', lang)}
                            </h1>
                            <p className="text-[11px] text-slate-500 leading-tight flex items-center gap-1.5">
                                <ShieldCheck className="w-3.5 h-3.5 text-teal-600" aria-hidden="true" />
                                <span>{t('decision_support', lang)}</span>
                            </p>
                        </div>
                    </div>

                    <div className="flex items-center gap-2 flex-shrink-0">
                        {clinician?.name && (
                            <div className="hidden sm:flex flex-col items-end leading-tight">
                                <span className="text-[12.5px] font-semibold text-slate-900 truncate max-w-[160px]">
                                    {clinician.name}
                                </span>
                                <span className="text-[10.5px] text-slate-500">
                                    {t(`role_${clinician.role || 'nurse'}`, lang)}
                                </span>
                            </div>
                        )}
                        <LangToggle lang={lang} onChange={onLangChange} />
                        {clinician?.name && (
                            <button
                                type="button"
                                onClick={onSignOut}
                                className="p-1.5 rounded-lg text-slate-500 hover:text-red-600 hover:bg-slate-50 transition-colors"
                                aria-label="Sign out"
                                title="Sign out"
                            >
                                <LogOut className="w-4 h-4" aria-hidden="true" />
                            </button>
                        )}
                    </div>
                </div>
            </header>

            <div
                role="note"
                aria-label={t('synthetic_demo_banner', lang)}
                className="bg-amber-50 border-b border-amber-200 text-amber-900 print:hidden"
            >
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2 flex items-start gap-2 text-[12px] sm:text-[12.5px] leading-snug">
                    <FlaskConical className="w-4 h-4 mt-[1px] flex-shrink-0 text-amber-700" aria-hidden="true" />
                    <p>
                        <span className="font-semibold">{t('synthetic_demo_banner_title', lang)}</span>
                        <span className="mx-1.5 text-amber-700/70" aria-hidden="true">·</span>
                        <span>{t('synthetic_demo_banner_body', lang)}</span>
                    </p>
                </div>
            </div>

            <main className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 py-4 sm:py-6">
                {children}
            </main>

            <footer className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 text-center text-slate-400 text-[12px] print:hidden">
                {t('decision_support', lang)}
            </footer>
        </div>
    );
}
