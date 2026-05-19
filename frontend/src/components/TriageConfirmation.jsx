import React, { useEffect, useMemo, useState } from 'react';
import { CheckCircle2, Timer, AlertTriangle } from 'lucide-react';

export default function TriageConfirmation({
    recommendedESI,
    category,
    redFlags = [],
    timeoutSeconds = 300,
    isActive = true,
    onConfirm,
    onOverride,
    onTimeout,
}) {
    const [remaining, setRemaining] = useState(timeoutSeconds);
    const [overrideLevel, setOverrideLevel] = useState('');
    const [overrideReason, setOverrideReason] = useState('');
    const [supervisorPin, setSupervisorPin] = useState('');

    useEffect(() => {
        if (!isActive) return undefined;
        setRemaining(timeoutSeconds);
        const interval = setInterval(() => {
            setRemaining((prev) => {
                if (prev <= 1) {
                    clearInterval(interval);
                    if (onTimeout) onTimeout();
                    return 0;
                }
                return prev - 1;
            });
        }, 1000);
        return () => clearInterval(interval);
    }, [timeoutSeconds, onTimeout, isActive]);

    const timeText = useMemo(() => {
        const m = Math.floor(remaining / 60).toString().padStart(2, '0');
        const s = Math.floor(remaining % 60).toString().padStart(2, '0');
        return `${m}:${s}`;
    }, [remaining]);

    const handleOverride = () => {
        if (!overrideLevel || !overrideReason.trim()) return;
        onOverride?.(
            parseInt(overrideLevel, 10),
            overrideReason.trim(),
            supervisorPin.trim()
        );
    };

    return (
        <div className="mt-6 p-5 rounded-xl border border-amber-200 bg-amber-50">
            <div className="flex items-center justify-between gap-3">
                <div>
                    <p className="text-xs uppercase tracking-wider text-amber-700 font-bold">Human Confirmation Required</p>
                    <p className="text-sm text-amber-900">
                        Recommended ESI: <span className="font-bold">{recommendedESI}</span>
                        {category ? <span className="ml-2 text-amber-700">({category})</span> : null}
                    </p>
                </div>
                <div className="flex items-center gap-2 text-amber-900">
                    <Timer className="w-4 h-4" />
                    <span className="font-mono text-sm">{timeText}</span>
                </div>
            </div>

            {redFlags.length > 0 && (
                <div className="mt-3 text-xs text-amber-900 flex items-start gap-2">
                    <AlertTriangle className="w-4 h-4 mt-0.5" />
                    <span>Red flags: {redFlags.join(', ')}</span>
                </div>
            )}

            <div className="mt-4 flex flex-wrap items-center gap-3">
                <button
                    onClick={() => onConfirm?.(recommendedESI)}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 text-white text-sm font-semibold hover:bg-emerald-700 transition"
                >
                    <CheckCircle2 className="w-4 h-4" />
                    Confirm ESI {recommendedESI}
                </button>
            </div>

            <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-3">
                <select
                    value={overrideLevel}
                    onChange={(e) => setOverrideLevel(e.target.value)}
                    className="px-3 py-2 rounded-lg border border-amber-200 bg-white text-sm"
                >
                    <option value="">Override Level...</option>
                    {[1, 2, 3, 4, 5].map((lvl) => (
                        <option key={lvl} value={lvl}>ESI {lvl}</option>
                    ))}
                </select>
                <input
                    type="text"
                    value={overrideReason}
                    onChange={(e) => setOverrideReason(e.target.value)}
                    placeholder="Override reason"
                    className="px-3 py-2 rounded-lg border border-amber-200 bg-white text-sm col-span-2"
                />
            </div>

            {overrideLevel && parseInt(overrideLevel, 10) > recommendedESI && (
                <div className="mt-3">
                    <input
                        type="password"
                        value={supervisorPin}
                        onChange={(e) => setSupervisorPin(e.target.value)}
                        placeholder="Supervisor PIN (required for downgrade)"
                        className="px-3 py-2 rounded-lg border border-amber-200 bg-white text-sm w-full"
                    />
                </div>
            )}

            <div className="mt-3">
                <button
                    onClick={handleOverride}
                    className="px-4 py-2 rounded-lg border border-amber-300 text-amber-900 text-sm font-semibold hover:bg-amber-100 transition"
                >
                    Submit Override
                </button>
            </div>
        </div>
    );
}
