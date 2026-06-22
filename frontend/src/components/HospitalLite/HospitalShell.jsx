import React from 'react';
import { ShieldCheck, LogOut, FlaskConical, LockKeyhole } from 'lucide-react';
import LangToggle from './LangToggle';
import SafeTriageLogo from './SafeTriageLogo';
import { t } from '../../lib/i18n';

/**
 * Top app chrome for Hospital Lite. Keeps the clinical look from AppHeader
 * but drops Firebase, supervisor analytics, MedGemma, and the queue badge —
 * the queue lives in a side rail in this mode.
 */
export default function HospitalShell({ lang, onLangChange, clinician, onSignOut, children }) {
    return (
        <div className="min-h-screen bg-[#eef5f7] font-sans text-slate-900">
            <header className="sticky top-0 z-30 border-b border-white/10 bg-[#071525] text-white shadow-lg shadow-slate-950/10 print:hidden">
                <div className="h-1 bg-gradient-to-r from-teal-400 via-cyan-300 to-amber-400" aria-hidden="true" />
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 min-h-16 flex items-center justify-between gap-3 py-2">
                    <div className="flex items-center gap-2 min-w-0">
                        <SafeTriageLogo className="h-10 w-10 flex-shrink-0" />
                        <div className="min-w-0">
                            <h1 className="text-[15px] sm:text-[17px] font-extrabold leading-tight tracking-tight">
                                {t('app_title', lang)}
                            </h1>
                            <p className="hidden sm:flex text-[11px] text-slate-300 leading-tight items-center gap-1.5 truncate">
                                <ShieldCheck className="w-3.5 h-3.5 text-teal-200" aria-hidden="true" />
                                <span>{t('decision_support', lang)}</span>
                            </p>
                        </div>
                    </div>

                    <div className="flex items-center gap-2 flex-shrink-0">
                        {clinician?.name && (
                            <div className="hidden sm:flex flex-col items-end leading-tight">
                                <span className="text-[12.5px] font-semibold text-white truncate max-w-[160px]">
                                    {clinician.name}
                                </span>
                                <span className="text-[10.5px] text-slate-300">
                                    {t(`role_${clinician.role || 'nurse'}`, lang)}
                                </span>
                            </div>
                        )}
                        <div className="hidden md:inline-flex items-center gap-1.5 rounded-md border border-white/10 bg-white/5 px-2.5 py-1.5 text-[11px] font-semibold text-cyan-100">
                            <LockKeyhole className="h-3.5 w-3.5 text-cyan-200" aria-hidden="true" />
                            <span>{t('brand_signal_local', lang)}</span>
                        </div>
                        <LangToggle lang={lang} onChange={onLangChange} />
                        {clinician?.name && (
                            <button
                                type="button"
                                onClick={onSignOut}
                                className="p-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-white/10 transition-colors"
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

            <footer className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 text-center text-slate-500 text-[12px] print:hidden">
                {t('brand_rule', lang)}
            </footer>
        </div>
    );
}
