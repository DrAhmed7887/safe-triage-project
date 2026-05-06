/**
 * SAFE-Triage Form UI Components
 * Reusable styled components for the triage form.
 * Visual language matched to ui_kits/clinical-app/index.html — tonal header
 * bands on cards, segmented controls, chip-style toggles, monospace vitals
 * with inline out-of-range flagging.
 */

import React from 'react';

const accentColors = {
    teal: {
        border: 'border-l-teal-500',
        icon: 'text-teal-700',
        headerBg: 'bg-teal-50/70',
        chip: 'bg-teal-50 border-teal-300 text-teal-800',
        chipText: 'text-teal-700',
    },
    blue: {
        border: 'border-l-blue-500',
        icon: 'text-blue-700',
        headerBg: 'bg-blue-50/70',
        chip: 'bg-blue-50 border-blue-300 text-blue-800',
        chipText: 'text-blue-700',
    },
    amber: {
        border: 'border-l-amber-500',
        icon: 'text-amber-700',
        headerBg: 'bg-amber-50/60',
        chip: 'bg-amber-50 border-amber-300 text-amber-800',
        chipText: 'text-amber-700',
    },
    rose: {
        border: 'border-l-rose-500',
        icon: 'text-rose-700',
        headerBg: 'bg-rose-50/60',
        chip: 'bg-rose-50 border-rose-300 text-rose-800',
        chipText: 'text-rose-700',
    },
    purple: {
        border: 'border-l-purple-500',
        icon: 'text-purple-700',
        headerBg: 'bg-purple-50/60',
        chip: 'bg-purple-50 border-purple-300 text-purple-800',
        chipText: 'text-purple-700',
    },
    emerald: {
        border: 'border-l-emerald-500',
        icon: 'text-emerald-700',
        headerBg: 'bg-emerald-50/70',
        chip: 'bg-emerald-50 border-emerald-300 text-emerald-800',
        chipText: 'text-emerald-700',
    },
};

/**
 * SectionCard — clinical form section container.
 * White card, hairline border, left accent stripe in the section's tone,
 * tinted header band with icon + bilingual title, and an optional `action`
 * slot at the right of the header (e.g. AI source badge, helper text).
 */
export const SectionCard = ({
    icon: Icon,
    title,
    titleAr,
    children,
    accentColor = 'teal',
    action,
}) => {
    const colors = accentColors[accentColor] || accentColors.teal;

    return (
        <div
            className={`bg-white rounded-2xl border border-slate-200 border-l-4 ${colors.border} shadow-sm overflow-hidden`}
        >
            <header
                className={`px-4 sm:px-5 py-3 border-b border-slate-100 ${colors.headerBg} flex items-center justify-between gap-3`}
            >
                <div className="flex items-center gap-3 min-w-0">
                    {Icon && (
                        <span
                            className={`inline-flex items-center justify-center w-9 h-9 rounded-xl bg-white border border-slate-200 ${colors.icon} flex-shrink-0`}
                        >
                            <Icon className="w-4 h-4" aria-hidden="true" />
                        </span>
                    )}
                    <div className="flex flex-col min-w-0 leading-tight">
                        <h3 className="text-[14.5px] font-semibold text-slate-900 truncate">
                            {title}
                        </h3>
                        {titleAr && (
                            <span
                                className="text-[12px] text-slate-500 font-arabic font-medium truncate"
                                dir="rtl"
                            >
                                {titleAr}
                            </span>
                        )}
                    </div>
                </div>
                {action && <div className="flex-shrink-0">{action}</div>}
            </header>
            <div className="p-4 sm:p-5">{children}</div>
        </div>
    );
};

/**
 * InputField — labeled text/number input with bilingual label.
 */
export const InputField = ({ label, labelAr, className = '', ...props }) => (
    <div className={className}>
        <label className="block text-[12.5px] font-semibold text-slate-700 mb-1.5">
            {label}
            {labelAr && (
                <>
                    <span className="text-slate-300 font-normal mx-1.5" aria-hidden="true">
                        |
                    </span>
                    <span className="text-slate-500 font-normal font-arabic" dir="rtl">
                        {labelAr}
                    </span>
                </>
            )}
        </label>
        <input
            {...props}
            className="w-full px-3 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500 transition-colors text-slate-800 placeholder-slate-400 bg-white"
        />
    </div>
);

/**
 * SelectField — labeled select with bilingual label.
 */
export const SelectField = ({ label, labelAr, children, className = '', ...props }) => (
    <div className={className}>
        <label className="block text-[12.5px] font-semibold text-slate-700 mb-1.5">
            {label}
            {labelAr && (
                <>
                    <span className="text-slate-300 font-normal mx-1.5" aria-hidden="true">
                        |
                    </span>
                    <span className="text-slate-500 font-normal font-arabic" dir="rtl">
                        {labelAr}
                    </span>
                </>
            )}
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
 * Segmented — kit-style toggle pill (slate-100 capsule with one option
 * raised in white). Use for binary or short-list choices like Sex.
 *
 * Props mirror a controlled radio group:
 *   value     — current value
 *   options   — [{ value, label }]
 *   onChange  — (value) => void
 *   ariaLabel — accessible group label
 */
export const Segmented = ({ value, options, onChange, ariaLabel, disabled = false }) => (
    <div
        role="radiogroup"
        aria-label={ariaLabel}
        className="inline-flex bg-slate-100 p-1 rounded-lg border border-slate-200"
    >
        {options.map((opt) => {
            const active = value === opt.value;
            return (
                <button
                    key={opt.value}
                    type="button"
                    role="radio"
                    aria-checked={active}
                    disabled={disabled}
                    onClick={() => !disabled && onChange?.(opt.value)}
                    className={`px-3.5 py-1.5 rounded-md text-[13px] font-semibold transition-colors whitespace-nowrap ${
                        active
                            ? 'bg-white text-slate-900 shadow-sm'
                            : 'text-slate-600 hover:text-slate-900'
                    } ${disabled ? 'opacity-60 cursor-not-allowed' : ''}`}
                >
                    {opt.label}
                </button>
            );
        })}
    </div>
);

/**
 * Chip — toggle pill for clinical risk-factor selection.
 * Mirrors CheckboxCard's contract (name, checked, onChange) so it can be
 * a drop-in replacement in TriageForm risk-factor sections without
 * changing handlers.
 */
export const Chip = ({
    checked,
    onChange,
    name,
    label,
    title,
    accentColor = 'emerald',
}) => {
    const colors = accentColors[accentColor] || accentColors.emerald;
    return (
        <button
            type="button"
            onClick={() =>
                onChange?.({ target: { name, type: 'checkbox', checked: !checked } })
            }
            aria-pressed={checked}
            title={title}
            className={`inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full text-[12.5px] font-medium border transition-all whitespace-nowrap ${
                checked
                    ? `${colors.chip} font-semibold shadow-sm`
                    : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50 hover:border-slate-300'
            }`}
        >
            {checked && (
                <span aria-hidden="true" className="text-[11px] leading-none">
                    ✓
                </span>
            )}
            <span>{label}</span>
        </button>
    );
};

/**
 * VitalInput — compact monospace input for a single vital sign.
 * `flag` (truthy) marks the value as out-of-normal-range, applying a red
 * border, red-tinted background, aria-invalid, and an inline warning line.
 */
export const VitalInput = ({
    icon: Icon,
    label,
    unit,
    name,
    value,
    onChange,
    disabled = false,
    flag = false,
}) => {
    const wrapClass = flag
        ? 'bg-red-50 border-red-300'
        : 'bg-slate-50 border-slate-200';
    const inputBg = disabled
        ? 'bg-slate-100 text-slate-500 cursor-not-allowed'
        : flag
            ? 'bg-white text-red-700'
            : 'bg-white text-slate-800';

    return (
        <div className={`rounded-lg p-3 border ${wrapClass}`}>
            <label className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-500 uppercase tracking-wide mb-2">
                {Icon && <Icon className="w-3.5 h-3.5" aria-hidden="true" />}
                <span>{label}</span>
                {unit && (
                    <span className="ml-auto text-[10px] text-slate-400 font-mono normal-case tracking-normal">
                        {unit}
                    </span>
                )}
            </label>
            <input
                type="number"
                name={name}
                value={value}
                onChange={onChange}
                disabled={disabled}
                placeholder="—"
                aria-invalid={flag ? 'true' : undefined}
                className={`w-full border border-slate-300 rounded px-2 py-1.5 text-lg font-bold font-mono text-center focus:ring-2 focus:ring-teal-500 focus:border-teal-500 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none ${inputBg}`}
            />
            {flag && (
                <p className="mt-1.5 text-[10px] font-semibold text-red-700 leading-tight flex items-center gap-1">
                    <span aria-hidden="true">⚠</span>
                    <span>Outside normal</span>
                </p>
            )}
        </div>
    );
};

/**
 * CheckboxCard — bordered checkbox with title + subtitle.
 * Retained as the default treatment for fields with a longer subtitle
 * (e.g. immunocompromised reasons), while the new `Chip` is used for
 * compact yes/no clinical risk-factor toggles.
 */
export const CheckboxCard = ({
    checked,
    onChange,
    title,
    subtitle,
    name,
    accentColor = 'teal',
}) => {
    const colors = accentColors[accentColor] || accentColors.teal;

    return (
        <label
            className={`flex items-start gap-3 p-4 rounded-lg border-2 cursor-pointer transition-all ${
                checked ? colors.chip : 'border-slate-200 bg-white hover:border-slate-300'
            }`}
        >
            <input
                type="checkbox"
                name={name}
                checked={checked}
                onChange={onChange}
                className={`mt-0.5 w-5 h-5 ${colors.chipText} border-slate-300 rounded focus:ring-2`}
            />
            <div>
                <span className="font-semibold text-slate-800 block text-[13.5px]">{title}</span>
                {subtitle && <span className="text-xs text-slate-500">{subtitle}</span>}
            </div>
        </label>
    );
};

export default {
    SectionCard,
    InputField,
    SelectField,
    Segmented,
    Chip,
    VitalInput,
    CheckboxCard,
};
