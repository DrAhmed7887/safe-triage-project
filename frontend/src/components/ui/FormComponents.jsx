/**
 * SAFE-Triage Form UI Components
 * Reusable styled components for the triage form
 * Version 2.2 - Extracted from TriageForm.jsx for better maintainability
 */

import React from 'react';

// Color mapping for accent colors - cleaner than nested ternaries
const accentColors = {
    teal: {
        border: 'border-l-teal-500',
        icon: 'text-teal-600',
        checkbox: 'border-teal-500 bg-teal-50',
        checkboxRing: 'focus:ring-teal-500',
        checkboxText: 'text-teal-600'
    },
    blue: {
        border: 'border-l-blue-500',
        icon: 'text-blue-600',
        checkbox: 'border-blue-500 bg-blue-50',
        checkboxRing: 'focus:ring-blue-500',
        checkboxText: 'text-blue-600'
    },
    amber: {
        border: 'border-l-amber-500',
        icon: 'text-amber-600',
        checkbox: 'border-amber-500 bg-amber-50',
        checkboxRing: 'focus:ring-amber-500',
        checkboxText: 'text-amber-600'
    },
    rose: {
        border: 'border-l-rose-500',
        icon: 'text-rose-600',
        checkbox: 'border-rose-500 bg-rose-50',
        checkboxRing: 'focus:ring-rose-500',
        checkboxText: 'text-rose-600'
    },
    purple: {
        border: 'border-l-purple-500',
        icon: 'text-purple-600',
        checkbox: 'border-purple-500 bg-purple-50',
        checkboxRing: 'focus:ring-purple-500',
        checkboxText: 'text-purple-600'
    },
    emerald: {
        border: 'border-l-emerald-500',
        icon: 'text-emerald-600',
        checkbox: 'border-emerald-500 bg-emerald-50',
        checkboxRing: 'focus:ring-emerald-500',
        checkboxText: 'text-emerald-600'
    }
};

/**
 * SectionCard - A styled container for form sections
 * Features: Left accent border, icon, bilingual title (English | Arabic)
 * 
 * @param {Component} icon - Lucide icon component
 * @param {string} title - English section title
 * @param {string} titleAr - Arabic section title
 * @param {string} accentColor - One of: teal, blue, amber, rose, purple, emerald
 */
export const SectionCard = ({ icon: Icon, title, titleAr, children, accentColor = "teal" }) => {
    const colors = accentColors[accentColor] || accentColors.teal;
    
    return (
        <div className={`bg-white rounded-xl border-l-4 ${colors.border} shadow-sm mb-5`}>
            <div className="px-5 py-4 border-b border-slate-100">
                <h3 className="flex items-center gap-2 text-slate-800 font-semibold">
                    {Icon && <Icon className={`w-5 h-5 ${colors.icon}`} />}
                    {title}
                    <span className="text-slate-400 font-normal text-sm mr-1">|</span>
                    <span className="text-slate-500 font-normal text-sm font-arabic">{titleAr}</span>
                </h3>
            </div>
            <div className="p-5">{children}</div>
        </div>
    );
};

/**
 * InputField - Styled text/number input with bilingual label
 */
export const InputField = ({ label, labelAr, className = "", ...props }) => (
    <div className={className}>
        <label className="block text-sm font-medium text-slate-700 mb-1.5">
            {label}
            {labelAr && <span className="text-slate-400 font-normal"> | {labelAr}</span>}
        </label>
        <input
            {...props}
            className="w-full px-3 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500 transition-colors text-slate-800 placeholder-slate-400"
        />
    </div>
);

/**
 * SelectField - Styled select dropdown with bilingual label
 */
export const SelectField = ({ label, labelAr, children, className = "", ...props }) => (
    <div className={className}>
        <label className="block text-sm font-medium text-slate-700 mb-1.5">
            {label}
            {labelAr && <span className="text-slate-400 font-normal"> | {labelAr}</span>}
        </label>
        <select
            {...props}
            className="w-full px-3 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500 transition-colors text-slate-800 bg-white appearance-none cursor-pointer"
        >
            {children}
        </select>
    </div>
);

/**
 * VitalInput - Compact input for vital signs with icon and unit
 * Used in the Vital Signs section for a clean, uniform layout
 */
export const VitalInput = ({ icon: Icon, label, unit, name, value, onChange }) => (
    <div className="bg-slate-50 rounded-lg p-3 border border-slate-200">
        <label className="flex items-center gap-1.5 text-xs font-medium text-slate-500 mb-2">
            <Icon className="w-3.5 h-3.5" /> {label}
        </label>
        <div className="flex items-baseline gap-1">
            <input
                type="number"
                name={name}
                value={value}
                onChange={onChange}
                placeholder="--"
                className="w-full bg-white border border-slate-300 rounded px-2 py-1.5 text-lg font-semibold text-slate-800 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
            />
            <span className="text-xs text-slate-400 whitespace-nowrap">{unit}</span>
        </div>
    </div>
);

/**
 * CheckboxCard - Styled checkbox with title and subtitle
 * Changes appearance when checked - used for clinical risk factors
 */
export const CheckboxCard = ({ 
    checked, 
    onChange, 
    title, 
    subtitle, 
    name,
    accentColor = "teal" 
}) => {
    const colors = accentColors[accentColor] || accentColors.teal;
    
    return (
        <label className={`
            flex items-start gap-3 p-4 rounded-lg border-2 cursor-pointer transition-all
            ${checked ? colors.checkbox : 'border-slate-200 bg-white hover:border-slate-300'}
        `}>
            <input
                type="checkbox"
                name={name}
                checked={checked}
                onChange={onChange}
                className={`mt-0.5 w-5 h-5 ${colors.checkboxText} border-slate-300 rounded ${colors.checkboxRing}`}
            />
            <div>
                <span className="font-medium text-slate-800 block">{title}</span>
                {subtitle && <span className="text-xs text-slate-500">{subtitle}</span>}
            </div>
        </label>
    );
};

export default {
    SectionCard,
    InputField,
    SelectField,
    VitalInput,
    CheckboxCard
};
