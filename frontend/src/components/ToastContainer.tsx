/**
 * Toast notification container component.
 */

import { useToast } from '../hooks/useToast';
import { X, CheckCircle, XCircle, Info, AlertTriangle } from 'lucide-react';

export const ToastContainer = () => {
    const { toasts, removeToast } = useToast();

    const getToastStyles = (type: string) => {
        switch (type) {
            case 'success':
                return 'bg-green-600 border-green-500';
            case 'error':
                return 'bg-red-600 border-red-500';
            case 'warning':
                return 'bg-yellow-600 border-yellow-500';
            case 'info':
            default:
                return 'bg-blue-600 border-blue-500';
        }
    };

    const getToastIcon = (type: string) => {
        switch (type) {
            case 'success':
                return <CheckCircle className="w-5 h-5" />;
            case 'error':
                return <XCircle className="w-5 h-5" />;
            case 'warning':
                return <AlertTriangle className="w-5 h-5" />;
            case 'info':
            default:
                return <Info className="w-5 h-5" />;
        }
    };

    if (toasts.length === 0) return null;

    return (
        <div className="fixed top-4 right-4 z-50 space-y-2 max-w-md">
            {toasts.map((toast) => (
                <div
                    key={toast.id}
                    className={`${getToastStyles(toast.type)} border rounded-lg shadow-lg p-4
                               flex items-start gap-3 animate-slide-in-right`}
                >
                    <div className="flex-shrink-0 text-white mt-0.5">
                        {getToastIcon(toast.type)}
                    </div>
                    <p className="flex-1 text-white text-sm font-medium">
                        {toast.message}
                    </p>
                    <button
                        onClick={() => removeToast(toast.id)}
                        className="flex-shrink-0 text-white/80 hover:text-white transition-colors"
                        aria-label="Close notification"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </div>
            ))}
        </div>
    );
};
