import React from 'react';
import { AlertTriangle } from 'lucide-react';

export default function ConfirmationDialog({
    open,
    title = 'Please confirm',
    items = [],
    onConfirm,
    onCancel,
}) {
    if (!open) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 px-4">
            <div className="w-full max-w-2xl rounded-xl bg-white shadow-2xl border border-slate-200">
                <div className="px-5 py-4 border-b border-slate-200 flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5 text-amber-600" />
                    <h3 className="text-base font-semibold text-slate-900">{title}</h3>
                </div>
                <div className="px-5 py-4 max-h-[60vh] overflow-y-auto">
                    <p className="text-sm text-slate-700 mb-3">
                        Unusual values were detected. Confirm to proceed or cancel to review entries.
                    </p>
                    <ul className="space-y-2">
                        {items.map((item, idx) => (
                            <li key={`${item.type || 'warning'}-${idx}`} className="rounded-md border border-amber-200 bg-amber-50 p-3">
                                <p className="text-sm font-medium text-amber-900">{item.message}</p>
                                {item.messageAr ? (
                                    <p className="text-xs text-amber-800 mt-1" dir="rtl">
                                        {item.messageAr}
                                    </p>
                                ) : null}
                            </li>
                        ))}
                    </ul>
                </div>
                <div className="px-5 py-4 border-t border-slate-200 flex items-center justify-end gap-2">
                    <button
                        type="button"
                        onClick={onCancel}
                        className="px-4 py-2 rounded-md border border-slate-300 text-slate-700 hover:bg-slate-50"
                    >
                        Cancel | إلغاء
                    </button>
                    <button
                        type="button"
                        onClick={onConfirm}
                        className="px-4 py-2 rounded-md bg-amber-600 text-white hover:bg-amber-700"
                    >
                        Confirm & Continue | تأكيد والمتابعة
                    </button>
                </div>
            </div>
        </div>
    );
}
