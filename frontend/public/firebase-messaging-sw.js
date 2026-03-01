importScripts('https://www.gstatic.com/firebasejs/10.12.4/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.12.4/firebase-messaging-compat.js');

firebase.initializeApp({
  apiKey: 'AIzaSyBOPkLKaj-4XzlsAHBqTgU4xulNhnpECZs',
  authDomain: 'safe-triage-ai.firebaseapp.com',
  projectId: 'safe-triage-ai',
  storageBucket: 'safe-triage-ai.firebasestorage.app',
  messagingSenderId: '459364571026',
  appId: '1:459364571026:web:6bf8ec947a6d32d08f134b',
});

const messaging = firebase.messaging();

messaging.onBackgroundMessage((payload) => {
  const notification = payload.notification || {};
  const data = payload.data || {};
  const caseId = data.patient_id || data.case_id || 'unknown';

  self.registration.showNotification(notification.title || 'SAFE-Triage Alert', {
    body: notification.body || 'Critical triage alert received.',
    icon: '/icons/alert-icon.svg',
    tag: `triage-${caseId}`,
    requireInteraction: true,
    data,
  });
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  const data = event.notification.data || {};
  const caseId = data.patient_id || data.case_id;
  const targetUrl = caseId
    ? `${self.location.origin}/dashboard?case=${encodeURIComponent(caseId)}`
    : `${self.location.origin}/dashboard`;

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windows) => {
      for (const currentWindow of windows) {
        if ('focus' in currentWindow) {
          currentWindow.navigate(targetUrl);
          return currentWindow.focus();
        }
      }
      return clients.openWindow(targetUrl);
    })
  );
});
