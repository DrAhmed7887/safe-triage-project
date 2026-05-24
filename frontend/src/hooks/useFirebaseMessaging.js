import { useEffect, useRef, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { ensureMessaging, isFirebaseConfigured } from '../lib/firebaseClient';

const VAPID_KEY = 'BHlF5l1hUENEJtQiT_RapgStjvNGBgsMvoudCkTyLi8Wk8m_HE-ZflnDhxFyDdw4SFNUzOvwjeSQhQfaPjQ2itc';
const API_URL = import.meta.env.VITE_API_URL || 'https://safe-triage-eciux5h4aq-uc.a.run.app';
const MAX_HISTORY = 20;

const supportsNotifications = () =>
    typeof window !== 'undefined' &&
    'Notification' in window &&
    'serviceWorker' in navigator;

export function useFirebaseMessaging() {
    const { user } = useAuth();
    const notificationSupport = isFirebaseConfigured && supportsNotifications();
    const [notification, setNotification] = useState(null);
    const [notificationHistory, setNotificationHistory] = useState([]);
    const [registeredToken, setRegisteredToken] = useState(null);
    const [permissionStatus, setPermissionStatus] = useState(
        notificationSupport ? Notification.permission : 'unsupported'
    );
    const initializedUserRef = useRef(null);

    useEffect(() => {
        if (!user?.uid) {
            initializedUserRef.current = null;
            return;
        }
        if (!notificationSupport) {
            return;
        }
        if (initializedUserRef.current === user.uid) {
            return;
        }

        let unsubscribe = null;
        let cancelled = false;

        const initMessaging = async () => {
            try {
                const permission = Notification.permission === 'granted'
                    ? 'granted'
                    : await Notification.requestPermission();
                if (cancelled) return;

                setPermissionStatus(permission);
                if (permission !== 'granted') {
                    return;
                }

                const registration = await navigator.serviceWorker.register('/firebase-messaging-sw.js');
                const { messaging, messagingModule } = await ensureMessaging();
                const token = await messagingModule.getToken(messaging, {
                    vapidKey: VAPID_KEY,
                    serviceWorkerRegistration: registration,
                });

                if (cancelled) {
                    return;
                }

                if (token) {
                    initializedUserRef.current = user.uid;
                    setRegisteredToken(token);
                    await fetch(`${API_URL}/api/fcm/register`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            token,
                            user_id: user.uid,
                            role: user.role || 'nurse',
                        }),
                    });
                }

                unsubscribe = messagingModule.onMessage(messaging, (payload) => {
                    const nextNotification = {
                        title: payload.notification?.title || 'SAFE-Triage Alert',
                        body: payload.notification?.body || '',
                        data: payload.data || {},
                        receivedAt: new Date().toISOString(),
                    };
                    setNotification(nextNotification);
                    setNotificationHistory((current) => [nextNotification, ...current].slice(0, MAX_HISTORY));
                });
            } catch (error) {
                console.error('FCM init error:', error);
            }
        };

        initMessaging();

        return () => {
            cancelled = true;
            if (typeof unsubscribe === 'function') {
                unsubscribe();
            }
        };
    }, [notificationSupport, user?.uid, user?.role]);

    return {
        notification,
        notificationHistory,
        fcmToken: user?.uid ? registeredToken : null,
        permissionStatus,
        clearNotification: () => setNotification(null),
    };
}
