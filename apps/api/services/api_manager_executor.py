"""
API Manager Executor

Handles execution of dynamic APIs defined in API Manager including
SQL, Python, Workflow, and HTTP execution with security checks,
performance controls, and execution logging.
"""

from __future__ import annotations

import re
import time
import traceback
from typing import Any, Literal

import httpx
from sqlmodel import Session, text, select

from models import ApiDefinition, ApiExecutionLog, ApiMode


# Configuration constants
STATEMENT_TIMEOUT_MS = 3000  # 3 seconds
DEFAULT_LIMIT = 200
MAX_LIMIT = 1000
HTTP_TIMEOUT = 5.0  # 5 seconds

# Dangerous SQL keywords to block
DANGEROUS_SQL_KEYWORDS = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "ALTER",
    "DROP",
    "TRUNCATE",
    "CREATE",
    "GRANT",
    "REVOKE",
    "COPY",
    "CALL",
    "DO",
}


def validate_select_sql(sql: str) -> dict[str, Any]:
    """
    Validate SQL query for security and safety.
    
    Args:
        sql: SQL query string to validate
        
    Returns:
        Dictionary with validation results:
        - is_safe: bool
        - is_valid: bool
        - errors: list[str]
        - warnings: list[str]
    """
    result = {
        "is_safe": True,
        "is_valid": True,
        "errors": [],
        "warnings": [],
    }
    
    sql_upper = sql.upper().strip()
    
    # Check if it starts with SELECT or WITH
    if not sql_upper.startswith(("SELECT ", "WITH")):
        result["is_safe"] = False
        result["is_valid"] = False
        result["errors"].append("Only SELECT and WITH statements are allowed")
    
    # Check for dangerous keywords using word boundaries
    for keyword in DANGEROUS_SQL_KEYWORDS:
        pattern = r"\b" + keyword + r"\b"
        if re.search(pattern, sql_upper):
            result["is_safe"] = False
            result["errors"].append(f"Dangerous keyword detected: {keyword}")
    
    # Basic SQL injection pattern check
    injection_patterns = [
        r";\s*(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE)",  # Multiple statements
        r"--",  # SQL comments
        r"/\*",  # Multi-line comments
    ]
    
    for pattern in injection_patterns:
        if re.search(pattern, sql_upper):
            result["is_safe"] = False
            result["errors"].append(f"Potential SQL injection pattern detected")
            break
    
    # Check for LIMIT clause (performance)
    if "LIMIT" not in sql_upper:
        result["warnings"].append(
            f"Missing LIMIT clause. Default limit of {DEFAULT_LIMIT} will be applied."
        )
    
    return result


def record_exec_log(
    session: Session,
    api_id: str,
    executed_by: str | None,
    duration_ms: int,
    request_params: dict[str, Any] | None,
    response_data: dict[str, Any] | None,
    response_status: str,
    error_message: str | None = None,
    error_stacktrace: str | None = None,
    rows_affected: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> ApiExecutionLog:
    """
    Record API execution log.
    
    Args:
        session: Database session
        api_id: API definition ID
        executed_by: User or system identifier
        duration_ms: Execution duration in milliseconds
        request_params: Request parameters
        response_data: Response data
        response_status: Execution status (success/error/timeout)
        error_message: Error message if failed
        error_stacktrace: Error stacktrace if failed
        rows_affected: Number of rows affected (for SQL)
        metadata: Additional metadata
        
    Returns:
        ApiExecutionLog instance
    """
    log = ApiExecutionLog(
        api_id=api_id,
        executed_by=executed_by,
        duration_ms=duration_ms,
        request_params=request_params,
        response_data=response_data,
        response_status=response_status,
        error_message=error_message,
        error_stacktrace=error_stacktrace,
        rows_affected=rows_affected,
        metadata=metadata,
    )
    session.add(log)
    session.commit()
    session.refresh(log)
    return log


def execute_sql_api(
    session: Session,
    api_id: str,
    logic: str,
    params: dict[str, Any],
    executed_by: str | None = None,
) -> dict[str, Any]:
    """
    Execute SQL API with security checks and performance controls.
    
    Args:
        session: Database session
        api_id: API definition ID
        logic: SQL query to execute
        params: Query parameters
        executed_by: User or system identifier
        
    Returns:
        Dictionary with execution results:
        - success: bool
        - data: list[dict] (query results)
        - rows_affected: int
        - execution_log: ApiExecutionLog
        - validation: dict (security validation results)
    """
    start_time = time.time()
    error_message = None
    error_stacktrace = None
    result_data = None
    rows_affected = 0
    
    try:
        # Validate SQL
        validation = validate_select_sql(logic)
        
        if not validation["is_safe"]:
            raise ValueError(f"SQL validation failed: {', '.join(validation['errors'])}")
        
        # Apply LIMIT if not present
        sql_to_execute = logic.strip()
        if "LIMIT" not in sql_to_execute.upper():
            limit = params.get("limit", DEFAULT_LIMIT)
            if limit > MAX_LIMIT:
                limit = MAX_LIMIT
            sql_to_execute = f"{sql_to_execute.rstrip(';')} LIMIT {limit};"
        
        # Execute query
        result = session.execute(text(sql_to_execute))
        rows = [dict(row._mapping) for row in result]
        result_data = rows
        rows_affected = len(rows)
        
    except Exception as e:
        error_message = str(e)
        error_stacktrace = traceback.format_exc()
        validation = {"is_safe": False, "is_valid": False, "errors": [str(e)], "warnings": []}
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    # Record execution log
    execution_log = record_exec_log(
        session=session,
        api_id=api_id,
        executed_by=executed_by,
        duration_ms=duration_ms,
        request_params=params,
        response_data={"data": result_data, "rows": rows_affected} if result_data else None,
        response_status="success" if error_message is None else "error",
        error_message=error_message,
        error_stacktrace=error_stacktrace,
        rows_affected=rows_affected,
        metadata={"validation": validation},
    )
    
    return {
        "success": error_message is None,
        "data": result_data,
        "rows_affected": rows_affected,
        "execution_log": execution_log,
        "validation": validation,
        "error": error_message,
    }


def execute_http_api(
    session: Session,
    api_id: str,
    logic: str,
    params: dict[str, Any],
    executed_by: str | None = None,
) -> dict[str, Any]:
    """
    Execute HTTP API request with template substitution.
    
    Args:
        session: Database session (for logging)
        api_id: API definition ID
        logic: HTTP configuration (URL, method, headers, body)
        params: Request parameters for template substitution
        executed_by: User or system identifier
        
    Returns:
        Dictionary with execution results:
        - success: bool
        - data: dict (response data)
        - status_code: int
        - execution_log: ApiExecutionLog
        
    Note:
        Supports template substitution in logic using {{params.field}} pattern
        Compatible with workflow_executor syntax
    """
    start_time = time.time()
    error_message = None
    error_stacktrace = None
    result_data = None
    status_code = None
    
    try:
        # Parse HTTP configuration
        if isinstance(logic, str):
            import json
            logic_config = json.loads(logic)
        else:
            logic_config = logic
        
        # Template substitution
        def substitute_template(value: Any) -> Any:
            if isinstance(value, str):
                # Replace {{params.field}} with actual value
                pattern = r"\{\{params\.([^}]+)\}\}"
                matches = re.findall(pattern, value)
                for match in matches:
                    param_key = match.strip()
                    if param_key in params:
                        value = value.replace(f"{{params.{param_key}}}", str(params[param_key]))
                return value
            elif isinstance(value, dict):
                return {k: substitute_template(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [substitute_template(item) for item in value]
            return value
        
        # Substitute in URL, headers, and body
        url = substitute_template(logic_config.get("url", ""))
        method = logic_config.get("method", "GET").upper()
        headers = substitute_template(logic_config.get("headers", {}))
        body = substitute_template(logic_config.get("body"))
        
        # Execute HTTP request
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            if method == "GET":
                response = client.get(url, headers=headers, params=params)
            elif method == "POST":
                response = client.post(url, headers=headers, json=body if body else params)
            elif method == "PUT":
                response = client.put(url, headers=headers, json=body if body else params)
            elif method == "DELETE":
                response = client.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            status_code = response.status_code
            
            # Try to parse JSON response
            try:
                result_data = response.json()
            except:
                result_data = {"text": response.text}
    
    except Exception as e:
        error_message = str(e)
        error_stacktrace = traceback.format_exc()
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    # Record execution log
    execution_log = record_exec_log(
        session=session,
        api_id=api_id,
        executed_by=executed_by,
        duration_ms=duration_ms,
        request_params=params,
        response_data={"status_code": status_code, "data": result_data} if result_data else None,
        response_status="success" if error_message is None else "error",
        error_message=error_message,
        error_stacktrace=error_stacktrace,
        metadata={"http_status": status_code},
    )
    
    return {
        "success": error_message is None,
        "data": result_data,
        "status_code": status_code,
        "execution_log": execution_log,
        "error": error_message,
    }


def execute_python_api(
    session: Session,
    api_id: str,
    logic: str,
    params: dict[str, Any],
    executed_by: str | None = None,
) -> dict[str, Any]:
    """
    Execute Python script API with sandboxing.
    
    Args:
        session: Database session (for logging)
        api_id: API definition ID
        logic: Python code to execute
        params: Input parameters
        executed_by: User or system identifier
        
    Returns:
        Dictionary with execution results:
        - success: bool
        - data: Any (script output)
        - execution_log: ApiExecutionLog
        
    Note:
        This is a simplified implementation. For production use,
        consider using a proper sandboxing solution like RestrictedPython.
    """
    start_time = time.time()
    error_message = None
    error_stacktrace = None
    result_data = None
    
    try:
        # Create a restricted execution environment
        exec_globals = {
            "__builtins__": {
                "len": len,
                "str": str,
                "int": int,
                "float": float,
                "dict": dict,
                "list": list,
                "tuple": tuple,
                "bool": bool,
            },
            "params": params,
        }
        
        # Execute the script
        exec(logic, exec_globals)
        
        # Get the result from 'result' variable if defined
        if "result" in exec_globals:
            result_data = exec_globals["result"]
        else:
            result_data = {"message": "Script executed successfully (no result variable)"}
    
    except Exception as e:
        error_message = str(e)
        error_stacktrace = traceback.format_exc()
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    # Record execution log
    execution_log = record_exec_log(
        session=session,
        api_id=api_id,
        executed_by=executed_by,
        duration_ms=duration_ms,
        request_params=params,
        response_data=result_data,
        response_status="success" if error_message is None else "error",
        error_message=error_message,
        error_stacktrace=error_stacktrace,
    )
    
    return {
        "success": error_message is None,
        "data": result_data,
        "execution_log": execution_log,
        "error": error_message,
    }


def execute_workflow_api(
    session: Session,
    api_id: str,
    logic: str,
    params: dict[str, Any],
    executed_by: str | None = None,
) -> dict[str, Any]:
    """
    Execute Workflow API.
    
    Args:
        session: Database session (for logging)
        api_id: API definition ID
        logic: Workflow configuration
        params: Input parameters
        executed_by: User or system identifier
        
    Returns:
        Dictionary with execution results:
        - success: bool
        - data: Any (workflow output)
        - execution_log: ApiExecutionLog
        
    Note:
        This is a placeholder implementation. For production use,
        integrate with your actual workflow execution engine.
    """
    start_time = time.time()
    error_message = None
    error_stacktrace = None
    result_data = None
    
    try:
        # Placeholder: Workflow execution logic
        # In production, this would integrate with your workflow engine
        import json
        
        if isinstance(logic, str):
            workflow_config = json.loads(logic)
        else:
            workflow_config = logic
        
        # Placeholder workflow execution
        result_data = {
            "message": "Workflow execution not yet implemented",
            "workflow": workflow_config.get("name", "unknown"),
            "steps": workflow_config.get("steps", []),
            "input_params": params,
        }
        
        # TODO: Implement actual workflow execution logic
        # This would call your workflow orchestrator
        
    except Exception as e:
        error_message = str(e)
        error_stacktrace = traceback.format_exc()
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    # Record execution log
    execution_log = record_exec_log(
        session=session,
        api_id=api_id,
        executed_by=executed_by,
        duration_ms=duration_ms,
        request_params=params,
        response_data=result_data,
        response_status="success" if error_message is None else "error",
        error_message=error_message,
        error_stacktrace=error_stacktrace,
    )
    
    return {
        "success": error_message is None,
        "data": result_data,
        "execution_log": execution_log,
        "error": error_message,
    }


def execute_api(
    session: Session,
    api_id: str,
    params: dict[str, Any],
    executed_by: str | None = None,
) -> dict[str, Any]:
    """
    Execute API based on its mode.
    
    Args:
        session: Database session
        api_id: API definition ID
        params: Request parameters
        executed_by: User or system identifier
        
    Returns:
        Dictionary with execution results
        
    Raises:
        ValueError: If API not found or mode is invalid
    """
    # Get API definition
    api = session.get(ApiDefinition, api_id)
    if not api:
        raise ValueError(f"API not found: {api_id}")
    
    if not api.is_enabled:
        raise ValueError(f"API is disabled: {api.name}")
    
    if not api.mode:
        raise ValueError(f"API mode not specified: {api.name}")
    
    # Execute based on mode
    if api.mode == ApiMode.sql:
        return execute_sql_api(session, api_id, api.logic, params, executed_by)
    elif api.mode == ApiMode.python:
        return execute_python_api(session, api_id, api.logic, params, executed_by)
    elif api.mode == ApiMode.workflow:
        return execute_workflow_api(session, api_id, api.logic, params, executed_by)
    else:
        raise ValueError(f"Unsupported API mode: {api.mode}")