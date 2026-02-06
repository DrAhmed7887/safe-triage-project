import React, { useState, useEffect } from 'react';
import {
  BarChart3,
  Users,
  AlertCircle,
  AlertTriangle,
  Globe
} from 'lucide-react';

const TriageStats = ({ data }) => {
  const [lang, setLang] = useState('en');
  const [backendStats, setBackendStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  const mockData = {
    total: 38,
    esiBreakdown: { ESI1: 2, ESI2: 8, ESI3: 18, ESI4: 14, ESI5: 5 },
    underTriage: 0,
    overrideRate: 0
  };

  useEffect(() => {
    fetch(`${API_URL}/stats?days=1`)
      .then((res) => res.json())
      .then((payload) => {
        if (payload?.error || !payload?.esiBreakdown) {
          throw new Error(payload?.error || 'Invalid stats response');
        }
        setBackendStats(payload);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Backend fetch failed, using mock data", err);
        setLoading(false);
      });
  }, []);

  const stats = backendStats || data || mockData;
  const underTriage = Number.isFinite(stats?.underTriage) ? stats.underTriage : 0;

  const translations = {
    en: {
      title: "Triage Statistics Today",
      total: "Total Triages",
      esiBreakdown: "ESI Level Breakdown",
      underTriage: "Under-Triage",
      overrideRate: "Override Rate",
      switchLang: "العربية",
      dir: "ltr",
      esiLabels: {
        ESI1: "ESI 1 (Resuscitation)",
        ESI2: "ESI 2 (Emergent)",
        ESI3: "ESI 3 (Urgent)",
        ESI4: "ESI 4 (Less Urgent)",
        ESI5: "ESI 5 (Non-Urgent)"
      }
    },
    ar: {
      title: "إحصائيات الفرز اليوم",
      total: "إجمالي الفرز",
      esiBreakdown: "توزيع مستويات ESI",
      underTriage: "نقص الفرز",
      overrideRate: "معدل التجاوز",
      switchLang: "English",
      dir: "rtl",
      esiLabels: {
        ESI1: "ESI 1 (إنعاش)",
        ESI2: "ESI 2 (طوارئ)",
        ESI3: "ESI 3 (عاجل)",
        ESI4: "ESI 4 (أقل استعجالاً)",
        ESI5: "ESI 5 (غير عاجل)"
      }
    }
  };

  const t = translations[lang];

  const esiColors = {
    ESI1: 'bg-red-500',
    ESI2: 'bg-orange-500',
    ESI3: 'bg-yellow-400',
    ESI4: 'bg-green-500',
    ESI5: 'bg-blue-500'
  };

  const maxEsiCount = Math.max(...Object.values(stats.esiBreakdown));

  const SkeletonCard = () => (
    <div className="bg-slate-50 p-6 rounded-xl border border-slate-100 animate-pulse">
      <div className="flex items-center justify-between mb-4">
        <div className="h-4 bg-slate-200 rounded w-1/2"></div>
        <div className="w-9 h-9 bg-slate-200 rounded-lg"></div>
      </div>
      <div className="h-10 bg-slate-200 rounded w-1/4"></div>
    </div>
  );

  return (
    <div className={`p-6 bg-white rounded-xl shadow-lg border border-slate-100 ${t.dir === 'rtl' ? 'font-arabic' : ''}`} dir={t.dir}>
      <div className="flex justify-between items-center mb-8">
        <h2 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
          <BarChart3 className="w-6 h-6 text-blue-600" />
          {t.title}
        </h2>
        <button
          onClick={() => setLang(lang === 'en' ? 'ar' : 'en')}
          className="flex items-center gap-2 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 transition-colors rounded-lg text-sm font-medium text-slate-600"
        >
          <Globe className="w-4 h-4" />
          {t.switchLang}
        </button>
      </div>

      {loading ? (
        <div className="space-y-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
          <div className="bg-slate-50 p-6 rounded-xl border border-slate-100 animate-pulse">
            <div className="h-6 bg-slate-200 rounded w-1/4 mb-6"></div>
            <div className="space-y-6">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="space-y-2">
                  <div className="flex justify-between">
                    <div className="h-4 bg-slate-200 rounded w-1/3"></div>
                    <div className="h-4 bg-slate-200 rounded w-8"></div>
                  </div>
                  <div className="h-3 bg-slate-200 rounded-full"></div>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            {/* Total Card */}
            <div className="bg-slate-50 p-6 rounded-xl border border-slate-100 hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between mb-4">
                <span className="text-slate-500 font-medium">{t.total}</span>
                <div className="p-2 bg-blue-100 rounded-lg">
                  <Users className="w-5 h-5 text-blue-600" />
                </div>
              </div>
              <div className="text-4xl font-bold text-slate-800">{stats.total}</div>
            </div>

            {/* Under-Triage Card */}
            <div className="bg-slate-50 p-6 rounded-xl border border-slate-100 hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between mb-4">
                <span className="text-slate-500 font-medium">{t.underTriage}</span>
                <div className={`p-2 rounded-lg ${underTriage > 0 ? 'bg-red-100' : 'bg-emerald-100'}`}>
                  <AlertTriangle className={`w-5 h-5 ${underTriage > 0 ? 'text-red-600' : 'text-emerald-600'}`} />
                </div>
              </div>
              <div className={`text-3xl font-bold ${underTriage > 0 ? 'text-red-700' : 'text-emerald-700'}`}>
                {lang === 'ar'
                  ? `نقص الفرز: ${underTriage} ${underTriage > 0 ? '⚠️' : '✅'}`
                  : `Under-Triage: ${underTriage} ${underTriage > 0 ? '⚠️' : '✅'}`}
              </div>
              <div className="mt-2 text-xs text-slate-400">
                {lang === 'en'
                  ? 'Final ESI higher than AI recommendation'
                  : 'الفرز النهائي أعلى من توصية الذكاء الاصطناعي'}
              </div>
            </div>

            {/* Override Rate Card */}
            <div className="bg-slate-50 p-6 rounded-xl border border-slate-100 hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between mb-4">
                <span className="text-slate-500 font-medium">{t.overrideRate}</span>
                <div className="p-2 bg-amber-100 rounded-lg">
                  <AlertCircle className="w-5 h-5 text-amber-600" />
                </div>
              </div>
              <div className="text-4xl font-bold text-slate-800">{stats.overrideRate}%</div>
              <div className="mt-2 text-sm text-slate-400">
                {lang === 'en' ? 'Clinical overrides of AI suggestions' : 'تجاوزات سريرية لاقتراحات الذكاء الاصطناعي'}
              </div>
            </div>
          </div>

          <div className="bg-slate-50 p-6 rounded-xl border border-slate-100">
            <h3 className="text-lg font-semibold text-slate-800 mb-6">{t.esiBreakdown}</h3>
            <div className="space-y-4">
              {Object.entries(stats.esiBreakdown).map(([level, count]) => (
                <div key={level} className="space-y-1">
                  <div className="flex justify-between text-sm font-medium text-slate-600">
                    <span>{t.esiLabels[level]}</span>
                    <span>{count}</span>
                  </div>
                  <div className="h-3 bg-slate-200 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-1000 ${esiColors[level]}`}
                      style={{ width: `${(count / (maxEsiCount || 1)) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default TriageStats;
