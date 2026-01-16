"use client";

import { useEffect } from "react";

interface ToastProps {
    message: string;
    type?: "success" | "error" | "warning";
    onClose: () => void;
    duration?: number;
}

export default function Toast({ message, type = "success", onClose, duration = 3000 }: ToastProps) {
    useEffect(() => {
        const timer = setTimeout(() => {
            onClose();
        }, duration);

        return () => clearTimeout(timer);
    }, [duration, onClose]);

    const bgColor = {
        success: "bg-green-950/90 border-green-800",
        error: "bg-red-950/90 border-red-800",
        warning: "bg-yellow-950/90 border-yellow-800",
    }[type];

    const textColor = {
        success: "text-green-200",
        error: "text-red-200",
        warning: "text-yellow-200",
    }[type];

    const icon = {
        success: (
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
        ),
        error: (
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
        ),
        warning: (
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
        ),
    }[type];

    return (
        <div className="fixed top-4 right-4 z-50 animate-slide-in">
            <div className={`rounded-lg border ${bgColor} p-4 shadow-lg max-w-md`}>
                <div className="flex items-center gap-3">
                    <div className={textColor}>{icon}</div>
                    <p className={`text-sm ${textColor}`}>{message}</p>
                    <button
                        onClick={onClose}
                        className={`ml-auto ${textColor} hover:opacity-70 transition-opacity`}
                    >
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>
            </div>
        </div>
    );
}
