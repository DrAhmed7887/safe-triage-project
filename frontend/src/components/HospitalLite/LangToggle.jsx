import React from 'react';
import { Languages } from 'lucide-react';

export default function LangToggle({ lang, onChange }) {
    const isAr = lang === 'ar';
    return (
        <button
            type="button"
            onClick={() => onChange(isAr ? 'en' : 'ar')}
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[12.5px] font-semibold border border-slate-200 text-slate-700 bg-white hover:bg-slate-50 active:bg-slate-100 transition-colors"
            aria-label={isAr ? 'Switch to English' : 'التحويل إلى العربية'}
        >
            <Languages className="w-4 h-4" aria-hidden="true" />
            <span>{isAr ? 'EN' : 'AR'}</span>
        </button>
    );
}
