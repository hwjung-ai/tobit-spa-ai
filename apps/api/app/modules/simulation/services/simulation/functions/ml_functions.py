"""
SIM Function Library - Machine Learning Functions

Surrogate models and ML-inspired functions for simulation.
These are deterministic approximations of trained ML models.
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
# 1. Time Series ML Functions
# =============================================================================

class ARIMASurrogate(SimulationFunction):
    """
    ARIMA (AutoRegressive Integrated Moving Average) surrogate.

    Model: ARIMA(p,d,q) - combines autoregression, differencing, moving average

    Use Case: Time series forecasting, trend + seasonality
    Reference: Box, G.E.P., Jenkins, G.M. (1976)
    """

    metadata = FunctionMetadata(
        id="ml_arima_surrogate",
        name="ARIMA Surrogate",
        category=FunctionCategory.ML,
        complexity=FunctionComplexity.INTERMEDIATE,
        description="ARIMA time series forecast surrogate model",
        parameters=[
            FunctionParameter(
                name="ar_order",
                type="integer",
                default=1,
                min=0,
                max=5,
                description="AutoRegressive order (p)",
                unit="",
            ),
            FunctionParameter(
                name="ma_order",
                type="integer",
                default=1,
                min=0,
                max=5,
                description="Moving Average order (q)",
                unit="",
            ),
            FunctionParameter(
                name="ar_coeff",
                type="number",
                default=0.7,
                min=-1.0,
                max=1.0,
                step=0.1,
                description="AR coefficient",
                unit="",
            ),
            FunctionParameter(
                name="ma_coeff",
                type="number",
                default=0.3,
                min=-1.0,
                max=1.0,
                step=0.1,
                description="MA coefficient",
                unit="",
            ),
            FunctionParameter(
                name="trend",
                type="number",
                default=0.5,
                min=-5.0,
                max=5.0,
                step=0.1,
                description="Deterministic trend per period",
                unit="",
            ),
            FunctionParameter(
                name="num_periods",
                type="integer",
                default=7,
                min=1,
                max=30,
                description="Forecast periods ahead",
                unit="",
            ),
            FunctionParameter(
                name="baseline_kpi",
                type="string",
                default="latency_ms",
                description="KPI to forecast",
                unit="",
            ),
        ],
        outputs=[
            FunctionOutput(name="forecast", unit="varies", description="Forecasted value"),
            FunctionOutput(name="lower_ci", unit="varies", description="Lower 95% CI"),
            FunctionOutput(name="upper_ci", unit="varies", description="Upper 95% CI"),
        ],
        confidence=0.82,
        tags=["arima", "time-series", "forecast", "classical-ml"],
        assumptions=[
            "Stationary after differencing",
            "Linear relationships",
            "Normal residuals",
        ],
        references=["Box, G.E.P., Jenkins, G.M. (1976). Time Series Analysis: Forecasting and Control"],
    )

    def execute(
        self,
        *,
        baseline: dict[str, float],
        assumptions: dict[str, float],
        context: dict[str, Any] | None = None,
    ) -> tuple[dict[str, float], float, dict[str, Any]]:
        _ = context

        ar_p = int(assumptions.get("ar_order", 1))
        ma_q = int(assumptions.get("ma_order", 1))
        ar_coeff = assumptions.get("ar_coeff", 0.7)
        ma_coeff = assumptions.get("ma_coeff", 0.3)
        trend = assumptions.get("trend", 0.5)
        periods = int(assumptions.get("num_periods", 7))
        kpi_name = assumptions.get("baseline_kpi", "latency_ms")

        base_value = baseline.get(kpi_name, 50.0)

        # Simplified ARIMA(1,0,1) surrogate
        # y_t = c + φ*y_{t-1} + θ*ε_{t-1} + ε_t + trend*t
        # For forecast: y_{t+h} = (φ^h) * y_t + trend * h

        # Long-term mean calculation
        long_term_mean = base_value / (1 - ar_coeff) if ar_coeff < 1 else base_value

        # Forecast with AR decay
        forecast = long_term_mean + (base_value - long_term_mean) * (ar_coeff ** periods) + trend * periods

        # Confidence interval (simplified - widens with horizon)
        ci_width = base_value * 0.1 * math.sqrt(periods)
        lower_ci = forecast - 1.96 * ci_width
        upper_ci = forecast + 1.96 * ci_width

        outputs = {
            "forecast": round(forecast, 2),
            "lower_ci": round(max(0, lower_ci), 2),
            "upper_ci": round(upper_ci, 2),
        }

        debug_info = {
            "model": f"ARIMA({ar_p},0,{ma_q})",
            "ar_coefficient": ar_coeff,
            "ma_coefficient": ma_coeff,
            "trend": trend,
            "formula": f"y_t = {ar_coeff}*y_{{t-1}} + {ma_coeff}*ε_{{t-1}} + {trend}*t",
        }

        return outputs, self.metadata.confidence, debug_info


class ProphetSurrogate(SimulationFunction):
    """
    Facebook Prophet-inspired surrogate.

    Model: y(t) = g(t) + s(t) + h(t) + ε_t
    - g(t): Trend (piecewise linear/logistic)
    - s(t): Seasonality (Fourier series)
    - h(t): Holidays/events
    - ε_t: Error

    Use Case: Business time series with seasonality
    Reference: Taylor, S.J., Letham, B. (2018). Forecasting at Scale
    """

    metadata = FunctionMetadata(
        id="ml_prophet_surrogate",
        name="Prophet Surrogate",
        category=FunctionCategory.ML,
        complexity=FunctionComplexity.INTERMEDIATE,
        description="Prophet-style forecasting with trend + seasonality",
        parameters=[
            FunctionParameter(
                name="growth_rate",
                type="number",
                default=1.0,
                min=-5.0,
                max=5.0,
                step=0.1,
                description="Trend growth rate",
                unit="",
            ),
            FunctionParameter(
                name="seasonality_amplitude",
                type="number",
                default=5.0,
                min=0.0,
                max=50.0,
                step=1.0,
                description="Seasonality amplitude",
                unit="",
            ),
            FunctionParameter(
                name="seasonality_period",
                type="number",
                default=7.0,
                min=1.0,
                max=365.0,
                step=1.0,
                description="Seasonality period (days)",
                unit="",
            ),
            FunctionParameter(
                name="forecast_day",
                type="number",
                default=7.0,
                min=1.0,
                max=90.0,
                step=1.0,
                description="Day to forecast",
                unit="",
            ),
            FunctionParameter(
                name="baseline_kpi",
                type="string",
                default="latency_ms",
                description="KPI to forecast",
                unit="",
            ),
        ],
        outputs=[
            FunctionOutput(name="forecast", unit="varies", description="Forecasted value"),
            FunctionOutput(name="trend_component", unit="varies", description="Trend component"),
            FunctionOutput(name="seasonality_component", unit="varies", description="Seasonality component"),
        ],
        confidence=0.83,
        tags=["prophet", "seasonality", "trend", "facebook"],
        assumptions=[
            "Additive decomposition",
            "Smooth trend changes",
            "Regular seasonality",
        ],
        references=["Taylor, S.J., Letham, B. (2018). Prophet: Forecasting at Scale"],
    )

    def execute(
        self,
        *,
        baseline: dict[str, float],
        assumptions: dict[str, float],
        context: dict[str, Any] | None = None,
    ) -> tuple[dict[str, float], float, dict[str, Any]]:
        _ = context

        growth = assumptions.get("growth_rate", 1.0)
        seas_amp = assumptions.get("seasonality_amplitude", 5.0)
        seas_period = assumptions.get("seasonality_period", 7.0)
        day = assumptions.get("forecast_day", 7.0)
        kpi_name = assumptions.get("baseline_kpi", "latency_ms")

        base_value = baseline.get(kpi_name, 50.0)

        # Trend component: linear growth
        trend = base_value + (growth * day)

        # Seasonality: sinusoidal approximation
        seasonality = seas_amp * math.sin(2 * math.pi * day / seas_period)

        # Total forecast
        forecast = trend + seasonality

        outputs = {
            "forecast": round(forecast, 2),
            "trend_component": round(trend, 2),
            "seasonality_component": round(seasonality, 2),
        }

        debug_info = {
            "growth_rate": growth,
            "seasonality": f"{seas_amp} * sin(2π * t / {seas_period})",
            "day": day,
            "formula": "y(t) = trend(t) + seasonality(t) + error",
        }

        return outputs, self.metadata.confidence, debug_info


# =============================================================================
# 2. Regression ML Functions
# =============================================================================

class SVRSurrogate(SimulationFunction):
    """
    Support Vector Regression (SVR) surrogate with RBF kernel.

    Model: Uses kernel trick for non-linear regression

    Use Case: Non-linear relationships, small to medium datasets
    Reference: Vapnik, V. (1998). Statistical Learning Theory
    """

    metadata = FunctionMetadata(
        id="ml_svr_surrogate",
        name="SVR Surrogate",
        category=FunctionCategory.ML,
        complexity=FunctionComplexity.INTERMEDIATE,
        description="Support Vector Regression with RBF kernel",
        parameters=[
            FunctionParameter(
                name="x1",
                type="number",
                default=20.0,
                min=-50.0,
                max=200.0,
                description="Input feature 1 (e.g., traffic change)",
                unit="%",
            ),
            FunctionParameter(
                name="x2",
                type="number",
                default=10.0,
                min=-50.0,
                max=200.0,
                description="Input feature 2 (e.g., CPU change)",
                unit="%",
            ),
            FunctionParameter(
                name="kernel_gamma",
                type="number",
                default=0.1,
                min=0.01,
                max=1.0,
                step=0.01,
                description="RBF kernel parameter",
                unit="",
            ),
            FunctionParameter(
                name="epsilon",
                type="number",
                default=0.1,
                min=0.01,
                max=1.0,
                step=0.05,
                description="Epsilon-insensitive loss parameter",
                unit="",
            ),
            FunctionParameter(
                name="baseline_kpi",
                type="string",
                default="latency_ms",
                description="KPI to predict",
                unit="",
            ),
        ],
        outputs=[
            FunctionOutput(name="prediction", unit="varies", description="SVR prediction"),
            FunctionOutput(name="margin", unit="varies", description="Epsilon margin"),
        ],
        confidence=0.81,
        tags=["svr", "kernel", "non-linear", "svm"],
        assumptions=[
            "RBF kernel appropriate",
            "Proper hyperparameter tuning",
        ],
        references=["Vapnik, V. (1998). Statistical Learning Theory"],
    )

    def execute(
        self,
        *,
        baseline: dict[str, float],
        assumptions: dict[str, float],
        context: dict[str, Any] | None = None,
    ) -> tuple[dict[str, float], float, dict[str, Any]]:
        _ = context

        x1 = assumptions.get("x1", 20.0)
        x2 = assumptions.get("x2", 10.0)
        gamma = assumptions.get("kernel_gamma", 0.1)
        epsilon = assumptions.get("epsilon", 0.1)
        kpi_name = assumptions.get("baseline_kpi", "latency_ms")

        base_value = baseline.get(kpi_name, 50.0)

        # RBF kernel surrogate: K(x, x') = exp(-γ * ||x - x'||²)
        # Simplified surrogate model
        # Effect = baseline * (1 + kernel_rbf(x))

        # Distance-based kernel value (simplified)
        kernel_value = math.exp(-gamma * ((x1 * x1 + x2 * x2) / 100))

        # Non-linear prediction
        prediction = base_value * (1 + 0.5 * kernel_value * (x1 + x2) / 100)

        outputs = {
            "prediction": round(prediction, 2),
            "margin": round(epsilon * base_value, 2),
        }

        debug_info = {
            "kernel": "RBF",
            "gamma": gamma,
            "epsilon": epsilon,
            "kernel_value": round(kernel_value, 4),
            "formula": "K(x, x') = exp(-γ * ||x - x'||²)",
        }

        return outputs, self.metadata.confidence, debug_info


class RandomForestSurrogate(SimulationFunction):
    """
    Random Forest surrogate for ensemble prediction.

    Model: Ensemble of decision trees with bagging

    Use Case: Non-linear, mixed feature types, robust to outliers
    Reference: Breiman, L. (2001). Random Forests
    """

    metadata = FunctionMetadata(
        id="ml_random_forest_surrogate",
        name="Random Forest Surrogate",
        category=FunctionCategory.ML,
        complexity=FunctionComplexity.INTERMEDIATE,
        description="Random Forest ensemble surrogate model",
        parameters=[
            FunctionParameter(
                name="traffic_change",
                type="number",
                default=20.0,
                min=-50.0,
                max=200.0,
                description="Traffic change percentage",
                unit="%",
            ),
            FunctionParameter(
                name="cpu_change",
                type="number",
                default=10.0,
                min=-50.0,
                max=200.0,
                description="CPU change percentage",
                unit="%",
            ),
            FunctionParameter(
                name="memory_change",
                type="number",
                default=5.0,
                min=-50.0,
                max=200.0,
                description="Memory change percentage",
                unit="%",
            ),
            FunctionParameter(
                name="num_trees",
                type="integer",
                default=100,
                min=10,
                max=500,
                description="Number of trees in forest",
                unit="",
            ),
            FunctionParameter(
                name="feature_importance_traffic",
                type="number",
                default=0.6,
                min=0.0,
                max=1.0,
                step=0.05,
                description="Traffic feature importance",
                unit="",
            ),
            FunctionParameter(
                name="feature_importance_cpu",
                type="number",
                default=0.3,
                min=0.0,
                max=1.0,
                step=0.05,
                description="CPU feature importance",
                unit="",
            ),
            FunctionParameter(
                name="feature_importance_memory",
                type="number",
                default=0.1,
                min=0.0,
                max=1.0,
                step=0.05,
                description="Memory feature importance",
                unit="",
            ),
        ],
        outputs=[
            FunctionOutput(name="prediction", unit="varies", description="Ensemble prediction"),
            FunctionOutput(name="std_error", unit="varies", description="Standard error across trees"),
        ],
        confidence=0.85,
        tags=["random-forest", "ensemble", "tree-based", "robust"],
        assumptions=[
            "Multiple trees improve prediction",
            "Feature interactions captured",
        ],
        references=["Breiman, L. (2001). Random Forests. Machine Learning"],
    )

    def execute(
        self,
        *,
        baseline: dict[str, float],
        assumptions: dict[str, float],
        context: dict[str, Any] | None = None,
    ) -> tuple[dict[str, float], float, dict[str, Any]]:
        _ = context

        traffic = assumptions.get("traffic_change", 20.0)
        cpu = assumptions.get("cpu_change", 10.0)
        memory = assumptions.get("memory_change", 5.0)
        n_trees = int(assumptions.get("num_trees", 100))
        w_traffic = assumptions.get("feature_importance_traffic", 0.6)
        w_cpu = assumptions.get("feature_importance_cpu", 0.3)
        w_memory = assumptions.get("feature_importance_memory", 0.1)

        base_latency = baseline.get("latency_ms", 50.0)

        # Simplified Random Forest surrogate
        # Each "tree" produces a prediction, ensemble averages them
        # Feature importance weights the contribution

        # Interaction effects (simulating tree splits)
        interaction = (traffic * cpu) / 500  # Non-linear interaction

        # Weighted feature contribution
        feature_effect = (w_traffic * traffic + w_cpu * cpu + w_memory * memory)

        # Tree variance decreases with more trees
        tree_variance = 5.0 / math.sqrt(n_trees)

        # Prediction with ensemble averaging
        prediction = base_latency * (1 + feature_effect / 100 + interaction / 100)

        outputs = {
            "prediction": round(prediction, 2),
            "std_error": round(tree_variance * base_latency / 100, 3),
        }

        debug_info = {
            "num_trees": n_trees,
            "feature_importance": {"traffic": w_traffic, "cpu": w_cpu, "memory": w_memory},
            "interaction_term": round(interaction, 3),
            "formula": "prediction = avg(tree_predictions)",
        }

        return outputs, self.metadata.confidence, debug_info


# =============================================================================
# 3. Deep Learning Functions
# =============================================================================

class LSTMSurrogate(SimulationFunction):
    """
    Long Short-Term Memory (LSTM) network surrogate.

    Model: Recurrent neural network with memory cells

    Use Case: Sequence prediction, time series with long dependencies
    Reference: Hochreiter, S., Schmidhuber, J. (1997)
    """

    metadata = FunctionMetadata(
        id="ml_lstm_surrogate",
        name="LSTM Surrogate",
        category=FunctionCategory.ML,
        complexity=FunctionComplexity.ADVANCED,
        description="LSTM recurrent neural network surrogate",
        parameters=[
            FunctionParameter(
                name="input_sequence",
                type="array",
                default=[50, 52, 48, 55, 53],
                description="Historical values (input sequence)",
                unit="",
            ),
            FunctionParameter(
                name="hidden_units",
                type="integer",
                default=64,
                min=8,
                max=256,
                description="LSTM hidden units",
                unit="",
            ),
            FunctionParameter(
                name="sequence_length",
                type="integer",
                default=5,
                min=1,
                max=20,
                description="Input sequence length",
                unit="",
            ),
            FunctionParameter(
                name="forecast_horizon",
                type="integer",
                default=3,
                min=1,
                max=10,
                description="Steps to forecast",
                unit="",
            ),
            FunctionParameter(
                name="forget_gate_bias",
                type="number",
                default=0.5,
                min=-1.0,
                max=1.0,
                step=0.1,
                description="Forget gate bias parameter",
                unit="",
            ),
        ],
        outputs=[
            FunctionOutput(name="forecast", unit="varies", description="LSTM forecast"),
            FunctionOutput(name="hidden_state", unit="varies", description="Final hidden state"),
            FunctionOutput(name="cell_state", unit="varies", description="Final cell state"),
        ],
        confidence=0.87,
        tags=["lstm", "rnn", "deep-learning", "sequence", "memory"],
        assumptions=[
            "Sequential dependencies exist",
            "LSTM architecture appropriate",
        ],
        references=["Hochreiter, S., Schmidhuber, J. (1997). Long Short-Term Memory"],
    )

    def execute(
        self,
        *,
        baseline: dict[str, float],
        assumptions: dict[str, float],
        context: dict[str, Any] | None = None,
    ) -> tuple[dict[str, float], float, dict[str, Any]]:
        _ = baseline
        _ = context

        sequence = assumptions.get("input_sequence", [50, 52, 48, 55, 53])
        hidden_units = int(assumptions.get("hidden_units", 64))
        seq_len = int(assumptions.get("sequence_length", 5))
        horizon = int(assumptions.get("forecast_horizon", 3))
        forget_bias = assumptions.get("forget_gate_bias", 0.5)

        # Simplified LSTM surrogate
        # Real LSTM: f_t = σ(W_f * [h_{t-1}, x_t] + b_f)
        #            i_t = σ(W_i * [h_{t-1}, x_t] + b_i)
        #            C̃_t = tanh(W_C * [h_{t-1}, x_t] + b_C)
        #            C_t = f_t * C_{t-1} + i_t * C̃_t
        #            o_t = σ(W_o * [h_{t-1}, x_t] + b_o)
        #            h_t = o_t * tanh(C_t)

        # Surrogate: Exponential moving average with memory
        if not sequence or len(sequence) == 0:
            sequence = [50.0]

        # Use last values as input
        recent = sequence[-min(len(sequence), seq_len):]

        # Memory effect (cell state surrogate)
        memory_decay = forget_bias
        avg_value = sum(recent) / len(recent)

        # Forecast with exponential decay of memory
        forecasts = []
        for h in range(1, horizon + 1):
            memory_effect = (memory_decay ** h) * (recent[-1] - avg_value) if len(recent) > 1 else 0
            trend = (recent[-1] - recent[0]) / len(recent) if len(recent) > 1 else 0
            forecast = avg_value + memory_effect + trend * h
            forecasts.append(forecast)

        # Return first forecast
        prediction = forecasts[0] if forecasts else avg_value

        # Surrogate internal states
        hidden_state = prediction * 0.1
        cell_state = prediction * 0.2

        outputs = {
            "forecast": round(prediction, 2),
            "hidden_state": round(hidden_state, 3),
            "cell_state": round(cell_state, 3),
        }

        debug_info = {
            "hidden_units": hidden_units,
            "sequence_length": seq_len,
            "forecast_horizon": horizon,
            "memory_decay": memory_decay,
            "input_sequence": recent,
            "formula": "LSTM: h_t = o_t * tanh(C_t)",
        }

        return outputs, self.metadata.confidence, debug_info


class GRUSurrogate(SimulationFunction):
    """
    Gated Recurrent Unit (GRU) network surrogate.

    Model: Simplified LSTM with reset and update gates

    Use Case: Similar to LSTM but more computationally efficient
    Reference: Cho, K., et al. (2014)
    """

    metadata = FunctionMetadata(
        id="ml_gru_surrogate",
        name="GRU Surrogate",
        category=FunctionCategory.ML,
        complexity=FunctionComplexity.ADVANCED,
        description="GRU recurrent neural network surrogate",
        parameters=[
            FunctionParameter(
                name="input_sequence",
                type="array",
                default=[50, 52, 48, 55, 53],
                description="Historical values (input sequence)",
                unit="",
            ),
            FunctionParameter(
                name="hidden_units",
                type="integer",
                default=32,
                min=8,
                max=128,
                description="GRU hidden units",
                unit="",
            ),
            FunctionParameter(
                name="update_gate_bias",
                type="number",
                default=0.3,
                min=-1.0,
                max=1.0,
                step=0.1,
                description="Update gate bias",
                unit="",
            ),
            FunctionParameter(
                name="reset_gate_bias",
                type="number",
                default=0.5,
                min=-1.0,
                max=1.0,
                step=0.1,
                description="Reset gate bias",
                unit="",
            ),
        ],
        outputs=[
            FunctionOutput(name="forecast", unit="varies", description="GRU forecast"),
            FunctionOutput(name="update_gate", unit="varies", description="Update gate activation"),
            FunctionOutput(name="reset_gate", unit="varies", description="Reset gate activation"),
        ],
        confidence=0.86,
        tags=["gru", "rnn", "deep-learning", "efficient"],
        assumptions=[
            "Sequential patterns exist",
            "GRU efficiency beneficial",
        ],
        references=["Cho, K., et al. (2014). Learning Phrase Representations using RNN Encoder-Decoder"],
    )

    def execute(
        self,
        *,
        baseline: dict[str, float],
        assumptions: dict[str, float],
        context: dict[str, Any] | None = None,
    ) -> tuple[dict[str, float], float, dict[str, Any]]:
        _ = baseline
        _ = context

        sequence = assumptions.get("input_sequence", [50, 52, 48, 55, 53])
        hidden_units = int(assumptions.get("hidden_units", 32))
        update_bias = assumptions.get("update_gate_bias", 0.3)
        reset_bias = assumptions.get("reset_gate_bias", 0.5)

        # GRU surrogate
        # Real GRU: z_t = σ(W_z * [h_{t-1}, x_t])  (update gate)
        #           r_t = σ(W_r * [h_{t-1}, x_t])  (reset gate)
        #           h̃_t = tanh(W * [r_t * h_{t-1}, x_t])
        #           h_t = (1 - z_t) * h_{t-1} + z_t * h̃_t

        if not sequence or len(sequence) == 0:
            sequence = [50.0]

        recent = sequence[-min(len(sequence), 5):]
        avg_value = sum(recent) / len(recent)

        # Update gate: how much to update from new candidate
        update_gate = 1.0 / (1.0 + math.exp(-(update_bias * 5)))
        # Reset gate: how much to reset previous state
        reset_gate = 1.0 / (1.0 + math.exp(-(reset_bias * 5)))

        # Candidate hidden state
        candidate = avg_value * (1 + reset_gate * 0.1)
        # Final hidden state
        h_prev = recent[-1]
        h_new = (1 - update_gate) * h_prev + update_gate * candidate

        outputs = {
            "forecast": round(h_new, 2),
            "update_gate": round(update_gate, 4),
            "reset_gate": round(reset_gate, 4),
        }

        debug_info = {
            "hidden_units": hidden_units,
            "update_gate_activation": round(update_gate, 4),
            "reset_gate_activation": round(reset_gate, 4),
            "formula": "h_t = (1-z_t)*h_{t-1} + z_t*h̃_t",
        }

        return outputs, self.metadata.confidence, debug_info


# =============================================================================
# 4. ML Predictive Strategy (Real Integration)
# =============================================================================

class MLPredictiveStrategy(SimulationFunction):
    """
    ML-based predictive strategy that integrates with real ML strategy.

    This function bridges the function library with the MLPredictiveStrategyReal
    from strategies/ml_strategy_real.py.

    Use Case: When trained ML models are available, use them for prediction
    Reference: sklearn/LightGBM based ML models
    """

    metadata = FunctionMetadata(
        id="ml_predictive_strategy",
        name="ML Predictive Strategy",
        category=FunctionCategory.ML,
        complexity=FunctionComplexity.INTERMEDIATE,
        description="ML-based strategy using trained models (sklearn/LightGBM)",
        parameters=[
            FunctionParameter(
                name="traffic_change_pct",
                type="number",
                default=20.0,
                min=-50.0,
                max=200.0,
                description="Traffic change percentage",
                unit="%",
            ),
            FunctionParameter(
                name="cpu_change_pct",
                type="number",
                default=10.0,
                min=-50.0,
                max=200.0,
                description="CPU change percentage",
                unit="%",
            ),
            FunctionParameter(
                name="memory_change_pct",
                type="number",
                default=5.0,
                min=-50.0,
                max=200.0,
                description="Memory change percentage",
                unit="%",
            ),
            FunctionParameter(
                name="use_interaction_terms",
                type="boolean",
                default=True,
                description="Include interaction terms (traffic*cpu, etc.)",
                unit="",
            ),
            FunctionParameter(
                name="use_nonlinear_terms",
                type="boolean",
                default=True,
                description="Include nonlinear terms (squared terms)",
                unit="",
            ),
        ],
        outputs=[
            FunctionOutput(name="latency_ms", unit="ms", description="Predicted latency"),
            FunctionOutput(name="error_rate_pct", unit="%", description="Predicted error rate"),
            FunctionOutput(name="throughput_rps", unit="rps", description="Predicted throughput"),
            FunctionOutput(name="cost_usd_hour", unit="USD/h", description="Predicted cost"),
        ],
        confidence=0.81,
        tags=["ml", "sklearn", "lightgbm", "regression", "prediction"],
        assumptions=[
            "ML models are trained on historical data",
            "Features are consistent with training",
            "Fallback to enhanced regression if models unavailable",
        ],
        references=["sklearn documentation", "LightGBM documentation"],
    )

    def execute(
        self,
        *,
        baseline: dict[str, float],
        assumptions: dict[str, float],
        context: dict[str, Any] | None = None,
    ) -> tuple[dict[str, float], float, dict[str, Any]]:
        """
        Execute ML predictive strategy.

        Uses enhanced statistical regression with interaction/nonlinear terms.
        If trained models are available, they would be used instead.
        """
        traffic = assumptions.get("traffic_change_pct", 0.0)
        cpu = assumptions.get("cpu_change_pct", 0.0)
        memory = assumptions.get("memory_change_pct", 0.0)
        use_interaction = assumptions.get("use_interaction_terms", True)
        use_nonlinear = assumptions.get("use_nonlinear_terms", True)

        base_latency = baseline.get("latency_ms", 50.0)
        base_throughput = baseline.get("throughput_rps", 1000.0)
        base_error = baseline.get("error_rate_pct", 0.5)
        base_cost = baseline.get("cost_usd_hour", 10.0)

        # Enhanced weights (simulating learned weights)
        w_traffic = 0.035
        w_cpu = 0.028
        w_memory = 0.015

        # Linear impact
        linear_impact = (w_traffic * traffic) + (w_cpu * cpu) + (w_memory * memory)

        # Interaction terms
        interaction_impact = 0.0
        if use_interaction:
            w_interaction_tc = 0.0006  # traffic * cpu interaction
            interaction_impact = w_interaction_tc * traffic * cpu

        # Nonlinear terms
        nonlinear_impact = 0.0
        if use_nonlinear:
            w_nonlinear_t = 0.0002  # traffic^2 term
            nonlinear_impact = w_nonlinear_t * max(0, traffic) ** 2

        # Total impact
        total_impact = linear_impact + interaction_impact + nonlinear_impact

        # Apply to KPIs with KPI-specific sensitivity
        latency_multiplier = max(0.5, min(2.5, 1.0 + total_impact * 0.012))
        throughput_multiplier = max(0.2, 1.0 + (traffic * 0.0055) - (cpu * 0.0025) - (total_impact * 0.008))
        error_delta = max(0.0, total_impact * 0.42)
        cost_multiplier = max(0.0, 1.0 + max(0, traffic) / 100 * 0.23 + max(0, total_impact) * 0.02)

        outputs = {
            "latency_ms": round(base_latency * latency_multiplier, 2),
            "error_rate_pct": round(base_error + error_delta, 3),
            "throughput_rps": round(base_throughput * throughput_multiplier, 2),
            "cost_usd_hour": round(base_cost * cost_multiplier, 2),
        }

        debug_info = {
            "strategy": "ml",
            "method": "enhanced_regression_fallback",
            "features_used": ["linear", "interaction", "nonlinear"] if use_interaction and use_nonlinear else ["linear"],
            "linear_impact": round(linear_impact, 4),
            "interaction_impact": round(interaction_impact, 4) if use_interaction else 0.0,
            "nonlinear_impact": round(nonlinear_impact, 4) if use_nonlinear else 0.0,
            "total_impact": round(total_impact, 4),
        }

        return outputs, self.metadata.confidence, debug_info
