import React, { useState } from 'react';
import { Download, AlertCircle, Lock } from 'lucide-react';

const ExportDialog = ({ onConfirm, onCancel, loading = false }) => {
  const [acknowledged, setAcknowledged] = useState(false);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="w-full max-w-2xl bg-white rounded-2xl border border-slate-200 shadow-2xl">
        <div className="flex items-center gap-3 px-6 py-4 border-b border-slate-100">
          <div className="w-10 h-10 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center">
            <Lock className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-900">Export Triage Data</h2>
            <p className="text-xs text-slate-500">Read and acknowledge before download</p>
          </div>
        </div>

        <div className="px-6 py-5">
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-amber-700 mt-0.5 shrink-0" />
              <div className="space-y-3 text-sm text-slate-700">
                <div>
                  <h3 className="font-semibold text-slate-900">Important: Data Scope and Privacy</h3>
                </div>
                <div>
                  <strong>What You Are Exporting:</strong>
                  <p>This export contains cases you authored (submitted) plus cases you confirmed or reviewed. This is not a system-wide export.</p>
                </div>
                <div>
                  <strong>Privacy Protection:</strong>
                  <p>Patient identifiers are Safe Harbor de-identified. IDs are hashed and names are fully redacted.</p>
                </div>
                <div>
                  <strong>Your Responsibility:</strong>
                  <ul className="list-disc list-inside space-y-1">
                    <li>Do not share on unsecured channels</li>
                    <li>Delete after review (retain maximum 30 days for quality workflows)</li>
                    <li>This export action is logged and auditable</li>
                  </ul>
                </div>
                <div>
                  <strong>Regulatory Note:</strong>
                  <p>Designed to align with GAHAR privacy expectations. System-wide exports require supervisor access.</p>
                </div>
              </div>
            </div>
          </div>

          <label className="mt-4 flex items-start gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={acknowledged}
              onChange={(event) => setAcknowledged(event.target.checked)}
              className="mt-1"
            />
            <span>I understand this export contains my authored and reviewed cases and I will handle it securely.</span>
          </label>
        </div>

        <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-slate-100">
          <button
            type="button"
            onClick={onCancel}
            disabled={loading}
            className="px-4 py-2 text-sm rounded-md border border-slate-300 text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={!acknowledged || loading}
            className="px-4 py-2 text-sm rounded-md bg-[#1a5f7a] text-white hover:bg-[#164d63] disabled:opacity-50 flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            {loading ? 'Exporting...' : 'Export My Cases'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ExportDialog;
