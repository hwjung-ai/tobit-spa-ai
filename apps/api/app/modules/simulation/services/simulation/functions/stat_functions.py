"""
SIM Function Library - Statistical Functions

Functions based on statistical methods, time series analysis,
and probability distributions.
"""

from __future__ import annotations

import math
from typing import Any

from app.modules.simulation.services.simulation.functions.base import (
    FunctionCategory,
    FunctionComplexity,
    FunctionMetadata,
    FunctionOutput,
    FunctionParameter,
    SimulationFunction,
)


# =============================================================================
# 1. Moving Average Functions
# =============================================================================

class SimpleMovingAverage(SimulationFunction):
    """
    Simple Moving Average (SMA) for trend smoothing.

    Formula: SMA_t = (1/n) * Σ(x_i) for i in [t-n+1, t]

    Use Case: Noise reduction, trend identification
    Reference: Standard time series analysis
    """

    metadata = FunctionMetadata(
        id="stat_sma",
        name="Simple Moving Average",
        category=FunctionCategory.STATISTICAL,
        complexity=FunctionComplexity.BASIC,
        description="Simple moving average for trend smoothing",
        parameters=[
            FunctionParameter(
                name="window_size",
                type="integer",
                default=7,
                min=2,
                max=30,
                description="Number of periods to average",
                unit="",
            ),
            FunctionParameter(
                name="trend_slope",
                type="number",
                default=0.0,
                min=-5.0,
                max=5.0,
                step=0.1,
                description="Trend slope (change per period)",
                unit="",
            ),
            FunctionParameter(
                name="noise_level",
                type="number",
                default=0.1,
                min=0.0,
                max=1.0,
                step=0.05,
                description="Random noise level (std dev)",
                unit="",
            ),
            FunctionParameter(
                name="num_periods",
                type="integer",
                default=1,
                min=1,
                max=10,
                description="Number of periods to forecast",
                unit="",
            ),
            FunctionParameter(
                name="baseline_kpi",
                type="string",
                default="latency_ms",
                description="Which baseline KPI to forecast",
                unit="",
            ),
        ],
        outputs=[
            FunctionOutput(name="forecast", unit="varies", description="Forecasted value"),
            FunctionOutput(name="trend", unit="varies/period", description="Trend per period"),
            FunctionOutput(name="smoothed_baseline", unit="varies", description="Smoothed baseline"),
        ],
        confidence=0.70,
        tags=["moving-average", "trend", "smoothing", "forecast"],
        assumptions=[
            "Linear trend continues",
            "Noise is randomly distributed",
            "No seasonal patterns",
        ],
        references=["Box, G.E.P., Jenkins, G.M. (1976). Time Series Analysis"],
    )

    def execute(
        self,
        *,
        baseline: dict[str, float],
        assumptions: dict[str, float],
        context: dict[str, Any] | None = None,
    ) -> tuple[dict[str, float], float, dict[str, Any]]:
        _ = context

        window = int(assumptions.get("window_size", 7))
        slope = assumptions.get("trend_slope", 0.0)
        noise = assumptions.get("noise_level", 0.1)
        periods = int(assumptions.get("num_periods", 1))
        kpi_name = assumptions.get("baseline_kpi", "latency_ms")

        base_value = baseline.get(kpi_name, 50.0)

        # Apply smoothing (simulated - in real case, use historical data)
        smoothed = base_value  # Simplified for single baseline value

        # Forecast: SMA + trend * periods + noise
        forecast = smoothed + (slope * periods) + (noise * base_value * 0.1)

        outputs = {
            "forecast": round(forecast, 2),
            "trend": round(slope, 3),
            "smoothed_baseline": round(smoothed, 2),
        }

        debug_info = {
            "window": window,
            "base_value": base_value,
            "forecast_formula": f"SMA + ({slope} * {periods})",
        }

        return outputs, self.metadata.confidence, debug_info


class ExponentialMovingAverage(SimulationFunction):
    """
    Exponential Moving Average (EMA) for weighted recent data.

    Formula: EMA_t = α * x_t + (1-α) * EMA_{t-1}
    where α = 2 / (n + 1), n is the smoothing period

    Use Case: Responsive trend following, recent emphasis
    Reference: Technical analysis, signal processing
    """

    metadata = FunctionMetadata(
        id="stat_ema",
        name="Exponential Moving Average",
        category=FunctionCategory.STATISTICAL,
        complexity=FunctionComplexity.BASIC,
        description="Exponential moving average with recent data emphasis",
        parameters=[
            FunctionParameter(
                name="smoothing_period",
                type="integer",
                default=12,
                min=2,
                max=50,
                description="Smoothing period (higher = more smoothing)",
                unit="",
            ),
            FunctionParameter(
                name="change_rate",
                type="number",
                default=0.0,
                min=-0.5,
                max=0.5,
                step=0.01,
                description="Rate of change per period",
                unit="",
            ),
            FunctionParameter(
                name="num_periods",
                type="integer",
                default=1,
                min=1,
                max=10,
                description="Number of periods to forecast",
                unit="",
            ),
            FunctionParameter(
                name="baseline_kpi",
                type="string",
                default="latency_ms",
                description="Which baseline KPI to forecast",
                unit="",
            ),
        ],
        outputs=[
            FunctionOutput(name="forecast", unit="varies", description="Forecasted value"),
            FunctionOutput(name="ema_alpha", unit="", description="Smoothing alpha parameter"),
            FunctionOutput(name="momentum", unit="varies", description="Change momentum"),
        ],
        confidence=0.75,
        tags=["ema", "exponential", "trend", "momentum"],
        assumptions=[
            "Recent trends are more relevant",
            "Exponential decay applies",
        ],
        references=["Hunter, J. (1986). The Exponentially Weighted Moving Average"],
    )

    def execute(
        self,
        *,
        baseline: dict[str, float],
        assumptions: dict[str, float],
        context: dict[str, Any] | None = None,
    ) -> tuple[dict[str, float], float, dict[str, Any]]:
        _ = context

        period = int(assumptions.get("smoothing_period", 12))
        change_rate = assumptions.get("change_rate", 0.0)
        periods = int(assumptions.get("num_periods", 1))
        kpi_name = assumptions.get("baseline_kpi", "latency_ms")

        # Calculate alpha: α = 2 / (n + 1)
        alpha = 2.0 / (period + 1)

        base_value = baseline.get(kpi_name, 50.0)

        # EMA forecast with momentum
        momentum = base_value * change_rate
        forecast = base_value + (momentum * periods)

        outputs = {
            "forecast": round(forecast, 2),
            "ema_alpha": round(alpha, 4),
            "momentum": round(momentum, 3),
        }

        debug_info = {
            "alpha": round(alpha, 4),
            "period": period,
            "formula": "EMA_t = α*x_t + (1-α)*EMA_{t-1}",
        }

        return outputs, self.metadata.confidence, debug_info


# =============================================================================
# 2. Regression Functions
# =============================================================================

class LinearRegressionForecast(SimulationFunction):
    """
    Linear regression for trend extrapolation.

    Formula: y = a*x + b
    where a = slope, b = intercept

    Use Case: Trend forecasting, capacity planning
    Reference: Standard regression analysis
    """

    metadata = FunctionMetadata(
        id="stat_linear_regression",
        name="Linear Regression Forecast",
        category=FunctionCategory.STATISTICAL,
        complexity=FunctionComplexity.BASIC,
        description="Linear regression trend extrapolation",
        parameters=[
            FunctionParameter(
                name="slope",
                type="number",
                default=1.0,
                min=-10.0,
                max=10.0,
                step=0.1,
                description="Regression slope (change per unit x)",
                unit="",
            ),
            FunctionParameter(
                name="intercept",
                type="number",
                default=50.0,
                min=-100.0,
                max=200.0,
                description="Y-intercept (baseline at x=0)",
                unit="",
            ),
            FunctionParameter(
                name="forecast_x",
                type="number",
                default=10.0,
                min=0.0,
                max=100.0,
                description="X value to forecast at (e.g., days ahead)",
                unit="",
            ),
            FunctionParameter(
                name="r_squared",
                type="number",
                default=0.85,
                min=0.0,
                max=1.0,
                step=0.05,
                description="R-squared (goodness of fit)",
                unit="",
            ),
        ],
        outputs=[
            FunctionOutput(name="forecast", unit="varies", description="Forecasted value"),
            FunctionOutput(name="confidence_interval_lower", unit="varies", description="Lower CI bound"),
            FunctionOutput(name="confidence_interval_upper", unit="varies", description="Upper CI bound"),
        ],
        confidence=0.78,
        tags=["regression", "linear", "forecast", "trend"],
        assumptions=[
            "Linear relationship exists",
            "Residuals are normally distributed",
            "No autocorrelation",
        ],
        references=[" Montgomery, D.C., Peck, E.A. (1992). Introduction to Linear Regression"],
    )

    def execute(
        self,
        *,
        baseline: dict[str, float],
        assumptions: dict[str, float],
        context: dict[str, Any] | None = None,
    ) -> tuple[dict[str, float], float, dict[str, Any]]:
        _ = context
        _ = baseline

        slope = assumptions.get("slope", 1.0)
        intercept = assumptions.get("intercept", 50.0)
        x = assumptions.get("forecast_x", 10.0)
        r2 = assumptions.get("r_squared", 0.85)

        # Linear forecast: y = slope*x + intercept
        forecast = slope * x + intercept

        # Confidence interval (simplified)
        # CI width increases with distance from mean
        std_error = math.sqrt(1 - r2) * abs(intercept) * 0.2
        margin = std_error * math.sqrt(1 + 1/30 + (x - 15)**2 / 1000)  # Simplified

        outputs = {
            "forecast": round(forecast, 2),
            "confidence_interval_lower": round(forecast - margin, 2),
            "confidence_interval_upper": round(forecast + margin, 2),
        }

        debug_info = {
            "slope": slope,
            "intercept": intercept,
            "r_squared": r2,
            "formula": f"y = {slope}*x + {intercept}",
        }

        return outputs, self.metadata.confidence, debug_info


class PolynomialRegressionForecast(SimulationFunction):
    """
    Polynomial regression for curved relationships.

    Formula: y = a*x² + b*x + c

    Use Case: Non-linear trends, acceleration, deceleration
    Reference: Polynomial regression analysis
    """

    metadata = FunctionMetadata(
        id="stat_polynomial_regression",
        name="Polynomial Regression Forecast",
        category=FunctionCategory.STATISTICAL,
        complexity=FunctionComplexity.INTERMEDIATE,
        description="Polynomial regression for non-linear trends",
        parameters=[
            FunctionParameter(
                name="quadratic_coeff",
                type="number",
                default=0.05,
                min=-1.0,
                max=1.0,
                step=0.01,
                description="Quadratic coefficient (a in ax²+bx+c)",
                unit="",
            ),
            FunctionParameter(
                name="linear_coeff",
                type="number",
                default=2.0,
                min=-10.0,
                max=10.0,
                step=0.1,
                description="Linear coefficient (b in ax²+bx+c)",
                unit="",
            ),
            FunctionParameter(
                name="intercept",
                type="number",
                default=50.0,
                min=-100.0,
                max=200.0,
                description="Constant term (c in ax²+bx+c)",
                unit="",
            ),
            FunctionParameter(
                name="forecast_x",
                type="number",
                default=10.0,
                min=0.0,
                max=50.0,
                description="X value to forecast at",
                unit="",
            ),
        ],
        outputs=[
            FunctionOutput(name="forecast", unit="varies", description="Forecasted value"),
            FunctionOutput(name="curvature", unit="", description="Curve direction (convex/concave)"),
        ],
        confidence=0.76,
        tags=["polynomial", "non-linear", "curvature", "acceleration"],
        assumptions=[
            "Polynomial relationship fits the data",
            "Appropriate degree chosen",
        ],
        references=["Draper, N.R., Smith, H. (1998). Applied Regression Analysis"],
    )

    def execute(
        self,
        *,
        baseline: dict[str, float],
        assumptions: dict[str, float],
        context: dict[str, Any] | None = None,
    ) -> tuple[dict[str, float], float, dict[str, Any]]:
        _ = context
        _ = baseline

        a = assumptions.get("quadratic_coeff", 0.05)
        b = assumptions.get("linear_coeff", 2.0)
        c = assumptions.get("intercept", 50.0)
        x = assumptions.get("forecast_x", 10.0)

        # Polynomial: y = ax² + bx + c
        forecast = (a * x * x) + (b * x) + c
        curvature = "convex" if a > 0 else ("concave" if a < 0 else "linear")

        outputs = {
            "forecast": round(forecast, 2),
            "curvature": 1.0 if a > 0 else (-1.0 if a < 0 else 0.0),
        }

        debug_info = {
            "a": a,
            "b": b,
            "c": c,
            "x": x,
            "curvature_type": curvature,
            "formula": f"y = {a}*x² + {b}*x + {c}",
        }

        return outputs, self.metadata.confidence, debug_info


# =============================================================================
# 3. Variance/Dispersion Functions
# =============================================================================

class StandardDeviationImpact(SimulationFunction):
    """
    Assess impact based on standard deviation changes.

    Formula: New value = mean ± z * std_dev

    Use Case: Risk assessment, confidence intervals, SLA bounds
    Reference: Statistical quality control
    """

    metadata = FunctionMetadata(
        id="stat_std_dev_impact",
        name="Standard Deviation Impact",
        category=FunctionCategory.STATISTICAL,
        complexity=FunctionComplexity.BASIC,
        description="Assess KPI impact based on standard deviation",
        parameters=[
            FunctionParameter(
                name="z_score",
                type="number",
                default=1.96,
                min=0.0,
                max=4.0,
                step=0.01,
                description="Z-score for confidence (1.96 = 95%)",
                unit="",
            ),
            FunctionParameter(
                name="std_dev_multiplier",
                type="number",
                default=1.0,
                min=0.1,
                max=3.0,
                step=0.1,
                description="Multiply standard deviation by this factor",
                unit="",
            ),
            FunctionParameter(
                name="direction",
                type="string",
                default="upper",
                description="Direction: upper, lower, or both",
                unit="",
            ),
            FunctionParameter(
                name="baseline_mean",
                type="number",
                default=50.0,
                min=0.0,
                max=1000.0,
                description="Mean value of baseline",
                unit="",
            ),
            FunctionParameter(
                name="baseline_std",
                type="number",
                default=10.0,
                min=0.1,
                max=200.0,
                description="Standard deviation of baseline",
                unit="",
            ),
        ],
        outputs=[
            FunctionOutput(name="upper_bound", unit="varies", description="Upper confidence bound"),
            FunctionOutput(name="lower_bound", unit="varies", description="Lower confidence bound"),
            FunctionOutput(name="range", unit="varies", description="Total range"),
        ],
        confidence=0.82,
        tags=["std-dev", "confidence-interval", "risk", "bounds"],
        assumptions=[
            "Normal distribution applies",
            "Independent samples",
        ],
        references=["Montgomery, D.C. (2019). Introduction to Statistical Quality Control"],
    )

    def execute(
        self,
        *,
        baseline: dict[str, float],
        assumptions: dict[str, float],
        context: dict[str, Any] | None = None,
    ) -> tuple[dict[str, float], float, dict[str, Any]]:
        _ = context

        z = assumptions.get("z_score", 1.96)
        std_mult = assumptions.get("std_dev_multiplier", 1.0)
        direction = assumptions.get("direction", "upper")
        mean = assumptions.get("baseline_mean", 50.0)
        std = assumptions.get("baseline_std", 10.0)

        effective_std = std * std_mult
        margin = z * effective_std

        upper_bound = mean + margin
        lower_bound = max(0, mean - margin)
        range_val = upper_bound - lower_bound

        outputs = {
            "upper_bound": round(upper_bound, 2),
            "lower_bound": round(lower_bound, 2),
            "range": round(range_val, 2),
        }

        debug_info = {
            "z_score": z,
            "confidence_level": round((1 - (1 - math.erf(z / math.sqrt(2))) * 2) * 100, 1),
            "margin": round(margin, 2),
            "direction": direction,
        }

        return outputs, self.metadata.confidence, debug_info


# =============================================================================
# 4. Distribution Functions
# =============================================================================

class PercentileForecast(SimulationFunction):
    """
    Forecast based on percentile distribution.

    Formula: Value at percentile p

    Use Case: Tail risk assessment, SLA planning
    Reference: Quantile functions, percentile-based forecasting
    """

    metadata = FunctionMetadata(
        id="stat_percentile",
        name="Percentile Forecast",
        category=FunctionCategory.STATISTICAL,
        complexity=FunctionComplexity.BASIC,
        description="Forecast KPI at specific percentile",
        parameters=[
            FunctionParameter(
                name="percentile",
                type="number",
                default=95.0,
                min=50.0,
                max=99.9,
                step=0.1,
                description="Target percentile (e.g., 95 for p95)",
                unit="",
            ),
            FunctionParameter(
                name="baseline_mean",
                type="number",
                default=50.0,
                min=0.0,
                max=1000.0,
                description="Mean value of baseline",
                unit="",
            ),
            FunctionParameter(
                name="baseline_std",
                type="number",
                default=10.0,
                min=0.1,
                max=200.0,
                description="Standard deviation of baseline",
                unit="",
            ),
            FunctionParameter(
                name="distribution",
                type="string",
                default="normal",
                description="Distribution type: normal, lognormal, exponential",
                unit="",
            ),
        ],
        outputs=[
            FunctionOutput(name="percentile_value", unit="varies", description="Value at percentile"),
            FunctionOutput(name="tail_value", unit="varies", description="Tail distance from mean"),
        ],
        confidence=0.80,
        tags=["percentile", "tail-risk", "sla", "distribution"],
        assumptions=[
            "Specified distribution applies",
            "Sufficient sample size",
        ],
        references=["Quantile Functions and Statistical Distributions"],
    )

    def execute(
        self,
        *,
        baseline: dict[str, float],
        assumptions: dict[str, float],
        context: dict[str, Any] | None = None,
    ) -> tuple[dict[str, float], float, dict[str, Any]]:
        _ = context

        percentile = assumptions.get("percentile", 95.0)
        mean = assumptions.get("baseline_mean", 50.0)
        std = assumptions.get("baseline_std", 10.0)
        distribution = assumptions.get("distribution", "normal")

        # Convert percentile to z-score
        # p95 ≈ 1.645, p99 ≈ 2.326
        z_scores = {90: 1.282, 95: 1.645, 99: 2.326, 99.9: 3.090}
        z = z_scores.get(int(percentile), 1.645)

        if distribution == "normal":
            percentile_val = mean + (z * std)
        elif distribution == "lognormal":
            # Simplified lognormal approximation
            sigma = math.sqrt(math.log(1 + (std / mean) ** 2))
            mu = math.log(mean) - 0.5 * sigma * sigma
            percentile_val = math.exp(mu + z * sigma)
        else:  # exponential
            percentile_val = -mean * math.log(1 - percentile / 100)

        tail_value = percentile_val - mean

        outputs = {
            "percentile_value": round(percentile_val, 2),
            "tail_value": round(tail_value, 2),
        }

        debug_info = {
            "percentile": percentile,
            "z_score": round(z, 3),
            "distribution": distribution,
        }

        return outputs, self.metadata.confidence, debug_info
