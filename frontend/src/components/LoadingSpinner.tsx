import { Loader2 } from 'lucide-react';

interface Props {
    size?: 'sm' | 'md' | 'lg';
    message?: string;
    fullScreen?: boolean;
}

/**
 * Centralized loading spinner component.
 * Can be used inline or as a full-screen overlay.
 */
export const LoadingSpinner = ({ size = 'md', message, fullScreen = false }: Props) => {
    const sizeClasses = {
        sm: 'w-4 h-4',
        md: 'w-8 h-8',
        lg: 'w-12 h-12',
    };

    const spinner = (
        <div className="flex flex-col items-center justify-center gap-3">
            <Loader2 className={`${sizeClasses[size]} animate-spin text-blue-500`} />
            {message && (
                <p className="text-sm text-gray-400">{message}</p>
            )}
        </div>
    );

    if (fullScreen) {
        return (
            <div className="fixed inset-0 bg-gray-900/80 backdrop-blur-sm flex items-center justify-center z-50">
                {spinner}
            </div>
        );
    }

    return spinner;
};
