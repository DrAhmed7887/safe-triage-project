import React from 'react';
import { CloudCheck, CloudOff } from 'lucide-react';
import { t } from '../../lib/i18n';

/**
 * Visible chip + optional full-width warning that tells the clinician which
 * triage engine produced the suggestion. The Python backend engine is the
 * canonical SAFE-Triage engine; the JS fallback only runs when the network
 * call to `/triage` fails. Both states must be surfaced — silent fallback
 * is the failure mode we are trying to avoid.
 */
export default function EngineSourceBadge({ lang, source, error, variant = 'inline' }) {
    const isFallback = source === 'offline_js_fallback';
    const Icon = isFallback ? CloudOff : CloudCheck;

    if (variant === 'chip') {
        return (
            <span
                className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-semibold border ${
                    isFallback
                        ? 'bg-amber-50 text-amber-800 border-amber-300'
                        : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                }`}
                title={t(isFallback ? 'engine_fallback_help' : 'engine_python_help', lang)}
            >
                <Icon className="w-3.5 h-3.5" aria-hidden="true" />
                <span>{t(isFallback ? 'engine_fallback' : 'engine_python', lang)}</span>
            </span>
        );
    }

    if (isFallback) {
        return (
            <div
                role="alert"
                className="rounded-lg px-3 py-2 bg-amber-50 border border-amber-300 text-amber-900 text-[12.5px] flex items-start gap-2"
            >
                <CloudOff className="w-4 h-4 flex-shrink-0 mt-0.5" aria-hidden="true" />
                <div className="leading-snug">
                    <p className="font-semibold">{t('engine_fallback', lang)}</p>
                    <p>{t('engine_fallback_help', lang)}</p>
                    {error?.kind && (
                        <p className="text-[11px] mt-1 font-mono opacity-70">
                            {error.kind}{error.status ? ` ${error.status}` : ''}
                        </p>
                    )}
                </div>
            </div>
        );
    }

    return (
        <div className="rounded-lg px-3 py-2 bg-emerald-50 border border-emerald-200 text-emerald-800 text-[12.5px] flex items-center gap-2">
            <CloudCheck className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
            <span><span className="font-semibold">{t('engine_python', lang)}</span> · {t('engine_python_help', lang)}</span>
        </div>
    );
}
