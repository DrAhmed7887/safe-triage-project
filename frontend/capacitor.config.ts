import type { CapacitorConfig } from '@capacitor/cli';

// SAFE-Triage Hospital Lite — Capacitor wrapper for native iOS / iPadOS.
// The web build (`npm run build` -> dist/) is bundled into the iOS app so the
// deterministic JS triage engine and offline service-worker shell ship inside
// the IPA. No network is required to run a triage from a home-screen icon.
//
// Bootstrap (Mac, once):
//   npm --prefix frontend install
//   cp frontend/.env.hospital_lite frontend/.env.local
//   npm --prefix frontend run build
//   npx --prefix frontend cap add ios
//   npx --prefix frontend cap sync ios
//   npx --prefix frontend cap open ios
//
// After code changes:
//   npm --prefix frontend run build && npx --prefix frontend cap sync ios
const config: CapacitorConfig = {
    appId: 'app.safetriage.hospitallite',
    appName: 'SAFE-Triage Lite',
    webDir: 'dist',
    // Don't ship the dev server URL inside the IPA — that would proxy the app
    // through Vite at runtime. Bundled-asset mode is what we want for a
    // hackathon / TestFlight demo.
    server: {
        // Capacitor's iosScheme defaults to `capacitor`; using `https` keeps
        // service-worker registration paths (`location.hostname` checks in
        // index.html) consistent with the deployed PWA.
        iosScheme: 'https',
        // Allow http→https mixed content for local LAN dev only. The bundled
        // build never needs this, but it stops the simulator from refusing
        // dev-server connections when you `cap run ios --livereload`.
        cleartext: false,
    },
    ios: {
        // Match the PWA brand. Status bar is set programmatically (see
        // src/main.jsx) so this is just the launch / chrome backdrop.
        backgroundColor: '#071525ff',
        // Disable bouncy rubber-band scrolling — feels more clinical-app and
        // less Safari-tab.
        scrollEnabled: true,
        // Keep WKWebView remote debugging off for TestFlight/App Store builds.
        // Flip this temporarily only when inspecting a local device from Safari.
        webContentsDebuggingEnabled: false,
    },
};

export default config;
