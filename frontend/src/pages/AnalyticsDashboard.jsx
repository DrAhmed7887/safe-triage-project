import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getIdToken } from '../lib/firebaseClient';

const API_URL = import.meta.env.VITE_API_URL || import.meta.env.REACT_APP_API_URL || 'http://localhost:8000';

function MetricCard({ title, value, subtitle = '', tone = 'default' }) {
  const toneClass =
    tone === 'success'
      ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
      : tone === 'warning'
      ? 'bg-amber-50 border-amber-200 text-amber-800'
      : 'bg-white border-slate-200 text-slate-800';
  return (
    <div className={`rounded-xl border p-4 ${toneClass}`}>
      <div className="text-sm font-medium">{title}</div>
      <div className="mt-1 text-3xl font-bold">{value}</div>
      {subtitle ? <div className="mt-1 text-xs opacity-80">{subtitle}</div> : null}
    </div>
  );
}

export default function AnalyticsDashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [data, setData] = useState(null);
  const [range, setRange] = useState('24h');

  const normalizedRole = (user?.role || '').toString().toLowerCase();
  const isSupervisor = normalizedRole === 'supervisor' || normalizedRole === 'admin';

  const dateParams = useMemo(() => {
    const end = new Date();
    const start = new Date(end.getTime() - (range === '24h' ? 24 * 60 * 60 * 1000 : 7 * 24 * 60 * 60 * 1000));
    return new URLSearchParams({
      start_date: start.toISOString(),
      end_date: end.toISOString(),
    });
  }, [range]);

  useEffect(() => {
    let cancelled = false;
    const fetchAnalytics = async () => {
      setLoading(true);
      setError('');
      try {
        const token = await getIdToken();
        if (!token) throw new Error('Missing auth token');
        const response = await fetch(`${API_URL}/analytics/dashboard/summary?${dateParams.toString()}`, {
          headers: {
            Authorization: `Bearer ${token}`,
            'X-User-Role': user?.role || '',
          },
        });
        if (!response.ok) {
          const payload = await response.json().catch(() => ({}));
          throw new Error(payload?.detail || 'Access denied');
        }
        const payload = await response.json();
        if (cancelled) return;
        setData(payload);

        await fetch(`${API_URL}/analytics/audit/log-access`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
            'X-User-Role': user?.role || '',
          },
          body: JSON.stringify({
            action: 'view_analytics_dashboard',
            metadata: { range },
          }),
        }).catch(() => {});
      } catch (err) {
        if (!cancelled) setError(err?.message || 'Failed to load analytics');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    if (isSupervisor) {
      fetchAnalytics();
    } else {
      setLoading(false);
      setError('Supervisor access required');
    }
    return () => {
      cancelled = true;
    };
  }, [dateParams, isSupervisor, range, user?.role]);

  if (!isSupervisor) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-800">
          <div className="font-semibold">Access Denied | تم رفض الوصول</div>
          <div className="text-sm mt-1">Analytics dashboard is restricted to supervisors only.</div>
        </div>
        <button
          onClick={() => navigate('/dashboard')}
          className="mt-4 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 hover:bg-slate-100"
        >
          Back to Dashboard
        </button>
      </div>
    );
  }

  const stats = data?.statistics || {};
  const total = stats?.total_cases?.count || 0;
  const under = stats?.under_triage?.incidents || 0;
  const overPct = stats?.override_rate?.override_percentage || 0;
  const avgSecs = stats?.avg_response_time?.avg_seconds || 0;
  const esiDist = stats?.esi_distribution || [];
  const newsDist = stats?.news2_distribution || [];
  const hourly = stats?.hourly_volume || [];

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-slate-900">Analytics Dashboard | لوحة التحليلات</h1>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setRange('24h')}
            className={`rounded-md px-3 py-1.5 text-sm ${range === '24h' ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-700'}`}
          >
            Last 24h
          </button>
          <button
            onClick={() => setRange('7d')}
            className={`rounded-md px-3 py-1.5 text-sm ${range === '7d' ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-700'}`}
          >
            Last 7d
          </button>
          <button
            onClick={() => navigate('/dashboard')}
            className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-100"
          >
            Back
          </button>
        </div>
      </div>

      <div className="mb-4 rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
        Privacy notice: anonymized aggregate statistics only. No individual patient data is shown.
      </div>

      {error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-red-800">{error}</div>
      ) : null}

      {loading ? (
        <div className="rounded-lg border border-slate-200 bg-white p-6 text-slate-600">Loading analytics...</div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
            <MetricCard title="Total Cases" value={total} />
            <MetricCard
              title="Under-Triage"
              value={`${under} ${under > 0 ? '⚠️' : '✅'}`}
              subtitle="Target: 0"
              tone={under > 0 ? 'warning' : 'success'}
            />
            <MetricCard title="Override Rate" value={`${overPct}%`} subtitle={`${stats?.override_rate?.overrides || 0} / ${stats?.override_rate?.total || 0}`} />
            <MetricCard title="Avg Response Time" value={`${avgSecs}s`} subtitle="Confirmation response" />
          </div>

          <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <h2 className="mb-3 text-lg font-semibold text-slate-900">ESI Distribution</h2>
              <div className="space-y-2">
                {esiDist.map((row) => (
                  <div key={`esi-${row.esi_level}`} className="flex items-center gap-3">
                    <div className="w-20 text-sm text-slate-700">ESI {row.esi_level}</div>
                    <div className="h-3 flex-1 rounded bg-slate-100">
                      <div
                        className="h-3 rounded bg-blue-500"
                        style={{ width: `${Math.max(3, Number(row.percentage || 0))}%` }}
                      />
                    </div>
                    <div className="w-16 text-right text-sm text-slate-700">{row.count}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <h2 className="mb-3 text-lg font-semibold text-slate-900">NEWS2 Risk Distribution</h2>
              <div className="space-y-2">
                {newsDist.map((row) => (
                  <div key={row.risk_level} className="flex items-center justify-between rounded border border-slate-100 bg-slate-50 px-3 py-2 text-sm">
                    <span>{row.risk_level}</span>
                    <span className="font-semibold">{row.count}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-6 rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="mb-3 text-lg font-semibold text-slate-900">Hourly Case Volume</h2>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-left text-slate-600">
                    <th className="px-2 py-2">Hour</th>
                    <th className="px-2 py-2">Cases</th>
                  </tr>
                </thead>
                <tbody>
                  {hourly.map((row) => (
                    <tr key={`h-${row.hour}`} className="border-b border-slate-100">
                      <td className="px-2 py-2">{row.hour}</td>
                      <td className="px-2 py-2">{row.cases}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
