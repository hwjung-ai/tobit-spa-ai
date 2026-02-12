"""
SIM Function Library - Domain-Specific Functions

Functions for specific domains: performance, reliability, cost, security.
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
# 1. Performance Domain Functions
# =============================================================================

class ResponseTimeDecomposition(SimulationFunction):
    """
    Response time decomposition: R = S + W + Q

    - S: Service time (processing)
    - W: Waiting time (queue)
    - Q: Network time

    Use Case: Performance bottleneck identification
    Reference: Queueing theory, service level management
    """

    metadata = FunctionMetadata(
        id="domain_response_time_decomp",
        name="Response Time Decomposition",
        category=FunctionCategory.DOMAIN,
        complexity=FunctionComplexity.BASIC,
        description="Decompose response time into components",
        parameters=[
            FunctionParameter(
                name="service_time_ms",
                type="number",
                default=20.0,
                min=1.0,
                max=500.0,
                description="Base service/processing time",
                unit="ms",
            ),
            FunctionParameter(
                name="queue_depth",
                type="number",
                default=5.0,
                min=0.0,
                max=100.0,
                description="Average queue depth",
                unit="items",
            ),
            FunctionParameter(
                name="service_rate_per_ms",
                type="number",
                default=0.05,
                min=0.001,
                max=1.0,
                step=0.001,
                description="Service rate (items/ms)",
                unit="items/ms",
            ),
            FunctionParameter(
                name="network_latency_ms",
                type="number",
                default=10.0,
                min=0.0,
                max=200.0,
                description="Base network latency",
                unit="ms",
            ),
            FunctionParameter(
                name="network_congestion_pct",
                type="number",
                default=0.0,
                min=0.0,
                max=100.0,
                description="Network congestion percentage",
                unit="%",
            ),
        ],
        outputs=[
            FunctionOutput(name="total_response_time", unit="ms", description="Total response time"),
            FunctionOutput(name="service_component", unit="ms", description="Service time component"),
            FunctionOutput(name="queue_component", unit="ms", description="Queue waiting component"),
            FunctionOutput(name="network_component", unit="ms", description="Network component"),
        ],
        confidence=0.85,
        tags=["performance", "response-time", "bottleneck", "decomposition"],
        assumptions=[
            "M/M/1 queue approximation",
            "Linear congestion impact",
        ],
        references=["Queueing Theory: Basic Concepts and Applications"],
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

        service_time = assumptions.get("service_time_ms", 20.0)
        queue_depth = assumptions.get("queue_depth", 5.0)
        service_rate = assumptions.get("service_rate_per_ms", 0.05)
        network_base = assumptions.get("network_latency_ms", 10.0)
        congestion = assumptions.get("network_congestion_pct", 0.0)

        # Queue waiting time: W = L / λ = queue_depth / service_rate
        queue_time = queue_depth / service_rate if service_rate > 0 else 0

        # Network time with congestion
        network_time = network_base * (1 + congestion / 100.0)

        # Total response time
        total = service_time + queue_time + network_time

        outputs = {
            "total_response_time": round(total, 2),
            "service_component": round(service_time, 2),
            "queue_component": round(queue_time, 2),
            "network_component": round(network_time, 2),
        }

        debug_info = {
            "formula": "R = S + W + Q",
            "bottleneck": "queue" if queue_time > service_time else ("network" if network_time > service_time else "service"),
        }

        return outputs, self.metadata.confidence, debug_info


class UtilizationImpact(SimulationFunction):
    """
    Utilization-based performance impact.

    Formula: As utilization → 100%, response time → ∞

    Use Case: Capacity planning, scaling decisions
    Reference: Kingman's formula for G/G/1 queue
    """

    metadata = FunctionMetadata(
        id="domain_utilization_impact",
        name="Utilization Impact",
        category=FunctionCategory.DOMAIN,
        complexity=FunctionComplexity.INTERMEDIATE,
        description="Model response time degradation as utilization increases",
        parameters=[
            FunctionParameter(
                name="utilization_pct",
                type="number",
                default=70.0,
                min=10.0,
                max=99.0,
                description="Current utilization",
                unit="%",
            ),
            FunctionParameter(
                name="base_response_time_ms",
                type="number",
                default=50.0,
                min=1.0,
                max=1000.0,
                description="Base response time at low utilization",
                unit="ms",
            ),
            FunctionParameter(
                name="cv_arrival",
                type="number",
                default=1.0,
                min=0.1,
                max=3.0,
                step=0.1,
                description="Coefficient of variation of arrivals",
                unit="",
            ),
            FunctionParameter(
                name="cv_service",
                type="number",
                default=1.0,
                min=0.1,
                max=3.0,
                step=0.1,
                description="Coefficient of variation of service time",
                unit="",
            ),
        ],
        outputs=[
            FunctionOutput(name="response_time_ms", unit="ms", description="Expected response time"),
            FunctionOutput(name="waiting_time_ms", unit="ms", description="Expected waiting time"),
            FunctionOutput(name="degradation_factor", unit="", description="Response time multiplier"),
        ],
        confidence=0.83,
        tags=["utilization", "capacity", "kingman", "queueing"],
        assumptions=[
            "G/G/1 queue approximation",
            "Steady state conditions",
        ],
        references=["Kingman, J.F.C. (1961). The single server queue with Poisson arrivals"],
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

        util = assumptions.get("utilization_pct", 70.0) / 100.0
        base_rt = assumptions.get("base_response_time_ms", 50.0)
        cv_a = assumptions.get("cv_arrival", 1.0)
        cv_s = assumptions.get("cv_service", 1.0)

        if util >= 0.99:
            return {
                "response_time_ms": float("inf"),
                "waiting_time_ms": float("inf"),
                "degradation_factor": 999.99,
            }, 0.0, {"error": "System saturated"}

        # Kingman's formula approximation for G/G/1 waiting time
        # E[W] = (λ * (σ_a² + σ_s²)) / (2 * (1 - ρ))
        # Simplified using CVs
        ca_sq = cv_a ** 2
        cs_sq = cv_s ** 2

        waiting_time = base_rt * (util / (1 - util)) * ((ca_sq + cs_sq) / 2)
        response_time = base_rt + waiting_time
        degradation = response_time / base_rt if base_rt > 0 else 1.0

        outputs = {
            "response_time_ms": round(response_time, 2),
            "waiting_time_ms": round(waiting_time, 2),
            "degradation_factor": round(degradation, 2),
        }

        debug_info = {
            "utilization": round(util * 100, 1),
            "kingman_approximation": True,
            "warning": "High degradation" if degradation > 3 else "Normal",
        }

        return outputs, self.metadata.confidence, debug_info


# =============================================================================
# 2. Reliability Domain Functions
# =============================================================================

class AvailabilityModel(SimulationFunction):
    """
    Availability model: A = MTBF / (MTBF + MTTR)

    - MTBF: Mean Time Between Failures
    - MTTR: Mean Time To Repair

    Use Case: SLA compliance, redundancy planning
    Reference: ITIL, Reliability Engineering
    """

    metadata = FunctionMetadata(
        id="domain_availability",
        name="Availability Model",
        category=FunctionCategory.DOMAIN,
        complexity=FunctionComplexity.BASIC,
        description="Calculate availability from MTBF and MTTR",
        parameters=[
            FunctionParameter(
                name="mtbf_hours",
                type="number",
                default=720.0,
                min=1.0,
                max=87600.0,
                description="Mean Time Between Failures (hours)",
                unit="hours",
            ),
            FunctionParameter(
                name="mttr_hours",
                type="number",
                default=4.0,
                min=0.1,
                max=168.0,
                description="Mean Time To Repair (hours)",
                unit="hours",
            ),
            FunctionParameter(
                name="redundancy_factor",
                type="number",
                default=1.0,
                min=1.0,
                max=10.0,
                step=0.5,
                description="Redundancy multiplier for MTBF",
                unit="",
            ),
        ],
        outputs=[
            FunctionOutput(name="availability_pct", unit="%", description="Availability percentage"),
            FunctionOutput(name="downtime_minutes_per_month", unit="min", description="Expected monthly downtime"),
            FunctionOutput(name="sla_class", unit="", description="SLA tier (1-9)"),
        ],
        confidence=0.90,
        tags=["availability", "sla", "mtbf", "mttr", "reliability"],
        assumptions=[
            "Exponential failure distribution",
            "Constant repair rate",
        ],
        references=["ITIL Service Design", "Reliability Engineering Handbook"],
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

        mtbf = assumptions.get("mtbf_hours", 720.0)
        mttr = assumptions.get("mttr_hours", 4.0)
        redundancy = assumptions.get("redundancy_factor", 1.0)

        # Effective MTBF with redundancy
        effective_mtbf = mtbf * redundancy

        # Availability: A = MTBF / (MTBF + MTTR)
        availability = effective_mtbf / (effective_mtbf + mttr)

        # Downtime per month (720 hours in 30 days)
        downtime_hours = 720 * (1 - availability)
        downtime_minutes = downtime_hours * 60

        # SLA class (number of 9s)
        if availability >= 0.99999:
            sla_class = 5  # 99.999%
        elif availability >= 0.9999:
            sla_class = 4  # 99.99%
        elif availability >= 0.999:
            sla_class = 3  # 99.9%
        elif availability >= 0.99:
            sla_class = 2  # 99%
        elif availability >= 0.95:
            sla_class = 1  # 95%
        else:
            sla_class = 0  # < 95%

        outputs = {
            "availability_pct": round(availability * 100, 4),
            "downtime_minutes_per_month": round(downtime_minutes, 2),
            "sla_class": float(sla_class),
        }

        debug_info = {
            "mtbf": effective_mtbf,
            "mttr": mttr,
            "formula": "A = MTBF / (MTBF + MTTR)",
            "nines": round(-math.log10(1 - availability), 2) if availability < 1 else 5,
        }

        return outputs, self.metadata.confidence, debug_info


class FailureCascading(SimulationFunction):
    """
    Model failure cascading in dependent systems.

    Formula: P(system fails) = 1 - Π(1 - P(component_i fails))

    Use Case: Dependency impact analysis, single point of failure
    Reference: Reliability block diagrams
    """

    metadata = FunctionMetadata(
        id="domain_failure_cascading",
        name="Failure Cascading Model",
        category=FunctionCategory.DOMAIN,
        complexity=FunctionComplexity.INTERMEDIATE,
        description="Model cascading failures in dependent components",
        parameters=[
            FunctionParameter(
                name="component_failure_probs",
                type="array",
                default=[0.01, 0.02, 0.005, 0.01],
                description="Individual component failure probabilities",
                unit="",
            ),
            FunctionParameter(
                name="dependency_matrix",
                type="array",
                default=[[1, 1, 0, 0], [0, 1, 1, 0], [0, 0, 1, 1], [0, 0, 0, 1]],
                description="Adjacency matrix (component_i depends on component_j if 1)",
                unit="",
            ),
            FunctionParameter(
                name="cascade_probability",
                type="number",
                default=0.3,
                min=0.0,
                max=1.0,
                step=0.05,
                description="Probability of failure propagating",
                unit="",
            ),
        ],
        outputs=[
            FunctionOutput(name="system_failure_prob", unit="%", description="System failure probability"),
            FunctionOutput(name="expected_failures", unit="components", description="Expected number of failed components"),
            FunctionOutput(name="cascade_depth", unit="steps", description="Maximum cascade depth"),
        ],
        confidence=0.78,
        tags=["reliability", "cascade", "dependencies", "fault-tolerance"],
        assumptions=[
            "Independent component failures",
            "Fixed cascade probability",
        ],
        references=["Complex Systems Reliability", "Cascading Failures in Networks"],
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

        fail_probs = assumptions.get("component_failure_probs", [0.01, 0.02, 0.005, 0.01])
        dep_matrix = assumptions.get("dependency_matrix", [[1, 1, 0, 0], [0, 1, 1, 0], [0, 0, 1, 1], [0, 0, 0, 1]])
        cascade_prob = assumptions.get("cascade_probability", 0.3)

        n = len(fail_probs)

        # Simplified cascade simulation
        # Initial failures
        failed = [i for i, p in enumerate(fail_probs) if hash(str(p)) % 1000 < p * 1000]

        # Propagate failures
        for step in range(n):
            new_failures = []
            for i in range(n):
                if i not in failed:
                    # Check if any dependency failed
                    for j in range(n):
                        if j in failed and dep_matrix[i][j] == 1:
                            if (hash(str(i) + str(j) + str(step)) % 1000) < cascade_prob * 1000:
                                new_failures.append(i)
                                break
            failed.extend(new_failures)
            if not new_failures:
                break

        # Calculate system failure probability (series system)
        system_fail_prob = 1 - math.prod([1 - p for p in fail_probs])

        outputs = {
            "system_failure_prob": round(system_fail_prob * 100, 3),
            "expected_failures": float(len(failed)),
            "cascade_depth": float(len(set(failed))),
        }

        debug_info = {
            "num_components": n,
            "initial_failures": len([p for p in fail_probs if p > 0]),
            "cascade_probability": cascade_prob,
            "formula": "P(system fails) = 1 - Π(1 - P(component_i fails))",
        }

        return outputs, self.metadata.confidence, debug_info


# =============================================================================
# 3. Cost Domain Functions
# =============================================================================

class CloudCostModel(SimulationFunction):
    """
    Cloud infrastructure cost model.

    Formula: Cost = Compute + Storage + Network + Premium Services

    Use Case: Cloud cost estimation, budget planning
    Reference: Major cloud providers pricing models
    """

    metadata = FunctionMetadata(
        id="domain_cloud_cost",
        name="Cloud Cost Model",
        category=FunctionCategory.DOMAIN,
        complexity=FunctionComplexity.BASIC,
        description="Estimate cloud infrastructure costs",
        parameters=[
            FunctionParameter(
                name="compute_instances",
                type="integer",
                default=10,
                min=1,
                max=1000,
                description="Number of compute instances",
                unit="",
            ),
            FunctionParameter(
                name="instance_cost_per_hour",
                type="number",
                default=0.15,
                min=0.01,
                max=10.0,
                step=0.01,
                description="Cost per instance per hour",
                unit="USD/h",
            ),
            FunctionParameter(
                name="storage_gb",
                type="number",
                default=1000.0,
                min=0.0,
                max=1000000.0,
                description="Storage in GB",
                unit="GB",
            ),
            FunctionParameter(
                name="storage_cost_per_gb_month",
                type="number",
                default=0.02,
                min=0.001,
                max=1.0,
                step=0.001,
                description="Storage cost per GB per month",
                unit="USD/GB/month",
            ),
            FunctionParameter(
                name="network_gb_per_month",
                type="number",
                default=5000.0,
                min=0.0,
                max=1000000.0,
                description="Network transfer per month",
                unit="GB/month",
            ),
            FunctionParameter(
                name="network_cost_per_gb",
                type="number",
                default=0.01,
                min=0.001,
                max=1.0,
                step=0.001,
                description="Network cost per GB",
                unit="USD/GB",
            ),
            FunctionParameter(
                name="hours_per_month",
                type="number",
                default=730.0,
                min=1.0,
                max=744.0,
                description="Hours in billing month",
                unit="hours",
            ),
        ],
        outputs=[
            FunctionOutput(name="monthly_cost_usd", unit="USD", description="Total monthly cost"),
            FunctionOutput(name="compute_cost", unit="USD", description="Compute cost component"),
            FunctionOutput(name="storage_cost", unit="USD", description="Storage cost component"),
            FunctionOutput(name="network_cost", unit="USD", description="Network cost component"),
        ],
        confidence=0.88,
        tags=["cost", "cloud", "budget", "infrastructure"],
        assumptions=[
            "Fixed pricing tiers",
            "No reserved instances",
            "On-demand pricing",
        ],
        references=["AWS/Azure/GCP Pricing Documentation"],
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

        instances = int(assumptions.get("compute_instances", 10))
        instance_cost = assumptions.get("instance_cost_per_hour", 0.15)
        storage_gb = assumptions.get("storage_gb", 1000.0)
        storage_cost = assumptions.get("storage_cost_per_gb_month", 0.02)
        network_gb = assumptions.get("network_gb_per_month", 5000.0)
        network_cost = assumptions.get("network_cost_per_gb", 0.01)
        hours = assumptions.get("hours_per_month", 730.0)

        # Calculate components
        compute_cost_month = instances * instance_cost * hours
        storage_cost_month = storage_gb * storage_cost
        network_cost_month = network_gb * network_cost
        total_monthly = compute_cost_month + storage_cost_month + network_cost_month

        outputs = {
            "monthly_cost_usd": round(total_monthly, 2),
            "compute_cost": round(compute_cost_month, 2),
            "storage_cost": round(storage_cost_month, 2),
            "network_cost": round(network_cost_month, 2),
        }

        debug_info = {
            "instances": instances,
            "total_gb": storage_gb + network_gb,
            "cost_breakdown_pct": {
                "compute": round(compute_cost_month / total_monthly * 100, 1) if total_monthly > 0 else 0,
                "storage": round(storage_cost_month / total_monthly * 100, 1) if total_monthly > 0 else 0,
                "network": round(network_cost_month / total_monthly * 100, 1) if total_monthly > 0 else 0,
            },
        }

        return outputs, self.metadata.confidence, debug_info


class TCOCalculator(SimulationFunction):
    """
    Total Cost of Ownership (TCO) calculator.

    Formula: TCO = CAPEX + OPEX

    Use Case: Investment decisions, make vs buy analysis
    Reference: TCO analysis frameworks
    """

    metadata = FunctionMetadata(
        id="domain_tco",
        name="TCO Calculator",
        category=FunctionCategory.DOMAIN,
        complexity=FunctionComplexity.INTERMEDIATE,
        description="Calculate Total Cost of Ownership",
        parameters=[
            FunctionParameter(
                name="initial_investment",
                type="number",
                default=100000.0,
                min=0.0,
                max=10000000.0,
                description="Initial CAPEX (hardware, licenses)",
                unit="USD",
            ),
            FunctionParameter(
                name="annual_operational_cost",
                type="number",
                default=20000.0,
                min=0.0,
                max=1000000.0,
                description="Annual OPEX (maintenance, support)",
                unit="USD/year",
            ),
            FunctionParameter(
                name="analysis_period_years",
                type="integer",
                default=3,
                min=1,
                max=10,
                description="Analysis period in years",
                unit="years",
            ),
            FunctionParameter(
                name="annual_inflation_rate",
                type="number",
                default=0.03,
                min=0.0,
                max=0.2,
                step=0.005,
                description="Annual cost inflation rate",
                unit="",
            ),
            FunctionParameter(
                name="discount_rate",
                type="number",
                default=0.08,
                min=0.0,
                max=0.3,
                step=0.005,
                description="Discount rate for NPV calculation",
                unit="",
            ),
        ],
        outputs=[
            FunctionOutput(name="total_tco", unit="USD", description="Total TCO over period"),
            FunctionOutput(name="npv", unit="USD", description="Net Present Value"),
            FunctionOutput(name="annualized_tco", unit="USD/year", description="Annualized TCO"),
            FunctionOutput(name="capex_pct", unit="%", description="CAPEX percentage of TCO"),
        ],
        confidence=0.85,
        tags=["tco", "financial", "investment", "npv"],
        assumptions=[
            "Constant inflation rate",
            "End-of-period cash flows",
        ],
        references=["IT Financial Management Association (ITFMA)"],
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

        capex = assumptions.get("initial_investment", 100000.0)
        annual_opex = assumptions.get("annual_operational_cost", 20000.0)
        years = int(assumptions.get("analysis_period_years", 3))
        inflation = assumptions.get("annual_inflation_rate", 0.03)
        discount_rate = assumptions.get("discount_rate", 0.08)

        # Calculate NPV of OPEX with inflation
        npv_opex = 0
        for year in range(1, years + 1):
            inflated_opex = annual_opex * ((1 + inflation) ** year)
            pv = inflated_opex / ((1 + discount_rate) ** year)
            npv_opex += pv

        # Total TCO (nominal, not discounted)
        total_opex_nominal = sum([annual_opex * ((1 + inflation) ** y) for y in range(1, years + 1)])
        total_tco = capex + total_opex_nominal

        # NPV
        npv = -capex - npv_opex  # Negative because it's a cost

        # Annualized TCO
        annualized = total_tco / years if years > 0 else total_tco

        outputs = {
            "total_tco": round(total_tco, 2),
            "npv": round(npv, 2),
            "annualized_tco": round(annualized, 2),
            "capex_pct": round(capex / total_tco * 100, 1) if total_tco > 0 else 0,
        }

        debug_info = {
            "capex": capex,
            "total_opex": round(total_opex_nominal, 2),
            "npv_opex": round(npv_opex, 2),
            "formula": "TCO = CAPEX + Σ(OPEX * (1 + inflation)^t)",
        }

        return outputs, self.metadata.confidence, debug_info


# =============================================================================
# 4. Capacity Domain Functions
# =============================================================================

class CapacityPlanning(SimulationFunction):
    """
    Capacity planning with growth projection.

    Formula: Future Capacity = Current * (1 + growth_rate)^periods

    Use Case: Resource planning, budget forecasting
    Reference: Capacity planning best practices
    """

    metadata = FunctionMetadata(
        id="domain_capacity_planning",
        name="Capacity Planning",
        category=FunctionCategory.DOMAIN,
        complexity=FunctionComplexity.BASIC,
        description="Project future capacity requirements",
        parameters=[
            FunctionParameter(
                name="current_capacity_units",
                type="number",
                default=1000.0,
                min=1.0,
                max=1000000.0,
                description="Current capacity (CPU cores, GB, etc.)",
                unit="units",
            ),
            FunctionParameter(
                name="growth_rate_pct",
                type="number",
                default=20.0,
                min=-10.0,
                max=200.0,
                description="Expected growth rate per period",
                unit="%",
            ),
            FunctionParameter(
                name="num_periods",
                type="integer",
                default=12,
                min=1,
                max=60,
                description="Number of periods to forecast",
                unit="",
            ),
            FunctionParameter(
                name="safety_margin_pct",
                type="number",
                default=20.0,
                min=0.0,
                max=100.0,
                description="Safety buffer above projected need",
                unit="%",
            ),
        ],
        outputs=[
            FunctionOutput(name="projected_capacity", unit="units", description="Projected capacity needed"),
            FunctionOutput(name="recommended_capacity", unit="units", description="Capacity with safety margin"),
            FunctionOutput(name="additional_needed", unit="units", description="Additional capacity required"),
            FunctionOutput(name="compound_growth_factor", unit="", description="Total growth multiplier"),
        ],
        confidence=0.82,
        tags=["capacity", "growth", "planning", "forecast"],
        assumptions=[
            "Constant growth rate",
            "No disruptive changes",
        ],
        references=["Capacity Planning Methodologies"],
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

        current = assumptions.get("current_capacity_units", 1000.0)
        growth_rate = assumptions.get("growth_rate_pct", 20.0) / 100.0
        periods = int(assumptions.get("num_periods", 12))
        margin = assumptions.get("safety_margin_pct", 20.0) / 100.0

        # Compound growth: FV = PV * (1 + r)^n
        growth_factor = (1 + growth_rate) ** periods
        projected = current * growth_factor
        recommended = projected * (1 + margin)
        additional = recommended - current

        outputs = {
            "projected_capacity": round(projected, 1),
            "recommended_capacity": round(recommended, 1),
            "additional_needed": round(additional, 1),
            "compound_growth_factor": round(growth_factor, 3),
        }

        debug_info = {
            "current": current,
            "growth_rate": round(growth_rate * 100, 1),
            "periods": periods,
            "safety_margin": round(margin * 100, 1),
            "formula": f"projected = {current} * (1 + {growth_rate})^{periods}",
        }

        return outputs, self.metadata.confidence, debug_info
