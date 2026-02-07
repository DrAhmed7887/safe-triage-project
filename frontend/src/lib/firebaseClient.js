const firebaseConfig = {
    apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
    authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
    projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
    appId: import.meta.env.VITE_FIREBASE_APP_ID,
    messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
    storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
    measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID,
};

const requiredKeys = [
    'apiKey',
    'authDomain',
    'projectId',
    'appId',
    'messagingSenderId',
];

const isValidValue = (value) =>
    Boolean(value) && value !== 'REPLACE_ME' && !value.startsWith('YOUR_FIREBASE_');

const isFirebaseConfigured = requiredKeys.every((key) => isValidValue(firebaseConfig[key]));

const FIREBASE_APP_URL = 'https://www.gstatic.com/firebasejs/10.12.4/firebase-app.js';
const FIREBASE_AUTH_URL = 'https://www.gstatic.com/firebasejs/10.12.4/firebase-auth.js';

let firebaseCache = null;

const ensureFirebase = async () => {
    if (firebaseCache) return firebaseCache;
    if (!isFirebaseConfigured) {
        throw new Error('Firebase is not configured.');
    }
    const appModule = await import(/* @vite-ignore */ FIREBASE_APP_URL);
    const authModule = await import(/* @vite-ignore */ FIREBASE_AUTH_URL);
    const app = appModule.getApps().length
        ? appModule.getApps()[0]
        : appModule.initializeApp(firebaseConfig);
    const auth = authModule.getAuth(app);
    const googleProvider = new authModule.GoogleAuthProvider();
    firebaseCache = { auth, authModule, googleProvider };
    return firebaseCache;
};

const signInWithGoogle = async ({ rememberMe = true } = {}) => {
    const { auth, authModule, googleProvider } = await ensureFirebase();
    const persistence = rememberMe
        ? authModule.browserLocalPersistence
        : authModule.browserSessionPersistence;
    await authModule.setPersistence(auth, persistence);
    try {
        const popupResult = await authModule.signInWithPopup(auth, googleProvider);
        return { mode: 'popup', user: popupResult.user };
    } catch (error) {
        const code = error?.code || '';
        if (code === 'auth/popup-blocked' || code === 'auth/cancelled-popup-request') {
            await authModule.signInWithRedirect(auth, googleProvider);
            return { mode: 'redirect', redirected: true };
        }
        throw error;
    }
};

const signOutUser = async () => {
    const { auth, authModule } = await ensureFirebase();
    await authModule.signOut(auth);
};

const subscribeToAuthChanges = async (callback) => {
    const { auth, authModule } = await ensureFirebase();
    return authModule.onAuthStateChanged(auth, callback);
};

const getIdToken = async () => {
    const { auth } = await ensureFirebase();
    if (!auth.currentUser) return null;
    return auth.currentUser.getIdToken();
};

export { isFirebaseConfigured, signInWithGoogle, signOutUser, subscribeToAuthChanges, getIdToken };
