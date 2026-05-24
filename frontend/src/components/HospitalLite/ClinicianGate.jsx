import React, { useState } from 'react';
import {
    AlertTriangle, Languages, ShieldCheck, Workflow,
} from 'lucide-react';
import { setClinician } from '../../lib/hospitalLite';
import { t } from '../../lib/i18n';
import SafeTriageLogo from './SafeTriageLogo';

/**
 * Local clinician sign-in for Hospital Lite. No Firebase. Just stores the
 * name + role so we can attach them to audit events. The "session" persists
 * in localStorage until the clinician signs out, which is practical for a
 * single triage desk computer or shared iPad.
 */
export default function ClinicianGate({ lang, onSignedIn }) {
    const [name, setName] = useState('');
    const [role, setRole] = useState('nurse');
    const isArabic = lang === 'ar';

    const submit = (e) => {
        e.preventDefault();
        if (!name.trim()) return;
        const profile = setClinician({ name: name.trim(), role });
        onSignedIn(profile);
    };

    return (
        <div className="relative overflow-hidden bg-[#071525] text-white">
            <div className="absolute inset-0 opacity-45" aria-hidden="true">
                <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(255,255,255,0.06)_1px,transparent_1px),linear-gradient(180deg,rgba(255,255,255,0.06)_1px,transparent_1px)] bg-[size:56px_56px]" />
                <div className="absolute right-0 top-0 h-72 w-72 rounded-full bg-teal-400/10 blur-3xl" />
                <div className="absolute bottom-0 left-0 h-72 w-72 rounded-full bg-amber-400/10 blur-3xl" />
            </div>

            <div className="relative mx-auto grid min-h-[72vh] w-full max-w-7xl gap-8 px-4 py-8 sm:px-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(360px,0.9fr)] lg:px-8 lg:py-12">
                <section className="flex min-w-0 flex-col justify-center">
                    <div className="mb-6 flex items-center gap-3">
                        <SafeTriageLogo className="h-14 w-14 flex-shrink-0" />
                        <div className="min-w-0">
                            <p className="text-[12px] font-bold uppercase tracking-[0.16em] text-teal-100">
                                {t('brand_kicker', lang)}
                            </p>
                            <p className="mt-1 text-[12.5px] font-semibold text-slate-300">
                                {t('app_subtitle', lang)}
                            </p>
                        </div>
                    </div>

                    <h1 className="max-w-2xl text-4xl font-extrabold leading-tight tracking-normal text-white sm:text-5xl">
                        {t('app_title', lang)}
                    </h1>
                    <p className="mt-3 max-w-xl text-xl font-bold leading-snug text-teal-100">
                        {t('brand_headline', lang)}
                    </p>
                    <p className="mt-4 max-w-2xl text-[15px] leading-7 text-slate-200">
                        {t('brand_body', lang)}
                    </p>

                    <div className="mt-5 flex flex-wrap gap-2">
                        {[t('brand_signal_language', lang), t('brand_signal_rules', lang), t('brand_signal_local', lang)].map((item) => (
                            <span key={item} className="rounded-md border border-white/15 bg-white/10 px-3 py-1.5 text-[12px] font-bold text-slate-100">
                                {item}
                            </span>
                        ))}
                    </div>

                    <div className="mt-6 rounded-lg border border-amber-300/25 bg-amber-300/10 px-4 py-3 text-[13px] font-semibold leading-6 text-amber-50">
                        <div className="flex items-start gap-2">
                            <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-200" aria-hidden="true" />
                            <span>{t('synthetic_demo_banner_body', lang)}</span>
                        </div>
                    </div>

                    <div className="mt-8 max-w-lg rounded-lg border border-white/15 bg-white/10 p-3 shadow-2xl shadow-slate-950/30">
                        <div className="rounded-lg bg-white p-3 text-slate-900">
                            <div className="mb-3 flex items-center justify-between rounded-md bg-[#0b2a3c] px-3 py-2 text-white">
                                <div className="flex items-center gap-2 text-[13px] font-bold">
                                    <Workflow className="h-4 w-4 text-teal-200" aria-hidden="true" />
                                    <span>{t('app_title', lang)}</span>
                                </div>
                                <span className="rounded-full bg-white/15 px-2 py-0.5 text-[10px] font-bold">
                                    {isArabic ? 'AR' : 'EN'}
                                </span>
                            </div>
                            <div className="grid gap-2 text-[12px]">
                                <PreviewRow label={t('preview_complaint', lang)} value={t('preview_complaint_value', lang)} />
                                <PreviewRow label="ESI" value="Level 2" strong />
                                <PreviewRow label="NEWS2" value="9 - high" strong />
                                <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-red-800">
                                    <div className="flex items-center gap-2 font-bold">
                                        <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
                                        <span>{t('preview_safety', lang)}</span>
                                    </div>
                                </div>
                                <div className="rounded-md border border-teal-200 bg-teal-50 px-3 py-2 font-bold text-teal-800">
                                    {t('preview_confirmation', lang)}
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                <form
                    onSubmit={submit}
                    className="self-center rounded-lg border border-white/20 bg-white p-5 text-slate-900 shadow-2xl shadow-slate-950/30 sm:p-6"
                >
                    <div className="flex items-start gap-3">
                        <SafeTriageLogo className="h-12 w-12 flex-shrink-0" />
                        <div className="min-w-0">
                            <h2 className="text-lg font-extrabold leading-tight">{t('app_title', lang)}</h2>
                            <p className="mt-1 text-[12px] font-semibold leading-5 text-slate-500">{t('app_subtitle', lang)}</p>
                        </div>
                    </div>

                    <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-[12px] font-semibold leading-5 text-slate-700">
                        <div className="flex items-start gap-2">
                            <Languages className="mt-0.5 h-4 w-4 flex-shrink-0 text-teal-700" aria-hidden="true" />
                            <span>{t('brand_rule', lang)}</span>
                        </div>
                    </div>

                    <div className="mt-5 space-y-2">
                        <label className="block text-[13px] font-semibold text-slate-700">
                            {t('clinician_name', lang)}
                        </label>
                        <input
                            type="text"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            autoFocus
                            autoComplete="name"
                            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-[15px] outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
                            placeholder="Dr. / RN"
                            required
                        />
                    </div>

                    <div className="mt-4 space-y-2">
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
                                    className={`rounded-lg border px-2 py-2 text-[12.5px] font-semibold transition-colors ${
                                        role === r
                                            ? 'border-teal-600 bg-teal-600 text-white'
                                            : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'
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
                        className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-[#b7791f] px-4 py-3 text-[14px] font-bold text-white shadow-sm transition-colors hover:bg-amber-700 disabled:cursor-not-allowed disabled:bg-slate-300"
                    >
                        {t('sign_in_local', lang)}
                    </button>
                </form>
            </div>
        </div>
    );
}

function PreviewRow({ label, value, strong = false }) {
    return (
        <div className="flex items-center justify-between gap-3 rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
            <span className="font-semibold text-slate-500">{label}</span>
            <span className={`${strong ? 'font-extrabold text-slate-950' : 'font-bold text-slate-800'} text-right`}>
                {value}
            </span>
        </div>
    );
}
