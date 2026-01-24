"use client";

interface ValidationAlertProps {
    errors: string[];
    onClose?: () => void;
    isWarning?: boolean;
}

export default function ValidationAlert({ errors, onClose }: ValidationAlertProps) {
    if (errors.length === 0) return null;

    return (
        <div className="mb-4 rounded-lg border border-red-800 bg-red-950/50 p-4">
            <div className="flex items-start justify-between">
                <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                        <svg
                            className="h-5 w-5 text-red-400"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                            />
                        </svg>
                        <h3 className="text-sm font-medium text-red-200">Validation Errors</h3>
                    </div>
                    <ul className="list-disc list-inside space-y-1 text-sm text-red-300">
                        {errors.map((error, index) => (
                            <li key={index}>{error}</li>
                        ))}
                    </ul>
                </div>
                {onClose && (
                    <button
                        onClick={onClose}
                        className="ml-4 text-red-400 hover:text-red-300 transition-colors"
                        aria-label="Close"
                    >
                        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                )}
            </div>
        </div>
    );
}
