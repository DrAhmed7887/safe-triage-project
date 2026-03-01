import React, { useEffect, useState } from 'react';
import { Bell, BellOff } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useFirebaseMessaging } from '../hooks/useFirebaseMessaging';

const MAX_HISTORY = 20;

const buildCaseUrl = (notificationData) => {
    const caseId = notificationData?.patient_id || notificationData?.case_id;
    if (!caseId) {
        return '/dashboard';
    }
    return `/dashboard?case=${encodeURIComponent(caseId)}`;
};

export default function NotificationBell() {
    const navigate = useNavigate();
    const { notification, permissionStatus, clearNotification } = useFirebaseMessaging();
    const [showPanel, setShowPanel] = useState(false);
    const [history, setHistory] = useState([]);

    useEffect(() => {
        if (!notification) {
            return;
        }
        setHistory((current) => [notification, ...current].slice(0, MAX_HISTORY));
    }, [notification]);

    if (permissionStatus === 'unsupported' || permissionStatus === 'denied') {
        return (
            <span
                className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-slate-200 bg-slate-100 text-slate-400"
                title="Browser notifications are unavailable"
            >
                <BellOff className="h-4 w-4" />
            </span>
        );
    }

    return (
        <div className="relative">
            <button
                type="button"
                onClick={() => {
                    setShowPanel((current) => !current);
                    if (notification) {
                        clearNotification();
                    }
                }}
                className="relative inline-flex h-9 w-9 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-600 transition hover:border-blue-300 hover:text-blue-600"
                title="Notifications"
            >
                <Bell className="h-4 w-4" />
                {notification && (
                    <span className="absolute right-1 top-1 inline-flex h-2.5 w-2.5 rounded-full bg-red-500" />
                )}
            </button>

            {showPanel && (
                <div className="absolute right-0 top-11 z-20 w-80 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl">
                    <div className="border-b border-slate-200 px-4 py-3 text-sm font-semibold text-slate-800">
                        Triage Alerts | تنبيهات SAFE-Triage
                    </div>
                    {history.length === 0 ? (
                        <div className="px-4 py-6 text-center text-sm text-slate-500">
                            No alerts yet | لا توجد تنبيهات
                        </div>
                    ) : (
                        <div className="max-h-80 overflow-y-auto">
                            {history.map((item, index) => (
                                <button
                                    type="button"
                                    key={`${item.receivedAt}-${index}`}
                                    onClick={() => {
                                        clearNotification();
                                        setShowPanel(false);
                                        navigate(buildCaseUrl(item.data));
                                    }}
                                    className={`block w-full border-b border-slate-100 px-4 py-3 text-left transition hover:bg-slate-50 ${
                                        index === 0 && notification ? 'bg-amber-50' : 'bg-white'
                                    }`}
                                >
                                    <div className="text-sm font-semibold text-slate-800">{item.title}</div>
                                    <div className="mt-1 text-xs text-slate-600">
                                        {item.body || 'Open the dashboard for details'}
                                    </div>
                                    <div className="mt-2 text-[11px] text-slate-400">
                                        {new Date(item.receivedAt).toLocaleTimeString()}
                                    </div>
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
