import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getIdToken } from '../lib/firebaseClient';
import AppHeader from '../components/AppHeader';

const API_URL = import.meta.env.VITE_API_URL || import.meta.env.REACT_APP_API_URL || 'http://localhost:8000';

const SEVERITY_COLORS = {
  Critical: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-800', bar: 'bg-red-500', dot: 'bg-red-500' },
  Moderate: { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-800', bar: 'bg-amber-500', dot: 'bg-amber-500' },
  Low: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-800', bar: 'bg-blue-400', dot: 'bg-blue-400' },
};

function KpiCard({ title, value, subtitle, severity }) {
  const colors = SEVERITY_COLORS[severity] || { bg: 'bg-white', border: 'border-slate-200', text: 'text-slate-800' };
  return (
    <div className={`rounded-xl border p-4 ${colors.bg} ${colors.border}`}>
      <div className={`text-sm font-medium ${colors.text}`}>{title}</div>
      <div className={`mt-1 text-3xl font-bold ${colors.text}`}>{value}</div>
      {subtitle && <div className={`mt-1 text-xs opacity-80 ${colors.text}`}>{subtitle}</div>}
    </div>
  );
}

function SeverityBadge({ severity }) {
  const colors = SEVERITY_COLORS[severity] || SEVERITY_COLORS.Low;
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${colors.bg} ${colors.text}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${colors.dot}`} />
      {severity}
    </span>
  );
}

export default function MedGemmaDashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [data, setData] = useState(null);
  const [days, setDays] = useState(7);

  const normalizedRole = (user?.role || '').toString().toLowerCase();
  const isSupervisor = normalizedRole === 'supervisor' || normalizedRole === 'admin';

  useEffect(() => {
    let cancelled = false;
    const fetchData = async () => {
      setLoading(true);
      setError('');
      try {
        const token = await getIdToken();
        const response = await fetch(`${API_URL}/medgemma/dashboard?days=${days}`, {
          headers: {
            Authorization: `Bearer ${token}`,
            'X-User-Role': user?.role || '',
          },
        });
        if (!response.ok) throw new Error('Failed to load MedGemma dashboard');
        const payload = await response.json();
        if (!cancelled) setData(payload);
      } catch (err) {
        if (!cancelled) setError(err?.message || 'Failed to load');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    if (isSupervisor) {
      fetchData();
    } else {
      setLoading(false);
      setError('Supervisor access required');
    }
    return () => { cancelled = true; };
  }, [days, isSupervisor, user?.role]);

  if (!isSupervisor) {
    return (
      <div className="min-h-screen bg-slate-50 font-sans" dir="ltr">
        <AppHeader />
        <main className="max-w-4xl mx-auto p-6">
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-800">
            <div className="font-semibold">Access Denied | تم رفض الوصول</div>
            <div className="text-sm mt-1">MedGemma QA dashboard requires supervisor access.</div>
          </div>
          <button
            onClick={() => navigate('/dashboard')}
            className="mt-4 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 hover:bg-slate-100"
          >
            Back to Triage
          </button>
        </main>
      </div>
    );
  }

  const severity = data?.severity_breakdown || [];
  const patterns = data?.pattern_frequency || [];
  const daily = data?.daily_trend || [];
  const recent = data?.recent_flags || [];
  const totalFlags = data?.total_flags || 0;
  const criticalTotal = data?.critical_total || 0;
  const moderateTotal = severity.find(s => s.severity === 'Moderate')?.total || 0;
  const avgConf = severity.length > 0
    ? (severity.reduce((sum, s) => sum + (s.avg_confidence || 0) * (s.total || 0), 0) / Math.max(totalFlags, 1)).toFixed(2)
    : '—';

  const maxDaily = Math.max(...daily.map(d => d.total_flags || 0), 1);

  return (
    <div className="min-h-screen bg-slate-50 font-sans" dir="ltr">
      <AppHeader />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 inline-flex items-baseline gap-2 flex-wrap">
              <span>MedGemma QA</span>
              <span className="text-slate-300 font-normal" aria-hidden="true">|</span>
              <span dir="rtl" className="font-arabic text-xl text-slate-700">جودة الذكاء الطبي</span>
            </h1>
            <p className="text-sm text-slate-500 mt-0.5">AI quality assurance — flagged case monitoring</p>
          </div>
          <div className="flex items-center gap-2">
            {[7, 14, 30].map(d => (
              <button
                key={d}
                onClick={() => setDays(d)}
                className={`rounded-md px-3 py-1.5 text-sm ${days === d ? 'bg-purple-600 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'}`}
              >
                {d}d
              </button>
            ))}
          </div>
        </div>

      <div className="mb-4 rounded-lg border border-purple-200 bg-purple-50 p-3 text-sm text-purple-800">
        MedGemma reviews triage cases hourly, flagging concerning patterns (silent MI, atypical stroke, sepsis). No patient-identifiable data is shown.
      </div>

      {error && <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-red-800">{error}</div>}

      {loading ? (
        <div className="rounded-lg border border-slate-200 bg-white p-6 text-slate-600">Loading MedGemma analytics...</div>
      ) : (
        <>
          {/* KPI Cards */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
            <KpiCard title="Total Flags" value={totalFlags} subtitle={`Last ${days} days`} />
            <KpiCard title="Critical" value={criticalTotal} subtitle="Disaster alerts sent" severity="Critical" />
            <KpiCard title="Moderate" value={moderateTotal} subtitle="Needs review" severity="Moderate" />
            <KpiCard title="Avg Confidence" value={avgConf} subtitle="Flag confidence score" />
          </div>

          <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
            {/* Daily Trend */}
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <h2 className="mb-3 text-lg font-semibold text-slate-900">Daily Flag Trend</h2>
              {daily.length === 0 ? (
                <div className="text-sm text-slate-500 py-4 text-center">No data yet</div>
              ) : (
                <div className="space-y-2">
                  {daily.map(row => (
                    <div key={row.review_date} className="flex items-center gap-3">
                      <div className="w-24 text-xs text-slate-600 font-mono">{row.review_date}</div>
                      <div className="h-5 flex-1 flex rounded overflow-hidden bg-slate-100">
                        {row.critical > 0 && (
                          <div className="bg-red-500 h-5" style={{ width: `${(row.critical / maxDaily) * 100}%` }} title={`Critical: ${row.critical}`} />
                        )}
                        {row.moderate > 0 && (
                          <div className="bg-amber-500 h-5" style={{ width: `${(row.moderate / maxDaily) * 100}%` }} title={`Moderate: ${row.moderate}`} />
                        )}
                        {row.low > 0 && (
                          <div className="bg-blue-400 h-5" style={{ width: `${(row.low / maxDaily) * 100}%` }} title={`Low: ${row.low}`} />
                        )}
                      </div>
                      <div className="w-10 text-right text-sm font-semibold text-slate-700">{row.total_flags}</div>
                    </div>
                  ))}
                </div>
              )}
              <div className="mt-3 flex gap-4 text-xs text-slate-500">
                <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-red-500" /> Critical</span>
                <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-amber-500" /> Moderate</span>
                <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-blue-400" /> Low</span>
              </div>
            </div>

            {/* Pattern Frequency */}
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <h2 className="mb-3 text-lg font-semibold text-slate-900">Top Patterns Detected</h2>
              {patterns.length === 0 ? (
                <div className="text-sm text-slate-500 py-4 text-center">No patterns flagged yet</div>
              ) : (
                <div className="space-y-2">
                  {patterns.map((p, i) => (
                    <div key={`${p.pattern}-${i}`} className="flex items-center justify-between rounded border border-slate-100 bg-slate-50 px-3 py-2">
                      <div className="flex items-center gap-2">
                        <SeverityBadge severity={p.severity} />
                        <span className="text-sm font-medium text-slate-800">{p.pattern}</span>
                      </div>
                      <div className="text-right">
                        <span className="text-sm font-bold text-slate-700">{p.occurrences}</span>
                        <span className="text-xs text-slate-400 ml-1">({p.avg_confidence})</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Recent Flags Table */}
          <div className="mt-6 rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="mb-3 text-lg font-semibold text-slate-900">Recent Flagged Cases</h2>
            {recent.length === 0 ? (
              <div className="text-sm text-slate-500 py-4 text-center">No flagged cases in this period</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 text-left text-slate-600">
                      <th className="px-2 py-2">Time</th>
                      <th className="px-2 py-2">Severity</th>
                      <th className="px-2 py-2">Pattern</th>
                      <th className="px-2 py-2">Confidence</th>
                      <th className="px-2 py-2">ESI Rec.</th>
                      <th className="px-2 py-2">Action</th>
                      <th className="px-2 py-2">Alert</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recent.map((row, i) => {
                      const ts = row.review_timestamp ? new Date(row.review_timestamp) : null;
                      const timeStr = ts ? `${ts.toLocaleDateString()} ${ts.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : '—';
                      return (
                        <tr key={i} className="border-b border-slate-100 hover:bg-slate-50">
                          <td className="px-2 py-2 text-xs font-mono text-slate-600">{timeStr}</td>
                          <td className="px-2 py-2"><SeverityBadge severity={row.severity} /></td>
                          <td className="px-2 py-2 font-medium text-slate-800">{row.pattern}</td>
                          <td className="px-2 py-2 text-slate-600">{row.confidence?.toFixed(2) || '—'}</td>
                          <td className="px-2 py-2 text-slate-600">{row.esi_recommendation || '—'}</td>
                          <td className="px-2 py-2 text-xs text-slate-500 max-w-[200px] truncate">{row.recommended_action || '—'}</td>
                          <td className="px-2 py-2">{row.disaster_alert_sent ? <span className="text-red-600 font-semibold">Sent</span> : '—'}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Model Info */}
          <div className="mt-4 text-xs text-slate-400 text-center">
            Model: MedGemma 4B-IT (Vertex AI Model Garden) | Data from BigQuery medgemma_flagged_cases
          </div>
        </>
      )}
      </main>
    </div>
  );
}
