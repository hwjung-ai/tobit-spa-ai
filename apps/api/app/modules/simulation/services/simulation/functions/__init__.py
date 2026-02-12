"""
SIM Function Library

A comprehensive library of simulation functions organized by category:
- Rule-based functions
- Statistical functions
- Machine Learning functions
- Domain-specific functions

Usage:
    from app.modules.simulation.services.simulation.functions import (
        FunctionRegistry,
        list_functions,
        execute_simulation,
    )

    # List all functions
    all_functions = list_functions()

    # List by category
    rule_functions = list_functions(category=FunctionCategory.RULE)

    # Execute a function
    result = execute_simulation(
        function_id="rule_linear_weight",
        baseline={"latency_ms": 50, "throughput_rps": 1000},
        assumptions={"traffic_change_pct": 20, "cpu_change_pct": 10},
    )
"""

from app.modules.simulation.services.simulation.functions.base import (
    CompositeFunction,
    FunctionCategory,
    FunctionComplexity,
    FunctionMetadata,
    FunctionOutput,
    FunctionParameter,
    SimulationFunction,
    create_error_result,
)
from app.modules.simulation.services.simulation.functions.registry import (
    FunctionRegistry,
    execute_simulation,
    get_function_info,
    get_strategy_function,
    list_functions,
)

__all__ = [
    # Base classes
    "SimulationFunction",
    "CompositeFunction",
    "FunctionCategory",
    "FunctionComplexity",
    "FunctionMetadata",
    "FunctionParameter",
    "FunctionOutput",
    "create_error_result",
    # Registry
    "FunctionRegistry",
    "list_functions",
    "get_function_info",
    "execute_simulation",
    "get_strategy_function",
]
