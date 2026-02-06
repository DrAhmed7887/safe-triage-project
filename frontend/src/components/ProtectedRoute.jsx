import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function ProtectedRoute() {
    const { user, loading } = useAuth();

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center text-slate-500">
                Loading...
            </div>
        );
    }

    if (!user) {
        return <Navigate to="/signin" replace />;
    }

    return <Outlet />;
}
