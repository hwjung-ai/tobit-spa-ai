"""
SIM Function Library - Base Classes

Defines the base abstraction for all simulation functions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any


class FunctionCategory(str, Enum):
    """Simulation function categories."""

    RULE = "rule"
    STATISTICAL = "statistical"
    ML = "ml"
    DOMAIN = "domain"


class FunctionComplexity(str, Enum):
    """Function complexity levels."""

    BASIC = "basic"      # Simple linear/threshold functions
    INTERMEDIATE = "intermediate"  # Multi-variable, polynomial
    ADVANCED = "advanced"  # ML/DL models, complex simulations


@dataclass
class FunctionParameter:
    """Function parameter definition."""

    name: str
    type: str  # "number", "integer", "boolean", "string", "array"
    default: Any
    min: float | None = None
    max: float | None = None
    step: float | None = None
    description: str = ""
    unit: str = ""
    required: bool = True


@dataclass
class FunctionOutput:
    """Function output definition."""

    name: str
    unit: str
    description: str = ""
    min_value: float | None = None
    max_value: float | None = None


@dataclass
class FunctionMetadata:
    """Function metadata for catalog registration."""

    id: str
    name: str
    category: FunctionCategory
    complexity: FunctionComplexity
    description: str
    parameters: list[FunctionParameter]
    outputs: list[FunctionOutput]
    confidence: float  # Expected confidence score (0-1)
    tags: list[str]
    assumptions: list[str]  # Key assumptions/limitations
    references: list[str]  # Academic/industry references
    version: str = "1.0.0"
    author: str = "tobit-spa-ai"


class SimulationFunction(ABC):
    """
    Base class for all simulation functions.

    A simulation function takes baseline data and assumptions,
    then produces simulated KPI outputs.
    """

    # Subclasses must define these class attributes
    metadata: FunctionMetadata

    @abstractmethod
    def execute(
        self,
        *,
        baseline: dict[str, float],
        assumptions: dict[str, float],
        context: dict[str, Any] | None = None,
    ) -> tuple[dict[str, float], float, dict[str, Any]]:
        """
        Execute the simulation function.

        Args:
            baseline: Baseline KPI values (e.g., {"latency_ms": 50, "throughput_rps": 1000})
            assumptions: Input assumptions (e.g., {"traffic_change_pct": 20})
            context: Additional context (service name, tenant_id, etc.)

        Returns:
            (outputs, confidence, debug_info)
            - outputs: Simulated KPI values
            - confidence: Confidence score (0-1)
            - debug_info: Additional debug/explanation data
        """
        pass

    def validate_inputs(
        self,
        baseline: dict[str, float],
        assumptions: dict[str, float],
    ) -> list[str]:
        """
        Validate inputs against function requirements.

        Returns:
            List of validation error messages (empty if valid).
        """
        errors = []

        # Check required baseline KPIs
        for output in self.metadata.outputs:
            if output.name not in baseline:
                errors.append(f"Missing baseline KPI: {output.name}")

        # Check required assumptions
        for param in self.metadata.parameters:
            if param.required and param.name not in assumptions:
                errors.append(f"Missing required assumption: {param.name}")

        # Validate parameter ranges
        for param in self.metadata.parameters:
            value = assumptions.get(param.name)
            if value is not None:
                if param.min is not None and value < param.min:
                    errors.append(f"{param.name} must be >= {param.min}, got {value}")
                if param.max is not None and value > param.max:
                    errors.append(f"{param.name} must be <= {param.max}, got {value}")

        return errors


class CompositeFunction(SimulationFunction):
    """
    Base class for functions that combine multiple sub-functions.
    """

    def __init__(self, functions: list[SimulationFunction], weights: list[float] | None = None):
        self.functions = functions
        self.weights = weights or [1.0 / len(functions)] * len(functions)

        if len(self.weights) != len(self.functions):
            raise ValueError("Weights must match number of functions")

        if abs(sum(self.weights) - 1.0) > 0.01:
            raise ValueError("Weights must sum to 1.0")


def create_error_result(message: str) -> tuple[dict[str, float], float, dict[str, Any]]:
    """Create an error result for function execution failures."""
    return {}, 0.0, {"error": message, "success": False}
