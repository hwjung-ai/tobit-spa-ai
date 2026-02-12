"""
User Function Registration System

Allows users to register custom simulation functions that can be used
alongside the built-in function library.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from sqlmodel import Session, select

from app.modules.simulation.services.simulation.functions.base import (
    FunctionCategory,
    FunctionComplexity,
    FunctionMetadata,
    FunctionOutput,
    FunctionParameter,
    SimulationFunction,
)


class UserFunctionRegistry:
    """
    Registry for user-defined simulation functions.

    User functions are stored in the database and can be used
    alongside built-in functions.
    """

    @staticmethod
    def _generate_function_id(user_id: str, name: str) -> str:
        """Generate a unique function ID from user_id and name."""
        hash_input = f"{user_id}:{name}".encode()
        return f"user_{hashlib.sha256(hash_input).hexdigest()[:16]}"

    @staticmethod
    def validate_function_code(code: str) -> tuple[bool, list[str]]:
        """
        Validate user function code for safety.

        Args:
            code: Python code to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Check for dangerous operations
        dangerous_patterns = [
            "import os",
            "import subprocess",
            "import sys",
            "eval(",
            "exec(",
            "__import__",
            "compile(",
            "open(",
            "file(",
            "globals(",
            "locals(",
        ]

        for pattern in dangerous_patterns:
            if pattern in code:
                errors.append(f"Dangerous operation detected: {pattern}")

        # Check for required function signature
        if "def execute(" not in code:
            errors.append("Function must have an 'execute' method")

        if "self, baseline, assumptions" not in code and "baseline, assumptions" not in code:
            errors.append("execute() method must accept 'baseline' and 'assumptions' parameters")

        return len(errors) == 0, errors

    @staticmethod
    def register_user_function(
        *,
        user_id: str,
        tenant_id: str,
        name: str,
        description: str,
        category: FunctionCategory,
        complexity: FunctionComplexity,
        code: str,
        parameters: list[dict[str, Any]],
        outputs: list[dict[str, Any]],
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Register a user-defined function.

        Args:
            user_id: User ID
            tenant_id: Tenant ID
            name: Function name
            description: Function description
            category: Function category
            complexity: Function complexity
            code: Python function code
            parameters: List of parameter definitions
            outputs: List of output definitions
            tags: Optional tags

        Returns:
            Registered function metadata
        """
        # Validate code
        is_valid, errors = UserFunctionRegistry.validate_function_code(code)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid function code: {'; '.join(errors)}"
            )

        # Generate function ID
        function_id = UserFunctionRegistry._generate_function_id(user_id, name)

        # Create metadata
        function_params = [
            FunctionParameter(
                name=p["name"],
                type=p.get("type", "number"),
                default=p.get("default"),
                min=p.get("min"),
                max=p.get("max"),
                step=p.get("step"),
                description=p.get("description", ""),
                unit=p.get("unit", ""),
                required=p.get("required", True),
            )
            for p in parameters
        ]

        function_outputs = [
            FunctionOutput(
                name=o["name"],
                unit=o.get("unit", ""),
                description=o.get("description", ""),
            )
            for o in outputs
        ]

        metadata = FunctionMetadata(
            id=function_id,
            name=name,
            category=category,
            complexity=complexity,
            description=description,
            parameters=function_params,
            outputs=function_outputs,
            confidence=0.75,  # Default confidence for user functions
            tags=tags or [],
            assumptions=["User-defined function", "Not validated by system"],
            references=[],
            version="1.0.0",
            author=user_id,
        )

        # In production, save to database here
        # For now, return metadata

        return {
            "function_id": function_id,
            "metadata": metadata,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "status": "pending_validation",
        }

    @staticmethod
    def load_user_function(function_id: str, session: Session) -> SimulationFunction | None:
        """
        Load a user function from the database.

        Args:
            function_id: Function ID
            session: Database session

        Returns:
            SimulationFunction instance or None
        """
        # In production, load from database
        # For now, return None

        # Example implementation:
        # from app.modules.simulation.models import UserFunction
        # db_func = session.exec(
        #     select(UserFunction).where(UserFunction.function_id == function_id)
        # ).first()
        #
        # if not db_func:
        #     return None
        #
        # return DynamicUserFunction(db_func.code, metadata)

        return None


class DynamicUserFunction(SimulationFunction):
    """
    Dynamically loaded user function.

    Executes user-provided code in a controlled environment.
    """

    def __init__(self, code: str, metadata: FunctionMetadata):
        self.code = code
        self.metadata = metadata
        self._compiled_code = None

        try:
            self._compiled_code = compile(code, "<user_function>", "exec")
        except SyntaxError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Syntax error in function code: {e}"
            )

    def execute(
        self,
        *,
        baseline: dict[str, float],
        assumptions: dict[str, float],
        context: dict[str, Any] | None = None,
    ) -> tuple[dict[str, float], float, dict[str, Any]]:
        """
        Execute the user function.

        Args:
            baseline: Baseline KPI values
            assumptions: Input assumptions
            context: Optional context

        Returns:
            (outputs, confidence, debug_info)
        """
        if not self._compiled_code:
            return {}, 0.0, {"error": "Function not compiled"}

        # Create execution namespace
        namespace = {
            "baseline": baseline,
            "assumptions": assumptions,
            "context": context or {},
            "result": None,
        }

        try:
            # Execute user code
            exec(self._compiled_code, namespace)

            # Get result
            result = namespace.get("result")

            if not isinstance(result, dict):
                return {}, 0.0, {"error": "Function must set 'result' variable with dict output"}

            confidence = result.get("confidence", self.metadata.confidence)

            return result, confidence, {
                "user_function": True,
                "function_id": self.metadata.id,
            }

        except Exception as e:
            return {}, 0.0, {
                "error": f"Function execution failed: {str(e)}",
                "user_function": True,
                "function_id": self.metadata.id,
            }


def register_user_function_from_spec(
    *,
    user_id: str,
    tenant_id: str,
    spec: dict[str, Any],
) -> dict[str, Any]:
    """
    Register a user function from a specification dict.

    This is the main entry point for user function registration.

    Args:
        user_id: User ID
        tenant_id: Tenant ID
        spec: Function specification containing:
            - name: Function name
            - description: Function description
            - category: Function category
            - complexity: Function complexity
            - code: Python function code
            - parameters: List of parameter definitions
            - outputs: List of output definitions
            - tags: Optional tags

    Returns:
        Registration result
    """
    return UserFunctionRegistry.register_user_function(
        user_id=user_id,
        tenant_id=tenant_id,
        name=spec["name"],
        description=spec.get("description", ""),
        category=FunctionCategory(spec.get("category", "rule")),
        complexity=FunctionComplexity(spec.get("complexity", "basic")),
        code=spec["code"],
        parameters=spec.get("parameters", []),
        outputs=spec.get("outputs", []),
        tags=spec.get("tags"),
    )


# Example user function template
USER_FUNCTION_TEMPLATE = '''
def execute_simulation(baseline, assumptions):
    """
    User-defined simulation function.

    Args:
        baseline: Dict with baseline KPIs (latency_ms, throughput_rps, etc.)
        assumptions: Dict with input assumptions

    Returns:
        Dict with:
            - outputs: Dict of simulated KPI values
            - confidence: Confidence score (0-1)
            - debug_info: Dict with debug information
    """
    traffic = assumptions.get("traffic_change_pct", 0.0)
    cpu = assumptions.get("cpu_change_pct", 0.0)

    # Calculate impact
    impact = (0.6 * traffic) + (0.3 * cpu)

    # Apply to baseline
    baseline_latency = baseline.get("latency_ms", 50.0)
    simulated_latency = baseline_latency * (1 + impact / 100)

    result = {
        "latency_ms": simulated_latency,
        "throughput_rps": baseline.get("throughput_rps", 1000) * (1 + traffic / 100),
        "error_rate_pct": baseline.get("error_rate_pct", 0.5) + max(0, impact) * 0.01,
        "cost_usd_hour": baseline.get("cost_usd_hour", 10) * (1 + max(0, traffic) / 100),
    }

    return {
        "outputs": result,
        "confidence": 0.75,
        "debug_info": {
            "impact": impact,
            "method": "user_defined"
        }
    }
'''
