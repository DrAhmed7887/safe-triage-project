import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Activity, LogOut } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import NotificationBell from './NotificationBell';

const TABS = [
    { id: 'triage',    en: 'Triage',    ar: 'فرز',     to: '/dashboard' },
    { id: 'queue',     en: 'Queue',     ar: 'الطابور', to: '/queue' },
    { id: 'analytics', en: 'Analytics', ar: 'التحليلات', to: '/analytics/dashboard', supervisorOnly: true },
    { id: 'knowledge', en: 'Knowledge', ar: 'المعرفة', to: '/knowledge' },
];

const ROLE_LABEL = {
    nurse: 'Triage Nurse',
    doctor: 'Doctor',
    physician: 'Physician',
    supervisor: 'Supervisor',
    admin: 'Admin',
};

const isActiveRoute = (pathname, to) => {
    if (to === '/dashboard') return pathname === '/dashboard' || pathname === '/';
    if (to === '/analytics/dashboard') return pathname.startsWith('/analytics');
    return pathname.startsWith(to);
};

const getInitials = (name) => {
    if (!name) return 'CL';
    const parts = name.trim().split(/\s+/).filter(Boolean);
    if (parts.length === 0) return 'CL';
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
};

/**
 * AppHeader — top navigation strip shared across Dashboard, Queue, Analytics,
 * MedGemma, and Knowledge pages. Adapted from ui_kits/clinical-app/AppHeader.jsx
 * to the production frontend's React Router + auth context.
 *
 * Props:
 *   queueCount — optional number, renders a count chip on the Queue tab when > 0
 */
export default function AppHeader({ queueCount }) {
    const { user, logout } = useAuth();
    const location = useLocation();

    const role = (user?.role || 'nurse').toString().toLowerCase();
    const isSupervisor = role === 'supervisor' || role === 'admin';
    const initials = getInitials(user?.name);
    const displayName = user?.name ? `Dr. ${user.name}` : 'Clinician';
    const roleLabel = ROLE_LABEL[role] || 'Clinician';

    return (
        <header className="bg-white sticky top-0 z-30 border-b border-slate-200 shadow-sm">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 min-h-16 flex flex-wrap items-center justify-between gap-y-2 gap-x-4 py-2">
                {/* Brand */}
                <Link to="/dashboard" className="flex items-center gap-3 min-w-0 group">
                    <div className="bg-teal-600 p-2 rounded-xl shadow-sm shadow-teal-600/20 flex-shrink-0 group-hover:shadow-teal-600/40 transition-shadow">
                        <Activity className="w-6 h-6 text-white" aria-hidden="true" />
                    </div>
                    <div className="min-w-0">
                        <h1 className="text-base sm:text-lg font-bold text-slate-900 leading-tight tracking-tight">
                            SAFE-Triage
                        </h1>
                        <p className="text-[11px] text-slate-500 leading-tight flex items-center gap-1.5 flex-wrap">
                            <span className="truncate max-w-[160px]">ED · {displayName}</span>
                            <span className="text-slate-300" aria-hidden="true">|</span>
                            <span dir="rtl" className="font-arabic">قسم الطوارئ</span>
                        </p>
                    </div>
                </Link>

                {/* Tabs */}
                <nav
                    className="flex items-center gap-0.5 sm:gap-1 overflow-x-auto min-w-0 max-w-full -mx-1 px-1"
                    aria-label="Primary navigation"
                >
                    {TABS.map((tab) => {
                        const active = isActiveRoute(location.pathname, tab.to);
                        const restricted = tab.supervisorOnly && !isSupervisor;
                        const showCountChip =
                            tab.id === 'queue' && typeof queueCount === 'number' && queueCount > 0;

                        const inner = (
                            <span className="inline-flex items-center gap-1.5">
                                <span>{tab.en}</span>
                                <span
                                    className="text-slate-300 font-normal hidden sm:inline"
                                    aria-hidden="true"
                                >
                                    |
                                </span>
                                <span
                                    dir="rtl"
                                    className="font-arabic text-[12px] hidden sm:inline"
                                >
                                    {tab.ar}
                                </span>
                                {showCountChip && (
                                    <span
                                        className="font-mono text-[10px] font-bold bg-red-50 text-red-700 border border-red-200 rounded-full px-1.5 py-0.5 ml-0.5"
                                        aria-label={`${queueCount} cases in queue`}
                                    >
                                        {queueCount}
                                    </span>
                                )}
                            </span>
                        );

                        const baseClass =
                            'px-2.5 sm:px-3 py-1.5 rounded-lg text-[13px] font-medium whitespace-nowrap flex-shrink-0 transition-colors';

                        if (restricted) {
                            return (
                                <span
                                    key={tab.id}
                                    className={`${baseClass} text-slate-300 cursor-not-allowed`}
                                    title="Supervisor role required"
                                    aria-disabled="true"
                                >
                                    {inner}
                                </span>
                            );
                        }

                        return (
                            <Link
                                key={tab.id}
                                to={tab.to}
                                className={`${baseClass} ${
                                    active
                                        ? 'bg-slate-100 text-slate-900 font-semibold'
                                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                                }`}
                                aria-current={active ? 'page' : undefined}
                            >
                                {inner}
                            </Link>
                        );
                    })}
                </nav>

                {/* Right side: bell, user, logout */}
                <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
                    <NotificationBell />
                    <div className="hidden md:flex items-center gap-2.5 pl-2 border-l border-slate-200">
                        <div
                            className="w-9 h-9 rounded-full bg-gradient-to-br from-teal-600 to-teal-700 text-white inline-flex items-center justify-center font-bold text-[13px]"
                            role="img"
                            aria-label={displayName}
                        >
                            {initials}
                        </div>
                        <div className="flex flex-col leading-tight max-w-[140px]">
                            <span className="text-[12.5px] font-semibold text-slate-900 truncate">
                                {displayName}
                            </span>
                            <span className="text-[10.5px] text-slate-500 truncate">
                                {roleLabel} · On call
                            </span>
                        </div>
                    </div>
                    <button
                        onClick={logout}
                        className="text-slate-500 hover:text-red-600 p-1.5 rounded-lg hover:bg-slate-50 transition-colors flex items-center gap-1"
                        aria-label="Sign out"
                        title="Sign out"
                    >
                        <LogOut className="w-4 h-4" aria-hidden="true" />
                        <span className="text-[12px] font-medium hidden lg:inline">Sign Out</span>
                    </button>
                </div>
            </div>
        </header>
    );
}
