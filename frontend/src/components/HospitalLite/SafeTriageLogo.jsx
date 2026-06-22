import React from 'react';

/**
 * SAFE-Triage brand mark.
 *
 * The mark combines three ideas without text inside the icon:
 *   - shield: safety floor / governed decision support
 *   - stepped bars: triage acuity levels
 *   - ECG line: emergency department workflow
 */
export default function SafeTriageLogo({ className = 'h-9 w-9', title = 'SAFE-Triage Lite' }) {
    return (
        <svg
            viewBox="0 0 64 64"
            role="img"
            aria-label={title}
            className={className}
        >
            <defs>
                <linearGradient id="safe-triage-logo-bg" x1="10" x2="54" y1="7" y2="57" gradientUnits="userSpaceOnUse">
                    <stop offset="0" stopColor="#0f3a56" />
                    <stop offset="0.55" stopColor="#0b2740" />
                    <stop offset="1" stopColor="#061827" />
                </linearGradient>
                <linearGradient id="safe-triage-logo-shield" x1="18" x2="46" y1="14" y2="52" gradientUnits="userSpaceOnUse">
                    <stop offset="0" stopColor="#2dd4bf" />
                    <stop offset="1" stopColor="#0d9488" />
                </linearGradient>
                <filter id="safe-triage-logo-shadow" x="-20%" y="-20%" width="140%" height="150%">
                    <feDropShadow dx="0" dy="5" stdDeviation="4" floodColor="#020617" floodOpacity="0.3" />
                </filter>
            </defs>

            <rect x="2.5" y="2.5" width="59" height="59" rx="15" fill="url(#safe-triage-logo-bg)" />
            <rect x="3.25" y="3.25" width="57.5" height="57.5" rx="14.25" fill="none" stroke="#5eead4" strokeOpacity="0.18" strokeWidth="1.5" />

            <path
                d="M32 10.5 47.5 16v13.7c0 10.1-5.8 18.9-15.5 23.8-9.7-4.9-15.5-13.7-15.5-23.8V16L32 10.5Z"
                fill="url(#safe-triage-logo-shield)"
                filter="url(#safe-triage-logo-shadow)"
            />
            <path
                d="M32 14.3 43.9 18.5v11.1c0 7.8-4.3 14.6-11.9 18.7-7.6-4.1-11.9-10.9-11.9-18.7V18.5L32 14.3Z"
                fill="#f8fafc"
                fillOpacity="0.12"
                stroke="#ccfbf1"
                strokeOpacity="0.35"
                strokeWidth="1"
            />

            <path
                d="M17.5 33h10.3l3.9-9.6 5.3 18 3.4-8.4h6.1"
                fill="none"
                stroke="#ffffff"
                strokeWidth="4.3"
                strokeLinecap="round"
                strokeLinejoin="round"
            />
            <path
                d="M23 43.5h5.2M23 38.5h9.3M39.6 23.2h4.2M39.6 28.2h4.2"
                fill="none"
                stroke="#052e3f"
                strokeOpacity="0.55"
                strokeWidth="2.3"
                strokeLinecap="round"
            />

            <circle cx="47.2" cy="33" r="3.2" fill="#f59e0b" stroke="#fff7ed" strokeWidth="1.4" />
        </svg>
    );
}
