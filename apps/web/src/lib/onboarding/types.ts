/**
 * Tour Types for Onboarding System
 *
 * This module defines the types used for onboarding tours throughout the application.
 * Tours guide users through features step by step.
 */

/**
 * Placement options for tooltip positioning relative to the target element
 */
export type TourPlacement = "top" | "bottom" | "left" | "right";

/**
 * A single step in an onboarding tour
 */
export interface TourStep {
  /** Unique identifier for this step */
  id: string;
  /** Title displayed in the tooltip header */
  title: string;
  /** Content/description of the step */
  content: string;
  /** CSS selector for the target element to highlight */
  target: string;
  /** Preferred placement of the tooltip relative to the target */
  placement?: TourPlacement;
  /** Whether this step can be skipped (default: true) */
  skipable?: boolean;
}

/**
 * Configuration for a complete onboarding tour
 */
export interface TourConfig {
  /** Unique identifier for this tour */
  id: string;
  /** Human-readable name of the tour */
  name: string;
  /** Ordered list of steps in the tour */
  steps: TourStep[];
  /** LocalStorage key to track tour completion status */
  storageKey: string;
}

/**
 * Status of a tour for a user
 */
export type TourStatus = "not_started" | "in_progress" | "completed" | "skipped";

/**
 * Props for the Tour component
 */
export interface TourProps {
  /** Tour configuration */
  config: TourConfig;
  /** Callback when tour is completed */
  onComplete: () => void;
  /** Callback when tour is skipped */
  onSkip: () => void;
  /** Optional initial step index (default: 0) */
  initialStepIndex?: number;
}

/**
 * Return type for useShouldShowTour hook
 */
export interface UseShouldShowTourResult {
  /** Whether the tour should be shown */
  shouldShow: boolean;
  /** Current status of the tour */
  status: TourStatus;
  /** Mark tour as completed */
  markCompleted: () => void;
  /** Mark tour as skipped */
  markSkipped: () => void;
  /** Reset tour status (show again) */
  reset: () => void;
}
