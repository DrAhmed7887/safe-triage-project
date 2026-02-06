import React from 'react';

class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true };
    }

    componentDidCatch(error, errorInfo) {
        console.error('Dashboard error:', error, errorInfo);
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="p-6 bg-red-50 border border-red-200 rounded-lg text-center m-4">
                    <h2 className="text-red-600 text-xl font-bold mb-2">Something went wrong</h2>
                    <p className="text-red-500 mb-4" dir="rtl">حدث خطأ غير متوقع</p>
                    <button
                        onClick={() => window.location.reload()}
                        className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
                    >
                        Reload / إعادة التحميل
                    </button>
                </div>
            );
        }
        return this.props.children;
    }
}

export default ErrorBoundary;
