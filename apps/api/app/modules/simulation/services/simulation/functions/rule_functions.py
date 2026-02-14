"""
SIM Function Library - Rule-Based Functions

Deterministic functions based on business rules, heuristics,
and domain expertise.
"""

from __future__ import annotations

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
# 1. Linear Rule Functions
# =============================================================================

class LinearWeightRule(SimulationFunction):
    """
    Standard linear weighted rule for KPI impact calculation.

    Formula: impact = Σ(weight_i * input_i)

    Use Case: Simple capacity planning, what-if scenarios
    Reference: Standard operations research practice
    """

    metadata = FunctionMetadata(
        id="rule_linear_weight",
        name="Linear Weight Rule",
        category=FunctionCategory.RULE,
        complexity=FunctionComplexity.BASIC,
        description="Calculate KPI impact using linear weighted sum of inputs",
        parameters=[
            FunctionParameter(
                name="traffic_weight",
                type="number",
                default=0.6,
                min=0.0,
                max=1.0,
                step=0.05,
                description="Weight for traffic change",
                unit="",
            ),
            FunctionParameter(
                name="cpu_weight",
                type="number",
                default=0.3,
                min=0.0,
                max=1.0,
                step=0.05,
                description="Weight for CPU change",
                unit="",
            ),
            FunctionParameter(
                name="memory_weight",
                type="number",
                default=0.2,
                min=0.0,
                max=1.0,
                step=0.05,
                description="Weight for memory change",
                unit="",
            ),
            FunctionParameter(
                name="traffic_change_pct",
                type="number",
                default=0.0,
                min=-90.0,
                max=300.0,
                step=1.0,
                description="Traffic change percentage",
                unit="%",
            ),
            FunctionParameter(
                name="cpu_change_pct",
                type="number",
                default=0.0,
                min=-90.0,
                max=300.0,
                step=1.0,
                description="CPU change percentage",
                unit="%",
            ),
            FunctionParameter(
                name="memory_change_pct",
                type="number",
                default=0.0,
                min=-90.0,
                max=300.0,
                step=1.0,
                description="Memory change percentage",
                unit="%",
            ),
            FunctionParameter(
                name="latency_sensitivity",
                type="number",
                default=0.9,
                min=0.1,
                max=2.0,
                step=0.1,
                description="Latency sensitivity to impact",
                unit="",
            ),
            FunctionParameter(
                name="error_sensitivity",
                type="number",
                default=0.015,
                min=0.001,
                max=0.1,
                step=0.001,
                description="Error rate sensitivity to impact",
                unit="",
            ),
            FunctionParameter(
                name="cost_sensitivity",
                type="number",
                default=0.2,
                min=0.0,
                max=1.0,
                step=0.05,
                description="Cost sensitivity to traffic increase",
                unit="",
            ),
        ],
        outputs=[
            FunctionOutput(name="latency_ms", unit="ms", description="Response latency"),
            FunctionOutput(name="error_rate_pct", unit="%", description="Error rate"),
            FunctionOutput(name="throughput_rps", unit="rps", description="Request throughput"),
            FunctionOutput(name="cost_usd_hour", unit="USD/h", description="Hourly cost"),
        ],
        confidence=0.72,
        tags=["linear", "basic", "capacity", "what-if"],
        assumptions=[
            "Linear relationship between inputs and outputs",
            "No interaction effects between variables",
            "Constant sensitivity coefficients",
        ],
        references=["Operations Research: Applications and Algorithms"],
    )

    def execute(
        self,
        *,
        baseline: dict[str, float],
        assumptions: dict[str, float],
        context: dict[str, Any] | None = None,
    ) -> tuple[dict[str, float], float, dict[str, Any]]:
        _ = context

        # Extract weights
        w_traffic = assumptions.get("traffic_weight", self.metadata.parameters[0].default)
        w_cpu = assumptions.get("cpu_weight", self.metadata.parameters[1].default)
        w_memory = assumptions.get("memory_weight", self.metadata.parameters[2].default)

        # Extract inputs
        traffic = assumptions.get("traffic_change_pct", 0.0)
        cpu = assumptions.get("cpu_change_pct", 0.0)
        memory = assumptions.get("memory_change_pct", 0.0)

        # Extract sensitivities
        lat_sens = assumptions.get("latency_sensitivity", 0.9)
        err_sens = assumptions.get("error_sensitivity", 0.015)
        cost_sens = assumptions.get("cost_sensitivity", 0.2)

        # Calculate weighted impact
        impact = (w_traffic * traffic) + (w_cpu * cpu) + (w_memory * memory)

        # Apply to KPIs
        baseline_latency = baseline.get("latency_ms", 50.0)
        baseline_error = baseline.get("error_rate_pct", 0.1)
        baseline_throughput = baseline.get("throughput_rps", 1000.0)
        baseline_cost = baseline.get("cost_usd_hour", 10.0)

        outputs = {
            "latency_ms": round(baseline_latency * (1.0 + max(-60.0, impact) / 100.0 * lat_sens), 2),
            "error_rate_pct": round(max(0.0, baseline_error + max(0.0, impact) * err_sens), 3),
            "throughput_rps": round(max(1.0, baseline_throughput * (1.0 + traffic / 100.0 * 0.8 - cpu / 100.0 * 0.15)), 2),
            "cost_usd_hour": round(baseline_cost * (1.0 + max(0.0, traffic) / 100.0 * cost_sens), 2),
        }

        debug_info = {
            "impact": round(impact, 2),
            "weights": {"traffic": w_traffic, "cpu": w_cpu, "memory": w_memory},
            "formula": "impact = traffic_w * traffic + cpu_w * cpu + mem_w * memory",
        }

        return outputs, self.metadata.confidence, debug_info


class PolynomialRule(SimulationFunction):
    """
    Polynomial rule for non-linear relationships.

    Formula: impact = a*x² + b*x + c

    Use Case: Diminishing returns, accelerating degradation
    Reference: Non-linear optimization theory
    """

    metadata = FunctionMetadata(
        id="rule_polynomial",
        name="Polynomial Rule",
        category=FunctionCategory.RULE,
        complexity=FunctionComplexity.INTERMEDIATE,
        description="Non-linear polynomial relationship for complex scenarios",
        parameters=[
            FunctionParameter(
                name="x",
                type="number",
                default=0.0,
                min=-100.0,
                max=200.0,
                description="Primary input variable (e.g., traffic change)",
                unit="%",
            ),
            FunctionParameter(
                name="quadratic_coeff",
                type="number",
                default=0.002,
                min=-0.01,
                max=0.01,
                step=0.0001,
                description="Quadratic coefficient (x² term)",
                unit="",
            ),
            FunctionParameter(
                name="linear_coeff",
                type="number",
                default=0.8,
                min=-2.0,
                max=2.0,
                step=0.1,
                description="Linear coefficient (x term)",
                unit="",
            ),
            FunctionParameter(
                name="intercept",
                type="number",
                default=0.0,
                min=-10.0,
                max=10.0,
                description="Constant term",
                unit="",
            ),
            FunctionParameter(
                name="baseline_kpi",
                type="string",
                default="latency_ms",
                description="Which baseline KPI to apply the multiplier to",
                unit="",
            ),
        ],
        outputs=[
            FunctionOutput(name="simulated_value", unit="varies", description="Simulated KPI value"),
        ],
        confidence=0.75,
        tags=["polynomial", "non-linear", "diminishing-returns"],
        assumptions=[
            "Polynomial relationship fits the phenomenon",
            "Coefficients are properly calibrated",
        ],
        references=["Non-linear Programming", "Response Surface Methodology"],
    )

    def execute(
        self,
        *,
        baseline: dict[str, float],
        assumptions: dict[str, float],
        context: dict[str, Any] | None = None,
    ) -> tuple[dict[str, float], float, dict[str, Any]]:
        _ = context

        x = assumptions.get("x", 0.0)
        a = assumptions.get("quadratic_coeff", self.metadata.parameters[1].default)
        b = assumptions.get("linear_coeff", self.metadata.parameters[2].default)
        c = assumptions.get("intercept", self.metadata.parameters[3].default)
        kpi_name = assumptions.get("baseline_kpi", "latency_ms")

        baseline_value = baseline.get(kpi_name, 50.0)

        # Polynomial: a*x² + b*x + c
        impact_pct = (a * x * x) + (b * x) + c
        multiplier = max(0.1, 1.0 + impact_pct / 100.0)

        outputs = {
            "simulated_value": round(baseline_value * multiplier, 2),
        }

        debug_info = {
            "polynomial_value": round(impact_pct, 3),
            "multiplier": round(multiplier, 3),
            "formula": f"{a}*x² + {b}*x + {c}",
            "kpi": kpi_name,
        }

        return outputs, self.metadata.confidence, debug_info


# =============================================================================
# 2. Threshold Rule Functions
# =============================================================================

class ThresholdRule(SimulationFunction):
    """
    Step/threshold function with discrete states.

    Formula: output = {
        baseline * normal_factor if x < threshold_low
        baseline * warning_factor if threshold_low <= x < threshold_high
        baseline * critical_factor if x >= threshold_high
    }

    Use Case: SLA breaches, capacity limits, alert thresholds
    Reference: Control theory, SLA management
    """

    metadata = FunctionMetadata(
        id="rule_threshold",
        name="Threshold Rule",
        category=FunctionCategory.RULE,
        complexity=FunctionComplexity.BASIC,
        description="Discrete step function based on threshold values",
        parameters=[
            FunctionParameter(
                name="input_value",
                type="number",
                default=50.0,
                min=0.0,
                max=200.0,
                description="Input value to check against thresholds",
                unit="%",
            ),
            FunctionParameter(
                name="warning_threshold",
                type="number",
                default=70.0,
                min=0.0,
                max=100.0,
                description="Warning threshold",
                unit="%",
            ),
            FunctionParameter(
                name="critical_threshold",
                type="number",
                default=90.0,
                min=0.0,
                max=100.0,
                description="Critical threshold",
                unit="%",
            ),
            FunctionParameter(
                name="normal_multiplier",
                type="number",
                default=1.0,
                min=0.5,
                max=1.5,
                step=0.05,
                description="KPI multiplier in normal state",
                unit="",
            ),
            FunctionParameter(
                name="warning_multiplier",
                type="number",
                default=1.5,
                min=1.0,
                max=3.0,
                step=0.1,
                description="KPI multiplier in warning state",
                unit="",
            ),
            FunctionParameter(
                name="critical_multiplier",
                type="number",
                default=3.0,
                min=1.5,
                max=10.0,
                step=0.5,
                description="KPI multiplier in critical state",
                unit="",
            ),
            FunctionParameter(
                name="baseline_kpi",
                type="string",
                default="latency_ms",
                description="Which baseline KPI to apply thresholds to",
                unit="",
            ),
        ],
        outputs=[
            FunctionOutput(name="simulated_value", unit="varies", description="Simulated KPI value"),
            FunctionOutput(name="state", unit="", description="Current state (normal/warning/critical)"),
        ],
        confidence=0.80,
        tags=["threshold", "step-function", "sla", "alerting"],
        assumptions=[
            "Discrete states are appropriate for the phenomenon",
            "Threshold values are well-calibrated",
        ],
        references=["SLA Management Best Practices", "Control Theory"],
    )

    def execute(
        self,
        *,
        baseline: dict[str, float],
        assumptions: dict[str, float],
        context: dict[str, Any] | None = None,
    ) -> tuple[dict[str, float], float, dict[str, Any]]:
        _ = context

        x = assumptions.get("input_value", 50.0)
        warn_thr = assumptions.get("warning_threshold", 70.0)
        crit_thr = assumptions.get("critical_threshold", 90.0)
        norm_mult = assumptions.get("normal_multiplier", 1.0)
        warn_mult = assumptions.get("warning_multiplier", 1.5)
        crit_mult = assumptions.get("critical_multiplier", 3.0)
        kpi_name = assumptions.get("baseline_kpi", "latency_ms")

        baseline_value = baseline.get(kpi_name, 50.0)

        if x < warn_thr:
            state = "normal"
            multiplier = norm_mult
        elif x < crit_thr:
            state = "warning"
            multiplier = warn_mult
        else:
            state = "critical"
            multiplier = crit_mult

        outputs = {
            "simulated_value": round(baseline_value * multiplier, 2),
            "state": 1.0 if state == "normal" else (2.0 if state == "warning" else 3.0),
        }

        debug_info = {
            "state": state,
            "multiplier": multiplier,
            "threshold_crossed": x >= warn_thr,
        }

        return outputs, self.metadata.confidence, debug_info


# =============================================================================
# 3. Domain-Specific Rule Functions
# =============================================================================

class LittleLawRule(SimulationFunction):
    """
    Little's Law for queueing systems.

    Formula: L = λ * W
    - L: Average number of items in system
    - λ: Average arrival rate
    - W: Average time in system

    Use Case: Queue length prediction, response time estimation
    Reference: Little, J.D.C. (1961). "A Proof for the Queuing Formula: L = λW"
    """

    metadata = FunctionMetadata(
        id="rule_little_law",
        name="Little's Law",
        category=FunctionCategory.DOMAIN,
        complexity=FunctionComplexity.BASIC,
        description="Fundamental queueing theory relationship",
        parameters=[
            FunctionParameter(
                name="arrival_rate_change_pct",
                type="number",
                default=0.0,
                min=-50.0,
                max=200.0,
                description="Change in arrival rate (traffic)",
                unit="%",
            ),
            FunctionParameter(
                name="service_time_change_pct",
                type="number",
                default=0.0,
                min=-50.0,
                max=200.0,
                description="Change in service time (latency)",
                unit="%",
            ),
        ],
        outputs=[
            FunctionOutput(name="latency_ms", unit="ms", description="Response time"),
            FunctionOutput(name="queue_length", unit="items", description="Average queue length"),
            FunctionOutput(name="throughput_rps", unit="rps", description="Throughput"),
        ],
        confidence=0.85,
        tags=["queueing", "fundamental", "little-law", "performance"],
        assumptions=[
            "System is stable (arrival rate < service rate)",
            "Steady-state conditions",
            "Average values apply",
        ],
        references=["Little, J.D.C. (1961). Operations Research"],
    )

    def execute(
        self,
        *,
        baseline: dict[str, float],
        assumptions: dict[str, float],
        context: dict[str, Any] | None = None,
    ) -> tuple[dict[str, float], float, dict[str, Any]]:
        _ = context

        arrival_change = assumptions.get("arrival_rate_change_pct", 0.0)
        service_change = assumptions.get("service_time_change_pct", 0.0)

        base_latency = baseline.get("latency_ms", 50.0)
        base_throughput = baseline.get("throughput_rps", 1000.0)

        # Little's Law: L = λ * W
        # If arrival rate increases by x%, and service time increases by y%:
        # New L = (λ * (1+x/100)) * (W * (1+y/100))
        # New W = L / λ = W * (1+y/100) * (1+x/100) / (1+x/100) = W * (1+y/100) when stable

        arrival_multiplier = 1.0 + arrival_change / 100.0
        service_multiplier = 1.0 + service_change / 100.0

        new_latency = base_latency * service_multiplier
        new_throughput = base_throughput * arrival_multiplier
        new_queue_length = new_throughput * new_latency / 1000.0

        outputs = {
            "latency_ms": round(new_latency, 2),
            "queue_length": round(new_queue_length, 2),
            "throughput_rps": round(new_throughput, 2),
        }

        debug_info = {
            "formula": "L = λ * W",
            "arrival_multiplier": round(arrival_multiplier, 3),
            "service_multiplier": round(service_multiplier, 3),
        }

        return outputs, self.metadata.confidence, debug_info


class ErlangCRule(SimulationFunction):
    """
    Erlang C formula for call center/service capacity planning.

    Formula: Probability that a customer has to wait for service

    Use Case: Staffing, capacity planning, SLA compliance
    Reference: Erlang, A.K. (1917)
    """

    metadata = FunctionMetadata(
        id="rule_erlang_c",
        name="Erlang C",
        category=FunctionCategory.DOMAIN,
        complexity=FunctionComplexity.INTERMEDIATE,
        description="Erlang C formula for service system capacity",
        parameters=[
            FunctionParameter(
                name="traffic_intensity",
                type="number",
                default=15.0,
                min=1.0,
                max=100.0,
                description="Traffic intensity (arrival rate * service time)",
                unit="Erlangs",
            ),
            FunctionParameter(
                name="num_servers",
                type="integer",
                default=20,
                min=1,
                max=200,
                description="Number of parallel servers/agents",
                unit="",
            ),
            FunctionParameter(
                name="target_service_level",
                type="number",
                default=0.8,
                min=0.5,
                max=0.99,
                step=0.05,
                description="Target service level (probability)",
                unit="",
            ),
        ],
        outputs=[
            FunctionOutput(name="probability_wait", unit="%", description="Probability of waiting"),
            FunctionOutput(name="avg_wait_time", unit="s", description="Average wait time"),
            FunctionOutput(name="service_level", unit="%", description="Actual service level"),
            FunctionOutput(name="utilization", unit="%", description="Server utilization"),
        ],
        confidence=0.88,
        tags=["capacity", "erlang", "staffing", "queueing"],
        assumptions=[
            "Poisson arrival process",
            "Exponential service times",
            "FCFS queue discipline",
            "Infinite queue capacity",
        ],
        references=["Erlang, A.K. (1917). Solution of some Problems in the Theory of Probabilities"],
    )

    def execute(
        self,
        *,
        baseline: dict[str, float],
        assumptions: dict[str, float],
        context: dict[str, Any] | None = None,
    ) -> tuple[dict[str, float], float, dict[str, Any]]:
        import math

        _ = context
        _ = baseline

        A = assumptions.get("traffic_intensity", 15.0)  # Traffic in Erlangs
        m = int(assumptions.get("num_servers", 20))  # Number of servers

        # Simplified Erlang C calculation
        # P(Wait) = ( (A^m / m!) * (m / (m - A)) ) / ( Σ (A^k / k!) + (A^m / m!) * (m / (m - A)) )

        if A >= m:
            # System is unstable (overloaded)
            return {
                "probability_wait": 100.0,
                "avg_wait_time": float("inf"),
                "service_level": 0.0,
                "utilization": 100.0,
            }, 0.0, {"error": "System overloaded (traffic >= servers)"}

        # Calculate Erlang C
        def erlang_c(traffic: float, servers: int) -> float:
            # Simplified approximation
            rho = traffic / servers
            if rho >= 1.0:
                return 1.0

            # Use approximation formula
            numerator = (traffic ** servers) / math.factorial(servers) * (servers / (servers - traffic))
            denominator = numerator
            for k in range(servers):
                denominator += (traffic ** k) / math.factorial(k)

            return numerator / denominator if denominator > 0 else 0.0

        p_wait = erlang_c(A, m)
        avg_service_time = 1.0  # Normalized service time
        avg_wait = p_wait * (avg_service_time / (m - A))

        utilization = (A / m) * 100

        outputs = {
            "probability_wait": round(p_wait * 100, 2),
            "avg_wait_time": round(avg_wait * 60, 2),  # Convert to conceptual units
            "service_level": round((1 - p_wait) * 100, 2),
            "utilization": round(utilization, 2),
        }

        debug_info = {
            "traffic_erlangs": A,
            "servers": m,
            "formula": "Erlang C formula",
        }

        return outputs, self.metadata.confidence, debug_info
