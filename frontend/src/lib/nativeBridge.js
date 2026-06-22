/**
 * nativeBridge.js — runtime detection + side-effects for when the SAFE-Triage
 * Hospital Lite frontend is loaded inside the Capacitor iOS wrapper instead of
 * a plain mobile Safari tab.
 *
 * Capacitor is loaded as a normal npm dep so `import` works in both worlds.
 * `Capacitor.isNativePlatform()` returns `true` only inside the iOS / Android
 * WebView, so all the native-only configuration is gated behind that check.
 *
 * Stays a no-op in the browser-only PWA path, so the regular web demo is
 * unaffected.
 */

import { Capacitor } from '@capacitor/core';

export const IS_NATIVE = Capacitor.isNativePlatform();
export const NATIVE_PLATFORM = Capacitor.getPlatform();

export async function initNativeShell() {
    if (!IS_NATIVE) return;

    // Status bar — match the teal brand. Lazy-imported so the web bundle
    // doesn't drag in the plugin's native shim when running in Safari.
    try {
        const { StatusBar, Style } = await import('@capacitor/status-bar');
        // Light-content text on the teal background reads cleanly.
        await StatusBar.setStyle({ style: Style.Light });
        if (NATIVE_PLATFORM === 'ios') {
            await StatusBar.setBackgroundColor({ color: '#0d9488' });
        }
        await StatusBar.setOverlaysWebView({ overlay: false });
    } catch (err) {
        console.warn('StatusBar init failed:', err);
    }

    // Soft Android back-button handling lives here too if we ever wrap Android.
    try {
        const { App } = await import('@capacitor/app');
        App.addListener('appStateChange', ({ isActive }) => {
            if (isActive) document.dispatchEvent(new CustomEvent('safetriage:appActive'));
        });
    } catch (err) {
        console.warn('App listener init failed:', err);
    }
}
