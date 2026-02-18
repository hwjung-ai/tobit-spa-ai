"use client";

import React, { useCallback } from "react";
import { Tour, useTour } from "@/components/onboarding/Tour";
import { CEP_TOUR_CONFIG, CEP_QUICK_TOUR_CONFIG } from "./cepTourConfig";
import { cn } from "@/lib/utils";

interface CepTourLauncherProps {
  /** Show the full tour button text */
  fullTourText?: string;
  /** Show the quick tour button text */
  quickTourText?: string;
  /** Additional CSS classes for the container */
  className?: string;
  /** Callback when tour starts */
  onTourStart?: () => void;
  /** Callback when tour completes */
  onTourComplete?: () => void;
  /** Callback when tour is skipped */
  onTourSkip?: () => void;
}

/**
 * CEP Tour Launcher Component
 *
 * Provides buttons to start the CEP Builder onboarding tour.
 * Automatically shows the tour for first-time users.
 */
export function CepTourLauncher({
  fullTourText = "Start Full Tour",
  quickTourText = "Quick Tour",
  className,
  onTourStart,
  onTourComplete,
  onTourSkip,
}: CepTourLauncherProps) {
  const {
    isActive: isFullTourActive,
    start: startFullTour,
    complete: completeFullTour,
    skip: skipFullTour,
  } = useTour(CEP_TOUR_CONFIG);

  const {
    isActive: isQuickTourActive,
    start: startQuickTour,
    complete: completeQuickTour,
    skip: skipQuickTour,
  } = useTour(CEP_QUICK_TOUR_CONFIG);

  const handleFullTourStart = useCallback(() => {
    startFullTour();
    onTourStart?.();
  }, [startFullTour, onTourStart]);

  const handleQuickTourStart = useCallback(() => {
    startQuickTour();
    onTourStart?.();
  }, [startQuickTour, onTourStart]);

  const handleFullTourComplete = useCallback(() => {
    completeFullTour();
    onTourComplete?.();
  }, [completeFullTour, onTourComplete]);

  const handleFullTourSkip = useCallback(() => {
    skipFullTour();
    onTourSkip?.();
  }, [skipFullTour, onTourSkip]);

  const handleQuickTourComplete = useCallback(() => {
    completeQuickTour();
    onTourComplete?.();
  }, [completeQuickTour, onTourComplete]);

  const handleQuickTourSkip = useCallback(() => {
    skipQuickTour();
    onTourSkip?.();
  }, [skipQuickTour, onTourSkip]);

  return (
    <div className={cn("flex items-center gap-2", className)}>
      {/* Full Tour Button */}
      <button
        onClick={handleFullTourStart}
        className={cn(
          "inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5",
          "text-xs font-medium text-muted-foreground",
          "transition-colors hover:border-primary hover:text-primary",
          "focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
        )}
        type="button"
        aria-label="Start full CEP Builder tour"
      >
        <svg
          className="h-3.5 w-3.5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        {fullTourText}
      </button>

      {/* Quick Tour Button */}
      <button
        onClick={handleQuickTourStart}
        className={cn(
          "inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5",
          "text-xs font-medium text-muted-foreground",
          "transition-colors hover:text-foreground",
          "focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
        )}
        type="button"
        aria-label="Start quick CEP Builder tour"
      >
        <svg
          className="h-3.5 w-3.5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M13 10V3L4 14h7v7l9-11h-7z"
          />
        </svg>
        {quickTourText}
      </button>

      {/* Render active tour */}
      {isFullTourActive && (
        <Tour
          config={CEP_TOUR_CONFIG}
          onComplete={handleFullTourComplete}
          onSkip={handleFullTourSkip}
        />
      )}

      {isQuickTourActive && (
        <Tour
          config={CEP_QUICK_TOUR_CONFIG}
          onComplete={handleQuickTourComplete}
          onSkip={handleQuickTourSkip}
        />
      )}
    </div>
  );
}

/**
 * Minimal tour launcher that only shows a help icon
 * Use this for compact layouts
 */
export function CepTourIconButton({
  className,
  onTourStart,
  onTourComplete,
  onTourSkip,
}: Omit<CepTourLauncherProps, "fullTourText" | "quickTourText">) {
  const {
    isActive,
    start,
    complete,
    skip,
  } = useTour(CEP_TOUR_CONFIG);

  const handleStart = useCallback(() => {
    start();
    onTourStart?.();
  }, [start, onTourStart]);

  const handleComplete = useCallback(() => {
    complete();
    onTourComplete?.();
  }, [complete, onTourComplete]);

  const handleSkip = useCallback(() => {
    skip();
    onTourSkip?.();
  }, [skip, onTourSkip]);

  return (
    <>
      <button
        onClick={handleStart}
        className={cn(
          "rounded-full p-1.5 text-muted-foreground",
          "transition-colors hover:bg-surface-base hover:text-foreground",
          "focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2",
          className
        )}
        type="button"
        aria-label="Start CEP Builder tour"
        title="Start Tour"
      >
        <svg
          className="h-4 w-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      </button>

      {isActive && (
        <Tour
          config={CEP_TOUR_CONFIG}
          onComplete={handleComplete}
          onSkip={handleSkip}
        />
      )}
    </>
  );
}

export default CepTourLauncher;
