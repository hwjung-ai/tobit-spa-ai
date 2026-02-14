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
from typing import Any

import httpx
from models import ApiDefinition, ApiExecutionLog, ApiMode
from sqlmodel import Session, text

class SecurityError(Exception):
    """Raised when script contains forbidden patterns."""


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
            result["errors"].append("Potential SQL injection pattern detected")
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
    
    # Validate logic before execution - block dangerous patterns
    _BLOCKED_PATTERNS = [
        r"\b__import__\b", r"\bimport\s+", r"\bfrom\s+\w+\s+import\b",
        r"\bopen\s*\(", r"\beval\s*\(", r"\bexec\s*\(",
        r"\bos\.", r"\bsys\.", r"\bsubprocess\.",
        r"\b__subclasses__\b", r"\b__bases__\b", r"\b__globals__\b",
        r"\b__builtins__\b", r"\bgetattr\s*\(", r"\bsetattr\s*\(",
        r"\bdelattr\s*\(", r"\b__class__\b", r"\bbreakpoint\s*\(",
        r"\bcompile\s*\(", r"\bglobals\s*\(", r"\blocals\s*\(",
    ]

    try:
        for pattern in _BLOCKED_PATTERNS:
            if re.search(pattern, logic):
                raise SecurityError(
                    f"Blocked: script contains forbidden pattern '{pattern}'"
                )

        # Create a tightly restricted execution environment
        _SAFE_BUILTINS = {
            "len": len, "str": str, "int": int, "float": float,
            "dict": dict, "list": list, "tuple": tuple, "bool": bool,
            "range": range, "enumerate": enumerate, "zip": zip,
            "min": min, "max": max, "sum": sum, "abs": abs,
            "round": round, "sorted": sorted, "reversed": reversed,
            "map": map, "filter": filter, "isinstance": isinstance,
            "True": True, "False": False, "None": None,
            "print": lambda *a, **kw: None,  # no-op print
        }

        exec_globals: dict[str, Any] = {
            "__builtins__": _SAFE_BUILTINS,
            "params": params,
        }
        exec_locals: dict[str, Any] = {}

        # Compile first to catch syntax errors before exec
        compiled = compile(logic, "<api_script>", "exec")

        # Execute the compiled code
        exec(compiled, exec_globals, exec_locals)  # noqa: S102

        # Get the result from 'result' variable if defined
        if "result" in exec_locals:
            result_data = exec_locals["result"]
        elif "result" in exec_globals:
            result_data = exec_globals["result"]
        else:
            result_data = {"message": "Script executed successfully (no result variable)"}

    except SecurityError as e:
        error_message = str(e)
        error_stacktrace = None
    except SyntaxError as e:
        error_message = f"Syntax error in script: {e}"
        error_stacktrace = traceback.format_exc()
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


def substitute_workflow_params(
    template: Any,
    context: dict[str, Any],
    params: dict[str, Any],
) -> Any:
    """
    Substitute workflow template parameters with actual values.
    
    Args:
        template: Template value (string, dict, list)
        context: Execution context including steps results
        params: Input parameters
        
    Returns:
        Substituted value
        
    Supports:
        - {{params.field}} - Input parameters
        - {{steps.node_id.rows}} - Results from previous steps
        - {{steps.node_id.columns}} - Column names from previous steps
        - {{steps.node_id.row_count}} - Row count from previous steps
    """
    if isinstance(template, str):
        # Substitute {{params.field}}
        pattern = r"\{\{params\.([^}]+)\}\}"
        matches = re.findall(pattern, template)
        for match in matches:
            param_key = match.strip()
            if param_key in params:
                template = template.replace(f"{{params.{param_key}}}", str(params[param_key]))
        
        # Substitute {{steps.node_id.rows}}
        pattern = r"\{\{steps\.([^}]+)\.rows\}\}"
        matches = re.findall(pattern, template)
        for match in matches:
            node_id = match.strip()
            if node_id in context:
                node_result = context[node_id]
                if "rows" in node_result and isinstance(node_result["rows"], list):
                    rows_str = str(node_result["rows"])
                    template = template.replace(f"{{steps.{node_id}.rows}}", rows_str)
        
        # Substitute {{steps.node_id.columns}}
        pattern = r"\{\{steps\.([^}]+)\.columns\}\}"
        matches = re.findall(pattern, template)
        for match in matches:
            node_id = match.strip()
            if node_id in context:
                node_result = context[node_id]
                if "columns" in node_result and isinstance(node_result["columns"], list):
                    columns_str = str(node_result["columns"])
                    template = template.replace(f"{{steps.{node_id}.columns}}", columns_str)
        
        # Substitute {{steps.node_id.row_count}}
        pattern = r"\{\{steps\.([^}]+)\.row_count\}\}"
        matches = re.findall(pattern, template)
        for match in matches:
            node_id = match.strip()
            if node_id in context:
                node_result = context[node_id]
                if "row_count" in node_result:
                    template = template.replace(f"{{steps.{node_id}.row_count}}", str(node_result["row_count"]))
        
        return template
    elif isinstance(template, dict):
        return {k: substitute_workflow_params(v, context, params) for k, v in template.items()}
    elif isinstance(template, list):
        return [substitute_workflow_params(item, context, params) for item in template]
    return template


def build_execution_order(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> list[str]:
    """
    Build execution order using topological sort.
    
    Args:
        nodes: List of workflow nodes
        edges: List of workflow edges (dependencies)
        
    Returns:
        Ordered list of node IDs
        
    Raises:
        ValueError: If there's a circular dependency
    """
    # Build adjacency list and in-degree count
    adjacency = {node["id"]: [] for node in nodes}
    in_degree = {node["id"]: 0 for node in nodes}
    
    for edge in edges:
        source = edge["source"]
        target = edge["target"]
        adjacency[source].append(target)
        in_degree[target] += 1
    
    # Kahn's algorithm for topological sort
    queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
    execution_order = []
    
    while queue:
        node_id = queue.pop(0)
        execution_order.append(node_id)
        
        for neighbor in adjacency[node_id]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    
    # Check for circular dependencies
    if len(execution_order) != len(nodes):
        raise ValueError("Circular dependency detected in workflow")
    
    return execution_order


def execute_workflow_node(
    session: Session,
    node: dict[str, Any],
    context: dict[str, Any],
    params: dict[str, Any],
    workflow_api_id: str,
    executed_by: str | None,
) -> dict[str, Any]:
    """
    Execute a single workflow node.
    
    Args:
        session: Database session
        node: Node configuration
        context: Execution context (results from previous steps)
        params: Input parameters
        workflow_api_id: Parent workflow API ID
        executed_by: User or system identifier
        
    Returns:
        Dictionary with node execution result:
        - node_id: str
        - node_type: str
        - status: str
        - duration_ms: int
        - columns: list (if applicable)
        - rows: list (if applicable)
        - output: any
        - error_message: str (if failed)
    """
    start_time = time.time()
    node_id = node["id"]
    node_type = node["type"]
    config = node.get("config", {})
    
    try:
        # Substitute parameters in config
        substituted_config = substitute_workflow_params(config, context, params)
        
        # Execute based on node type
        if node_type == "sql":
            query = substituted_config.get("query", "")
            if not query:
                raise ValueError(f"SQL node {node_id} has no query")
            
            # Validate and execute SQL
            validation = validate_select_sql(query)
            if not validation["is_safe"]:
                raise ValueError(f"SQL validation failed: {', '.join(validation['errors'])}")
            
            # Apply LIMIT if not present
            sql_to_execute = query.strip()
            if "LIMIT" not in sql_to_execute.upper():
                limit = params.get("limit", DEFAULT_LIMIT)
                if limit > MAX_LIMIT:
                    limit = MAX_LIMIT
                sql_to_execute = f"{sql_to_execute.rstrip(';')} LIMIT {limit};"
            
            # Execute query
            result = session.execute(text(sql_to_execute))
            rows = [dict(row._mapping) for row in result]
            columns = list(rows[0].keys()) if rows else []
            
            return {
                "node_id": node_id,
                "node_type": node_type,
                "status": "success",
                "duration_ms": int((time.time() - start_time) * 1000),
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "output": {"columns": columns, "rows": rows, "row_count": len(rows)},
                "error_message": None,
            }
        
        elif node_type == "http":
            url = substituted_config.get("url", "")
            method = substituted_config.get("method", "GET").upper()
            headers = substituted_config.get("headers", {})
            body = substituted_config.get("body")
            
            if not url:
                raise ValueError(f"HTTP node {node_id} has no URL")
            
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
                
                # Try to parse JSON response
                try:
                    response_data = response.json()
                except:
                    response_data = {"text": response.text}
                
                # Convert to table format
                if isinstance(response_data, dict):
                    columns = list(response_data.keys())
                    rows = [response_data]
                elif isinstance(response_data, list):
                    columns = list(response_data[0].keys()) if response_data else []
                    rows = response_data
                else:
                    columns = ["value"]
                    rows = [{"value": str(response_data)}]
                
                return {
                    "node_id": node_id,
                    "node_type": node_type,
                    "status": "success",
                    "duration_ms": int((time.time() - start_time) * 1000),
                    "columns": columns,
                    "rows": rows,
                    "row_count": len(rows),
                    "output": response_data,
                    "error_message": None,
                }
        
        elif node_type == "python":
            code = substituted_config.get("code", "")
            if not code:
                raise ValueError(f"Python node {node_id} has no code")
            
            # Create restricted execution environment
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
                "context": context,
            }
            
            # Execute Python code
            exec(code, exec_globals)
            
            # Get result from 'result' variable if defined
            if "result" in exec_globals:
                result = exec_globals["result"]
                
                # Convert to table format
                if isinstance(result, dict):
                    columns = ["key", "value"]
                    rows = [{"key": k, "value": v} for k, v in result.items()]
                elif isinstance(result, list):
                    columns = list(result[0].keys()) if result else []
                    rows = result
                else:
                    columns = ["value"]
                    rows = [{"value": str(result)}]
            else:
                result = {"message": "Python code executed (no result variable)"}
                columns = ["message"]
                rows = [result]
            
            return {
                "node_id": node_id,
                "node_type": node_type,
                "status": "success",
                "duration_ms": int((time.time() - start_time) * 1000),
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "output": result,
                "error_message": None,
            }
        
        else:
            raise ValueError(f"Unsupported node type: {node_type}")
    
    except Exception as e:
        return {
            "node_id": node_id,
            "node_type": node_type,
            "status": "fail",
            "duration_ms": int((time.time() - start_time) * 1000),
            "columns": [],
            "rows": [],
            "row_count": 0,
            "output": None,
            "error_message": str(e),
        }


def execute_workflow_api(
    session: Session,
    workflow_api: Any,
    params: dict[str, Any],
    input_payload: dict[str, Any] | None = None,
    executed_by: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """
    Execute Workflow API with node orchestration.
    
    Args:
        session: Database session (for logging)
        workflow_api: Workflow API object or dict with 'logic' and 'api_id'
        params: Input parameters
        input_payload: Additional input payload (optional)
        executed_by: User or system identifier
        limit: Row limit for SQL nodes (optional)
        
    Returns:
        Dictionary with execution results:
        - success: bool
        - steps: list[dict] (node execution results)
        - final_output: dict (workflow final output)
        - execution_log: ApiExecutionLog
        - error: str (if failed)
    """
    start_time = time.time()
    error_message = None
    error_stacktrace = None
    steps = []
    final_output = {}
    
    try:
        # Parse workflow configuration
        import json
        logic = workflow_api.logic if hasattr(workflow_api, "logic") else workflow_api.get("logic", "{}")
        api_id = str(workflow_api.api_id) if hasattr(workflow_api, "api_id") else workflow_api.get("api_id", "unknown")
        
        if isinstance(logic, str):
            workflow_config = json.loads(logic)
        else:
            workflow_config = logic
        
        # Get nodes and edges
        nodes = workflow_config.get("nodes", [])
        edges = workflow_config.get("edges", [])
        
        # Build execution order (topological sort)
        execution_order = build_execution_order(nodes, edges)
        
        # Execute nodes in order
        context: dict[str, Any] = {}
        
        for node_id in execution_order:
            # Find node configuration
            node = next((n for n in nodes if n["id"] == node_id), None)
            if not node:
                raise ValueError(f"Node not found: {node_id}")
            
            # Execute node
            step_result = execute_workflow_node(
                session=session,
                node=node,
                context=context,
                params=params,
                workflow_api_id=api_id,
                executed_by=executed_by,
            )
            
            steps.append(step_result)
            
            # Check for errors
            if step_result["status"] == "fail":
                raise Exception(f"Node {node_id} failed: {step_result['error_message']}")
            
            # Store result in context for next steps
            context[node_id] = {
                "columns": step_result["columns"],
                "rows": step_result["rows"],
                "row_count": step_result["row_count"],
                "output": step_result["output"],
            }
        
        # Final output (last step's output or all steps)
        final_output = {
            "steps": steps,
            "total_duration_ms": sum(step["duration_ms"] for step in steps),
            "total_nodes": len(steps),
            "successful_nodes": len([s for s in steps if s["status"] == "success"]),
            "failed_nodes": len([s for s in steps if s["status"] == "fail"]),
        }
        
        # Add last step's output as final result
        if steps:
            last_step = steps[-1]
            final_output["last_node_output"] = last_step["output"]
            final_output["last_node_id"] = last_step["node_id"]
    
    except Exception as e:
        error_message = str(e)
        error_stacktrace = traceback.format_exc()
        final_output = {
            "steps": steps,
            "total_duration_ms": sum(step["duration_ms"] for step in steps),
            "total_nodes": len(steps),
            "error": error_message,
        }
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    # Record execution log
    execution_log = record_exec_log(
        session=session,
        api_id=api_id,
        executed_by=executed_by,
        duration_ms=duration_ms,
        request_params={"params": params, "input_payload": input_payload},
        response_data={"steps": steps, "final_output": final_output} if final_output else None,
        response_status="success" if error_message is None else "error",
        error_message=error_message,
        error_stacktrace=error_stacktrace,
        rows_affected=sum(step.get("row_count", 0) for step in steps),
        metadata={"workflow_steps": len(steps)},
    )
    
    return {
        "success": error_message is None,
        "steps": steps,
        "final_output": final_output,
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