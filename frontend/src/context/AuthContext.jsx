/* eslint-disable react-refresh/only-export-components */
import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import {
    isFirebaseConfigured,
    signInWithGoogle,
    signOutUser,
    subscribeToAuthChanges,
} from '../lib/firebaseClient';

const AuthContext = createContext(null);

const ROLE_STORAGE_KEY = 'triageRoles';
const PENDING_ROLE_STORAGE_KEY = 'triagePendingRole';

const getRoleForUid = (uid) => {
    if (!uid) return null;
    const roles = JSON.parse(localStorage.getItem(ROLE_STORAGE_KEY) || '{}');
    return roles[uid] || null;
};

const setRoleForUid = (uid, role) => {
    if (!uid || !role) return;
    const roles = JSON.parse(localStorage.getItem(ROLE_STORAGE_KEY) || '{}');
    roles[uid] = role;
    localStorage.setItem(ROLE_STORAGE_KEY, JSON.stringify(roles));
};

const getPendingRole = () => localStorage.getItem(PENDING_ROLE_STORAGE_KEY);
const setPendingRole = (role) => {
    if (!role) return;
    localStorage.setItem(PENDING_ROLE_STORAGE_KEY, role);
};
const clearPendingRole = () => localStorage.removeItem(PENDING_ROLE_STORAGE_KEY);

const formatAuthError = (error) => {
    const code = error?.code || '';
    if (code === 'auth/popup-blocked') {
        return 'Popup was blocked. We switched to secure redirect sign-in.';
    }
    if (code === 'auth/popup-closed-by-user') {
        return 'Sign-in was cancelled before completion.';
    }
    return error?.message || 'Google sign-in failed';
};

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(isFirebaseConfigured);
    const [authError, setAuthError] = useState(null);

    useEffect(() => {
        if (!isFirebaseConfigured) {
            return;
        }

        let unsubscribe = null;
        subscribeToAuthChanges((firebaseUser) => {
            if (firebaseUser) {
                let role = getRoleForUid(firebaseUser.uid);
                if (!role) {
                    role = getPendingRole() || 'nurse';
                    setRoleForUid(firebaseUser.uid, role);
                }
                clearPendingRole();
                setUser({
                    uid: firebaseUser.uid,
                    name: firebaseUser.displayName || firebaseUser.email || 'Clinician',
                    email: firebaseUser.email || '',
                    username: firebaseUser.email || firebaseUser.uid,
                    role,
                    photoURL: firebaseUser.photoURL || null,
                });
            } else {
                setUser(null);
            }
            setLoading(false);
        })
            .then((unsub) => {
                unsubscribe = unsub;
            })
            .catch((error) => {
                setAuthError(error?.message || 'Failed to initialize Firebase');
                setLoading(false);
            });

        return () => {
            if (unsubscribe) unsubscribe();
        };
    }, []);

    const loginWithGoogle = useCallback(async (role, rememberMe = true) => {
        setAuthError(null);
        if (!isFirebaseConfigured) {
            const message = 'Firebase configuration missing.';
            setAuthError(message);
            return { success: false, message };
        }
        try {
            setPendingRole(role || 'nurse');
            const result = await signInWithGoogle({ rememberMe });
            if (result?.mode === 'redirect') {
                return { success: true, redirected: true };
            }
            const firebaseUser = result.user;
            const assignedRole = role || getRoleForUid(firebaseUser.uid) || 'nurse';
            setRoleForUid(firebaseUser.uid, assignedRole);
            clearPendingRole();
            setUser({
                uid: firebaseUser.uid,
                name: firebaseUser.displayName || firebaseUser.email || 'Clinician',
                email: firebaseUser.email || '',
                username: firebaseUser.email || firebaseUser.uid,
                role: assignedRole,
                photoURL: firebaseUser.photoURL || null,
            });
            return { success: true };
        } catch (error) {
            const message = formatAuthError(error);
            setAuthError(message);
            return { success: false, message };
        }
    }, []);

    const updateRole = useCallback((role) => {
        if (!role) return;
        setUser((prev) => {
            if (!prev?.uid) return prev;
            setRoleForUid(prev.uid, role);
            return { ...prev, role };
        });
    }, []);

    const logout = useCallback(async () => {
        await signOutUser();
        setUser(null);
    }, []);

    const value = useMemo(
        () => ({
            user,
            loginWithGoogle,
            updateRole,
            logout,
            loading,
            authError,
            isFirebaseConfigured,
        }),
        [user, loginWithGoogle, updateRole, logout, loading, authError]
    );

    return (
        <AuthContext.Provider value={value}>
            {!loading && children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => useContext(AuthContext);
