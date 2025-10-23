import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
    children: ReactNode;
    fallbackTitle?: string;
    onReset?: () => void;
}

interface State {
    hasError: boolean;
    error: Error | null;
    errorInfo: ErrorInfo | null;
}

/**
 * Error Boundary component that catches React errors and displays a fallback UI.
 * Prevents the entire app from crashing when a component error occurs.
 */
export class ErrorBoundary extends Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = {
            hasError: false,
            error: null,
            errorInfo: null,
        };
    }

    static getDerivedStateFromError(error: Error): Partial<State> {
        // Update state so the next render will show the fallback UI
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
        // Log error details for debugging
        console.error('Error Boundary caught an error:', error, errorInfo);
        this.setState({
            error,
            errorInfo,
        });
    }

    handleReset = (): void => {
        this.setState({
            hasError: false,
            error: null,
            errorInfo: null,
        });

        // Call optional onReset callback
        if (this.props.onReset) {
            this.props.onReset();
        }
    };

    render(): ReactNode {
        if (this.state.hasError) {
            const { fallbackTitle = 'Something went wrong' } = this.props;

            return (
                <div className="bg-red-900/20 border border-red-700 rounded-lg p-6">
                    <div className="flex items-start gap-3">
                        <AlertTriangle className="w-6 h-6 text-red-500 flex-shrink-0 mt-1" />
                        <div className="flex-1">
                            <h3 className="text-lg font-semibold text-red-400 mb-2">
                                {fallbackTitle}
                            </h3>
                            <p className="text-sm text-gray-300 mb-4">
                                An error occurred while rendering this section.
                                The rest of the app should continue to work normally.
                            </p>

                            {/* Show error details (useful for debugging) */}
                            {this.state.error && (
                                <details className="mb-4">
                                    <summary className="text-sm text-gray-400 cursor-pointer hover:text-gray-300">
                                        Technical Details
                                    </summary>
                                    <div className="mt-2 p-3 bg-gray-900 rounded text-xs font-mono overflow-x-auto">
                                        <div className="text-red-400 mb-2">
                                            {this.state.error.toString()}
                                        </div>
                                        {this.state.errorInfo && (
                                            <div className="text-gray-500">
                                                {this.state.errorInfo.componentStack}
                                            </div>
                                        )}
                                    </div>
                                </details>
                            )}

                            <button
                                onClick={this.handleReset}
                                className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 rounded text-sm transition-colors"
                            >
                                <RefreshCw className="w-4 h-4" />
                                Try Again
                            </button>
                        </div>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}
