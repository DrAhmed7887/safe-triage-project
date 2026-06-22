import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Activity, AlertTriangle, ShieldCheck } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'https://safe-triage-eciux5h4aq-uc.a.run.app';

const PERIODS = [
  { key: 'today', label: 'Today' },
  { key: 'week', label: 'Week' },
  { key: 'month', label: 'Month' },
];

export default function TriageStatsWidget() {
  const [period, setPeriod] = useState('today');
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [error, setError] = useState('');

  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/stats/${period}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const payload = await response.json();
      setStats(payload?.statistics || {});
      setLastUpdated(new Date());
      setError('');
    } catch (err) {
      setError(err?.message || 'Failed to fetch stats');
    } finally {
      setLoading(false);
    }
  }, [period]);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    if (isMounted) {
      fetchStats();
    }
    const interval = setInterval(fetchStats, 60000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [fetchStats]);

  const metric = useMemo(() => {
    const totalCases = stats?.total_cases?.count || 0;
    const criticalCases = stats?.critical_cases?.count || 0;
    const underTriage = stats?.under_triage_count?.count || 0;
    const responseTime = stats?.avg_response_time?.avg_seconds || 0;
    const overrideRate = stats?.override_rate?.override_percentage || 0;
    const avgNews2 = stats?.avg_news2?.avg_score || 0;
    const esiDistribution = Array.isArray(stats?.esi_distribution) ? stats.esi_distribution : [];
    return {
      totalCases,
      criticalCases,
      underTriage,
      responseTime,
      overrideRate,
      avgNews2,
      esiDistribution,
    };
  }, [stats]);

  return (
    <section className="bg-white rounded-xl shadow-lg border border-slate-100 p-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-5">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Triage Statistics</h2>
          <p className="text-xs text-slate-500">
            HIPAA-compliant aggregate data only. No PHI exposed.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {PERIODS.map((item) => (
            <button
              key={item.key}
              type="button"
              onClick={() => setPeriod(item.key)}
              className={`px-3 py-1.5 text-sm rounded-md border transition ${
                period === item.key
                  ? 'bg-[#1a5f7a] text-white border-[#1a5f7a]'
                  : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-50'
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div className="text-sm text-slate-500 py-4">Loading statistics...</div>
      )}

      {!loading && error && (
        <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-md px-3 py-2 mb-4">
          Failed to load live statistics: {error}
        </div>
      )}

      {!loading && !error && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mb-5">
            <StatCard label="Total Cases" value={metric.totalCases} tone="neutral" />
            <StatCard
              label="Under-Triage"
              value={metric.underTriage}
              hint={metric.underTriage === 0 ? 'Target met' : 'Needs review'}
              tone={metric.underTriage === 0 ? 'good' : 'bad'}
            />
            <StatCard label="Critical (ESI 1-2)" value={metric.criticalCases} tone="warn" />
            <StatCard label="Avg Response Time" value={`${Number(metric.responseTime || 0).toFixed(1)}s`} tone="neutral" />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-5">
            <div className="bg-slate-50 rounded-lg border border-slate-200 p-4">
              <div className="flex items-center gap-2 mb-2 text-slate-700">
                <Activity className="w-4 h-4" />
                <span className="text-sm font-semibold">Avg NEWS2</span>
              </div>
              <div className="text-2xl font-bold text-slate-900">{metric.avgNews2 || 0}</div>
            </div>
            <div className="bg-slate-50 rounded-lg border border-slate-200 p-4">
              <div className="flex items-center gap-2 mb-2 text-slate-700">
                <AlertTriangle className="w-4 h-4" />
                <span className="text-sm font-semibold">Override Rate</span>
              </div>
              <div className="text-2xl font-bold text-slate-900">{metric.overrideRate || 0}%</div>
            </div>
            <div className="bg-slate-50 rounded-lg border border-slate-200 p-4">
              <div className="flex items-center gap-2 mb-2 text-slate-700">
                <ShieldCheck className="w-4 h-4" />
                <span className="text-sm font-semibold">De-identification</span>
              </div>
              <div className="text-sm font-medium text-slate-800">Safe Harbor active</div>
              <div className="text-xs text-slate-500">ESI buckets &lt;5 merged as Other</div>
            </div>
          </div>

          <div className="bg-slate-50 rounded-lg border border-slate-200 p-4">
            <h3 className="text-sm font-semibold text-slate-800 mb-3">ESI Distribution</h3>
            <div className="space-y-3">
              {metric.esiDistribution.map((bucket) => (
                <BarRow
                  key={bucket.esi_level}
                  label={`ESI ${bucket.esi_level}`}
                  count={bucket.count}
                  percentage={bucket.percentage}
                />
              ))}
              {metric.esiDistribution.length === 0 && (
                <div className="text-xs text-slate-500">No data for selected period.</div>
              )}
            </div>
          </div>
        </>
      )}

      <div className="mt-4 text-xs text-slate-500">
        Updated: {lastUpdated ? lastUpdated.toLocaleTimeString('en-US') : '--:--:--'} | Privacy: aggregated counts and percentages only.
      </div>
    </section>
  );
}

function StatCard({ label, value, hint, tone }) {
  const toneClass =
    tone === 'good'
      ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
      : tone === 'bad'
        ? 'bg-red-50 border-red-200 text-red-900'
        : tone === 'warn'
          ? 'bg-orange-50 border-orange-200 text-orange-900'
          : 'bg-slate-50 border-slate-200 text-slate-900';

  return (
    <div className={`rounded-lg border p-4 ${toneClass}`}>
      <div className="text-sm font-medium">{label}</div>
      <div className="text-3xl font-bold mt-1">{value}</div>
      {hint ? <div className="text-xs mt-1 opacity-80">{hint}</div> : null}
    </div>
  );
}

function BarRow({ label, count, percentage }) {
  const width = Math.max(0, Math.min(100, Number(percentage || 0)));
  return (
    <div>
      <div className="flex items-center justify-between text-xs text-slate-600 mb-1">
        <span>{label}</span>
        <span>
          {count} ({width}%)
        </span>
      </div>
      <div className="h-2 rounded-full bg-slate-200 overflow-hidden">
        <div className="h-full bg-[#159895] rounded-full" style={{ width: `${width}%` }} />
      </div>
    </div>
  );
}
