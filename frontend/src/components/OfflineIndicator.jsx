import React, { useState, useEffect } from 'react';
import { WifiOff, AlertTriangle } from 'lucide-react';

const OfflineIndicator = () => {
    const [isOnline, setIsOnline] = useState(navigator.onLine);

    useEffect(() => {
        const handleOnline = () => setIsOnline(true);
        const handleOffline = () => setIsOnline(false);

        window.addEventListener('online', handleOnline);
        window.addEventListener('offline', handleOffline);

        return () => {
            window.removeEventListener('online', handleOnline);
            window.removeEventListener('offline', handleOffline);
        };
    }, []);

    if (isOnline) return null;

    return (
        <div className="bg-yellow-50 border-b border-yellow-200 py-3 px-4 shadow-sm animate-in fade-in slide-in-from-top duration-300">
            <div className="max-w-7xl mx-auto flex items-center justify-between gap-3">
                <div className="flex items-center gap-2 text-yellow-800">
                    <WifiOff className="w-5 h-5" />
                    <span className="font-semibold text-sm md:text-base">
                        ⚠️ Offline Mode - Limited functionality
                    </span>
                </div>
                <div className="hidden md:block text-yellow-700 font-arabic text-sm" dir="rtl">
                    وضع عدم الاتصال - وظائف محدودة
                </div>
                <div className="flex items-center gap-1 bg-yellow-100 text-yellow-700 px-2 py-1 rounded text-xs font-bold uppercase tracking-wider border border-yellow-200">
                    <AlertTriangle className="w-3 h-3" />
                    Offline
                </div>
            </div>
        </div>
    );
};

export default OfflineIndicator;
