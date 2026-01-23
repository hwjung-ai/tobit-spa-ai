"use client";

import { useEffect, useState } from "react";

interface ToastProps {
    message: string;
    type?: "success" | "error" | "warning" | "info";
    onDismiss?: () => void;
    duration?: number;
}

export default function Toast({ message, type = "success", onDismiss, duration = 3000 }: ToastProps) {
    const [isVisible, setIsVisible] = useState(false);

    useEffect(() => {
        if (!message) {
            setIsVisible(false);
            return;
        }

        setIsVisible(true);
        const timer = setTimeout(() => {
            setIsVisible(false);
            onDismiss?.();
        }, duration);

        return () => clearTimeout(timer);
    }, [message, duration, onDismiss]);

    const bgColor = {
        success: "bg-green-950/90 border-green-800",
        error: "bg-red-950/90 border-red-800",
        warning: "bg-yellow-950/90 border-yellow-800",
        info: "bg-blue-950/90 border-blue-800",
    }[type];

    const textColor = {
        success: "text-green-200",
        error: "text-red-200",
        warning: "text-yellow-200",
        info: "text-blue-200",
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
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333-.192 3 1.732 3z" />
            </svg>
        ),
        info: (
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 16h.01" />
            </svg>
        ),
    }[type];

    if (!isVisible) {
        return null;
    }

    const handleClose = () => {
        setIsVisible(false);
        onDismiss?.();
    };

    return (
        <div className="fixed bottom-6 right-6 z-50 flex w-full max-w-xs flex-col gap-3">
            <div className={`animate-slide-in rounded-2xl border ${bgColor} px-5 py-4 shadow-2xl`}>
                <div className="flex items-start gap-3">
                    <div className={`${textColor} mt-1`}>{icon}</div>
                    <p className={`text-sm font-medium leading-snug ${textColor}`}>{message}</p>
                    <button
                        onClick={handleClose}
                        className={`ml-auto ${textColor} rounded-full p-1 transition-opacity hover:opacity-70`}
                        aria-label="Close toast"
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
