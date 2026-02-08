"""
Statistical anomaly detection for CEP Engine.

Provides three detection methods:
- Z-Score: Detects values that deviate significantly from the mean
- IQR (Interquartile Range): Robust outlier detection using quartiles
- EMA (Exponential Moving Average): Adaptive detection for streaming data
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, Literal


@dataclass
class AnomalyResult:
    """Result of an anomaly detection check."""

    is_anomaly: bool
    score: float
    method: str
    details: Dict[str, Any] = field(default_factory=dict)


AnomalyMethod = Literal["zscore", "iqr", "ema"]


class ZScoreDetector:
    """
    Z-Score based anomaly detection.

    Detects values that are more than `threshold` standard deviations
    away from the rolling mean.
    """

    def __init__(self, threshold: float = 3.0):
        self.threshold = threshold

    def detect(self, values: list[float], current: float) -> AnomalyResult:
        if len(values) < 2:
            return AnomalyResult(
                is_anomaly=False,
                score=0.0,
                method="zscore",
                details={"reason": "insufficient_data", "min_required": 2},
            )

        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        std = math.sqrt(variance) if variance > 0 else 0.0

        if std == 0:
            z_score = 0.0
        else:
            z_score = abs(current - mean) / std

        return AnomalyResult(
            is_anomaly=z_score > self.threshold,
            score=z_score,
            method="zscore",
            details={
                "mean": round(mean, 4),
                "std": round(std, 4),
                "threshold": self.threshold,
                "z_score": round(z_score, 4),
                "current_value": current,
                "sample_size": len(values),
            },
        )


class IQRDetector:
    """
    Interquartile Range based anomaly detection.

    Detects values outside [Q1 - multiplier*IQR, Q3 + multiplier*IQR].
    More robust to outliers than Z-Score.
    """

    def __init__(self, multiplier: float = 1.5):
        self.multiplier = multiplier

    def _percentile(self, sorted_values: list[float], p: float) -> float:
        index = (p / 100.0) * (len(sorted_values) - 1)
        lower = int(index)
        upper = min(lower + 1, len(sorted_values) - 1)
        weight = index - lower
        return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight

    def detect(self, values: list[float], current: float) -> AnomalyResult:
        if len(values) < 4:
            return AnomalyResult(
                is_anomaly=False,
                score=0.0,
                method="iqr",
                details={"reason": "insufficient_data", "min_required": 4},
            )

        sorted_vals = sorted(values)
        q1 = self._percentile(sorted_vals, 25)
        q3 = self._percentile(sorted_vals, 75)
        iqr = q3 - q1

        lower_bound = q1 - self.multiplier * iqr
        upper_bound = q3 + self.multiplier * iqr

        is_anomaly = current < lower_bound or current > upper_bound

        # Score: how far outside the bounds (0 if within bounds)
        if current < lower_bound:
            score = (lower_bound - current) / max(iqr, 1e-10)
        elif current > upper_bound:
            score = (current - upper_bound) / max(iqr, 1e-10)
        else:
            score = 0.0

        return AnomalyResult(
            is_anomaly=is_anomaly,
            score=round(score, 4),
            method="iqr",
            details={
                "q1": round(q1, 4),
                "q3": round(q3, 4),
                "iqr": round(iqr, 4),
                "lower_bound": round(lower_bound, 4),
                "upper_bound": round(upper_bound, 4),
                "multiplier": self.multiplier,
                "current_value": current,
                "sample_size": len(values),
            },
        )


class EMADetector:
    """
    Exponential Moving Average based anomaly detection.

    Uses EMA to track a smoothed trend and detects when the current
    value deviates beyond `threshold` * EMA-based standard deviation.
    Good for streaming/time-series data with trends.
    """

    def __init__(self, alpha: float = 0.3, threshold: float = 3.0):
        self.alpha = max(0.01, min(1.0, alpha))
        self.threshold = threshold

    def detect(self, values: list[float], current: float) -> AnomalyResult:
        if len(values) < 2:
            return AnomalyResult(
                is_anomaly=False,
                score=0.0,
                method="ema",
                details={"reason": "insufficient_data", "min_required": 2},
            )

        # Compute EMA and EMA of squared deviations
        ema = values[0]
        ema_var = 0.0

        for v in values[1:]:
            ema = self.alpha * v + (1 - self.alpha) * ema
            deviation = v - ema
            ema_var = self.alpha * (deviation ** 2) + (1 - self.alpha) * ema_var

        ema_std = math.sqrt(ema_var) if ema_var > 0 else 0.0
        deviation = abs(current - ema)
        score = deviation / max(ema_std, 1e-10)

        return AnomalyResult(
            is_anomaly=score > self.threshold,
            score=round(score, 4),
            method="ema",
            details={
                "ema": round(ema, 4),
                "ema_std": round(ema_std, 4),
                "deviation": round(deviation, 4),
                "alpha": self.alpha,
                "threshold": self.threshold,
                "current_value": current,
                "sample_size": len(values),
            },
        )


_DETECTORS = {
    "zscore": lambda cfg: ZScoreDetector(threshold=cfg.get("threshold", 3.0)),
    "iqr": lambda cfg: IQRDetector(multiplier=cfg.get("multiplier", 1.5)),
    "ema": lambda cfg: EMADetector(
        alpha=cfg.get("alpha", 0.3),
        threshold=cfg.get("threshold", 3.0),
    ),
}


def detect_anomaly(
    values: list[float],
    current: float,
    method: AnomalyMethod = "zscore",
    config: Dict[str, Any] | None = None,
) -> AnomalyResult:
    """
    Detect anomaly using the specified method.

    Args:
        values: Historical baseline values.
        current: The current value to test.
        method: Detection method ('zscore', 'iqr', 'ema').
        config: Method-specific configuration.

    Returns:
        AnomalyResult with detection outcome and details.
    """
    cfg = config or {}
    factory = _DETECTORS.get(method)
    if not factory:
        return AnomalyResult(
            is_anomaly=False,
            score=0.0,
            method=method,
            details={"error": f"Unknown method: {method}"},
        )

    detector = factory(cfg)
    return detector.detect(values, current)
