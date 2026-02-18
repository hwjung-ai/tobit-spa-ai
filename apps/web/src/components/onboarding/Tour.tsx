"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import { createPortal } from "react-dom";
import { cn } from "@/lib/utils";
import type {
  TourConfig,
  TourProps,
  TourStatus,
  UseShouldShowTourResult,
} from "@/lib/onboarding/types";

/**
 * Tour Component
 *
 * Renders an interactive onboarding tour with:
 * - Semi-transparent overlay
 * - Highlighted target element
 * - Position-aware tooltip
 * - Navigation controls (Previous, Next, Skip)
 */
export function Tour({
  config,
  onComplete,
  onSkip,
  initialStepIndex = 0,
}: TourProps) {
  const [currentStepIndex, setCurrentStepIndex] = useState(initialStepIndex);
  const [targetRect, setTargetRect] = useState<DOMRect | null>(null);
  const [isVisible, setIsVisible] = useState(true);
  const [isMounted, setIsMounted] = useState(false);

  const currentStep = config.steps[currentStepIndex];
  const totalSteps = config.steps.length;

  // Handle client-side mounting
  useEffect(() => {
    setIsMounted(true);
  }, []);

  /**
   * Update the position of the tooltip relative to the target element
   */
  const updatePosition = useCallback(() => {
    if (!currentStep) return;

    const target = document.querySelector(currentStep.target);
    if (target) {
      const rect = target.getBoundingClientRect();
      setTargetRect(rect);

      // Scroll target into view if not visible
      const isInViewport =
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= window.innerHeight &&
        rect.right <= window.innerWidth;

      if (!isInViewport) {
        target.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    } else {
      console.warn(`Tour target not found: ${currentStep.target}`);
    }
  }, [currentStep]);

  // Update position on step change, resize, and scroll
  useEffect(() => {
    updatePosition();

    const handleResize = () => updatePosition();
    const handleScroll = () => updatePosition();

    window.addEventListener("resize", handleResize);
    window.addEventListener("scroll", handleScroll, true);

    // Re-position after a short delay to account for DOM updates
    const timeoutId = setTimeout(updatePosition, 100);

    return () => {
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("scroll", handleScroll, true);
      clearTimeout(timeoutId);
    };
  }, [updatePosition]);

  const handleNext = useCallback(() => {
    if (currentStepIndex < totalSteps - 1) {
      setCurrentStepIndex((prev) => prev + 1);
    } else {
      localStorage.setItem(config.storageKey, "completed");
      onComplete();
    }
  }, [currentStepIndex, totalSteps, config.storageKey, onComplete]);

  const handlePrev = useCallback(() => {
    if (currentStepIndex > 0) {
      setCurrentStepIndex((prev) => prev - 1);
    }
  }, [currentStepIndex]);

  const handleSkip = useCallback(() => {
    localStorage.setItem(config.storageKey, "skipped");
    setIsVisible(false);
    onSkip();
  }, [config.storageKey, onSkip]);

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      switch (event.key) {
        case "ArrowRight":
        case "Enter":
          handleNext();
          break;
        case "ArrowLeft":
          handlePrev();
          break;
        case "Escape":
          handleSkip();
          break;
      }
    },
    [handleNext, handlePrev, handleSkip]
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  // Calculate tooltip position based on placement
  const tooltipPosition = useMemo((): React.CSSProperties => {
    if (!targetRect) return {};

    const placement = currentStep?.placement || "bottom";
    const spacing = 12;

    switch (placement) {
      case "top":
        return {
          top: targetRect.top - spacing,
          left: targetRect.left + targetRect.width / 2,
          transform: "translate(-50%, -100%)",
        };
      case "bottom":
        return {
          top: targetRect.bottom + spacing,
          left: targetRect.left + targetRect.width / 2,
          transform: "translateX(-50%)",
        };
      case "left":
        return {
          top: targetRect.top + targetRect.height / 2,
          left: targetRect.left - spacing,
          transform: "translate(-100%, -50%)",
        };
      case "right":
        return {
          top: targetRect.top + targetRect.height / 2,
          left: targetRect.right + spacing,
          transform: "translateY(-50%)",
        };
      default:
        return {};
    }
  }, [targetRect, currentStep?.placement]);

  // Don't render if not mounted or not visible
  if (!isMounted || !isVisible || !currentStep || !targetRect) return null;

  const isFirstStep = currentStepIndex === 0;
  const isLastStep = currentStepIndex === totalSteps - 1;
  const canSkip = currentStep.skipable !== false;

  return createPortal(
    <>
      {/* Semi-transparent overlay */}
      <div
        className="fixed inset-0 z-[9998] bg-black/50 backdrop-blur-[1px] transition-opacity"
        onClick={canSkip ? handleSkip : undefined}
        aria-hidden="true"
      />

      {/* Highlight cutout around target element */}
      <div
        className="fixed z-[9999] pointer-events-none rounded-md transition-all duration-200"
        style={{
          top: targetRect.top - 4,
          left: targetRect.left - 4,
          width: targetRect.width + 8,
          height: targetRect.height + 8,
          boxShadow: "0 0 0 4px rgba(59, 130, 246, 0.6), 0 0 0 9999px rgba(0, 0, 0, 0.5)",
        }}
      />

      {/* Tooltip */}
      <div
        className={cn(
          "fixed z-[10000] w-72 rounded-lg border border-border bg-surface-elevated p-4 shadow-xl",
          "animate-in fade-in-0 zoom-in-95 duration-200"
        )}
        style={tooltipPosition}
        role="dialog"
        aria-labelledby="tour-title"
        aria-describedby="tour-content"
      >
        {/* Header: Step counter and Skip button */}
        <div className="mb-2 flex items-center justify-between">
          <span className="text-xs font-medium text-muted-foreground">
            Step {currentStepIndex + 1} of {totalSteps}
          </span>
          {canSkip && (
            <button
              onClick={handleSkip}
              className="text-xs text-muted-foreground hover:text-foreground transition-colors"
              type="button"
            >
              Skip tour
            </button>
          )}
        </div>

        {/* Title */}
        <h3
          id="tour-title"
          className="mb-1 text-base font-semibold text-foreground"
        >
          {currentStep.title}
        </h3>

        {/* Content */}
        <p
          id="tour-content"
          className="mb-4 text-sm leading-relaxed text-muted-foreground"
        >
          {currentStep.content}
        </p>

        {/* Progress dots */}
        <div className="mb-3 flex items-center justify-center gap-1.5">
          {config.steps.map((_, index) => (
            <div
              key={index}
              className={cn(
                "h-1.5 rounded-full transition-all duration-200",
                index === currentStepIndex
                  ? "w-4 bg-primary"
                  : index < currentStepIndex
                    ? "w-1.5 bg-primary/50"
                    : "w-1.5 bg-border"
              )}
            />
          ))}
        </div>

        {/* Navigation buttons */}
        <div className="flex items-center justify-between gap-2">
          <button
            onClick={handlePrev}
            disabled={isFirstStep}
            className={cn(
              "flex-1 rounded-md border border-border px-3 py-1.5 text-xs font-medium",
              "transition-colors hover:bg-surface-base",
              "disabled:cursor-not-allowed disabled:opacity-40"
            )}
            type="button"
          >
            Previous
          </button>
          <button
            onClick={handleNext}
            className={cn(
              "flex-1 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground",
              "transition-colors hover:bg-primary/90"
            )}
            type="button"
          >
            {isLastStep ? "Finish" : "Next"}
          </button>
        </div>
      </div>
    </>,
    document.body
  );
}

/**
 * Hook to check if a tour should be shown based on localStorage status
 *
 * @param storageKey - The localStorage key for tracking tour status
 * @returns Object with shouldShow boolean and control functions
 */
export function useShouldShowTour(storageKey: string): UseShouldShowTourResult {
  const [status, setStatus] = useState<TourStatus>("not_started");

  useEffect(() => {
    const storedStatus = localStorage.getItem(storageKey) as TourStatus | null;
    if (storedStatus === "completed" || storedStatus === "skipped") {
      setStatus(storedStatus);
    } else {
      setStatus("not_started");
    }
  }, [storageKey]);

  const markCompleted = useCallback(() => {
    localStorage.setItem(storageKey, "completed");
    setStatus("completed");
  }, [storageKey]);

  const markSkipped = useCallback(() => {
    localStorage.setItem(storageKey, "skipped");
    setStatus("skipped");
  }, [storageKey]);

  const reset = useCallback(() => {
    localStorage.removeItem(storageKey);
    setStatus("not_started");
  }, [storageKey]);

  return {
    shouldShow: status === "not_started",
    status,
    markCompleted,
    markSkipped,
    reset,
  };
}

/**
 * Hook to manage tour state for a specific tour config
 *
 * @param config - Tour configuration
 * @returns Object with tour state and control functions
 */
export function useTour(config: TourConfig) {
  const { shouldShow, status, markCompleted, markSkipped, reset } =
    useShouldShowTour(config.storageKey);
  const [isActive, setIsActive] = useState(false);

  useEffect(() => {
    if (shouldShow) {
      // Small delay to allow page to render
      const timeoutId = setTimeout(() => setIsActive(true), 500);
      return () => clearTimeout(timeoutId);
    }
  }, [shouldShow]);

  const start = useCallback(() => {
    setIsActive(true);
  }, []);

  const stop = useCallback(() => {
    setIsActive(false);
  }, []);

  const complete = useCallback(() => {
    markCompleted();
    setIsActive(false);
  }, [markCompleted]);

  const skip = useCallback(() => {
    markSkipped();
    setIsActive(false);
  }, [markSkipped]);

  const restart = useCallback(() => {
    reset();
    setIsActive(true);
  }, [reset]);

  return {
    isActive,
    status,
    shouldShow,
    start,
    stop,
    complete,
    skip,
    restart,
    TourComponent: isActive ? (
      <Tour config={config} onComplete={complete} onSkip={skip} />
    ) : null,
  };
}

export default Tour;
