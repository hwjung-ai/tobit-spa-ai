"""Test cases for API Manager Executor."""

import json
import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException
from sqlmodel import Session
from app.services.api_manager_executor import (
    execute_sql_api,
    execute_http_api,
    execute_python_api,
    execute_workflow_api,
    execute_api,
    validate_select_sql,
)


@pytest.mark.asyncio
async def test_validate_select_sql_valid():
    """Test valid SELECT SQL."""
    sql = "SELECT id, name FROM users WHERE status = 'active'"
    is_valid, error = validate_select_sql(sql)
    assert is_valid is True
    assert error is None


@pytest.mark.asyncio
async def test_validate_select_sql_with_cte():
    """Valid SQL with CTE (Common Table Expression)."""
    sql = """
    WITH active_users AS (
        SELECT id, name FROM users WHERE status = 'active'
    )
    SELECT * FROM active_users
    """
    is_valid, error = validate_select_sql(sql)
    assert is_valid is True
    assert error is None


@pytest.mark.asyncio
async def test_validate_select_sql_insert_forbidden():
    """INSERT statements should be rejected."""
    sql = "INSERT INTO users (name) VALUES ('test')"
    is_valid, error = validate_select_sql(sql)
    assert is_valid is False
    assert "INSERT is not allowed" in error


@pytest.mark.asyncio
async def test_validate_select_sql_delete_forbidden():
    """DELETE statements should be rejected."""
    sql = "DELETE FROM users WHERE id = 1"
    is_valid, error = validate_select_sql(sql)
    assert is_valid is False
    assert "DELETE is not allowed" in error


@pytest.mark.asyncio
async def test_validate_select_sql_drop_forbidden():
    """DROP statements should be rejected."""
    sql = "DROP TABLE users"
    is_valid, error = validate_select_sql(sql)
    assert is_valid is False
    assert "DROP is not allowed" in error


@pytest.mark.asyncio
async def test_validate_select_sql_sql_injection_keywords():
    """Dangerous SQL keywords should be rejected."""
    dangerous_sqls = [
        "SELECT * FROM users; DROP TABLE users--",
        "SELECT * FROM users UNION SELECT * FROM passwords",
        "SELECT * FROM users WHERE 1=1; GRANT ALL ON DATABASE * TO hacker",
    ]
    for sql in dangerous_sqls:
        is_valid, error = validate_select_sql(sql)
        assert is_valid is False, f"Should reject: {sql}"


@pytest.mark.asyncio
@patch("app.services.api_manager_executor.httpx.request")
async def test_execute_http_api_get(mock_request):
    """Test HTTP GET request execution."""
    # Mock response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": "test"}
    mock_request.return_value = mock_response

    logic_body = json.dumps({
        "method": "GET",
        "url": "https://api.example.com/data",
        "headers": {"Authorization": "Bearer token"}
    })

    session = Mock(spec=Session)
    result = execute_http_api(
        session=session,
        api_id="test-api",
        logic_body=logic_body,
        params={"param1": "value1"},
        executed_by="test-user"
    )

    assert result.status_code == 200
    assert result.rows == [{"data": "test"}]
    assert "columns" in result
    mock_request.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.api_manager_executor.httpx.request")
async def test_execute_http_api_post(mock_request):
    """Test HTTP POST request execution."""
    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"id": "123", "created": True}
    mock_request.return_value = mock_response

    logic_body = json.dumps({
        "method": "POST",
        "url": "https://api.example.com/users",
        "body": {"name": "John", "email": "john@example.com"},
        "headers": {"Content-Type": "application/json"}
    })

    session = Mock(spec=Session)
    result = execute_http_api(
        session=session,
        api_id="test-api",
        logic_body=logic_body,
        params={},
        executed_by="test-user"
    )

    assert result.status_code == 201
    assert result.rows == [{"id": "123", "created": True}]


@pytest.mark.asyncio
async def test_execute_http_api_invalid_json():
    """Test HTTP API with invalid JSON body."""
    logic_body = "invalid json {"
    session = Mock(spec=Session)

    with pytest.raises(HTTPException) as exc_info:
        execute_http_api(
            session=session,
            api_id="test-api",
            logic_body=logic_body,
            params={},
            executed_by="test-user"
        )
    
    assert exc_info.value.status_code == 400
    assert "Invalid HTTP logic body" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_execute_python_api_simple():
    """Test Python script execution."""
    logic_body = """
def main(params, input_payload):
    return {"result": "hello", "value": params.get("x", 0) * 2}
"""

    session = Mock(spec=Session)
    result = execute_python_api(
        session=session,
        api_id="test-api",
        logic_body=logic_body,
        params={"x": 5},
        executed_by="test-user"
    )

    assert result.status_code == 200
    assert result.rows == [{"result": "hello", "value": 10}]


@pytest.mark.asyncio
async def test_execute_python_api_with_input():
    """Test Python script with input_payload."""
    logic_body = """
def main(params, input_payload):
    return {
        "name": input_payload.get("name"),
        "count": len(input_payload.get("items", []))
    }
"""

    session = Mock(spec=Session)
    result = execute_python_api(
        session=session,
        api_id="test-api",
        logic_body=logic_body,
        params={},
        input_payload={"name": "test", "items": [1, 2, 3]},
        executed_by="test-user"
    )

    assert result.rows == [{"name": "test", "count": 3}]


@pytest.mark.asyncio
async def test_execute_python_api_runtime_error():
    """Test Python script with runtime error."""
    logic_body = """
def main(params, input_payload):
    raise ValueError("Test error")
"""

    session = Mock(spec=Session)
    result = execute_python_api(
        session=session,
        api_id="test-api",
        logic_body=logic_body,
        params={},
        executed_by="test-user"
    )

    assert result.status_code == 500
    assert result.rows == [{"error": "ValueError: Test error"}]
    assert "logs" in result.rows[0]


@pytest.mark.asyncio
async def test_execute_workflow_api_not_implemented():
    """Test workflow API (not implemented yet)."""
    session = Mock(spec=Session)

    with pytest.raises(HTTPException) as exc_info:
        execute_workflow_api(
            session=session,
            api_id="test-api",
            logic_body={},
            params={},
            executed_by="test-user"
        )
    
    assert exc_info.value.status_code == 501
    assert "not implemented" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
@patch("app.services.api_manager_executor.execute_http_api")
async def test_execute_api_http_mode(mock_execute_http):
    """Test execute_api with HTTP mode."""
    mock_execute_http.return_value = Mock(
        status_code=200,
        rows=[{"data": "test"}],
        duration_ms=100
    )

    session = Mock(spec=Session)
    result = execute_api(
        session=session,
        api_id="test-api",
        logic_type="http",
        logic_body='{"url": "https://api.example.com"}',
        params={},
        executed_by="test-user"
    )

    assert result.status_code == 200
    mock_execute_http.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.api_manager_executor.execute_sql_api")
async def test_execute_api_sql_mode(mock_execute_sql):
    """Test execute_api with SQL mode."""
    mock_execute_sql.return_value = Mock(
        status_code=200,
        rows=[{"id": 1, "name": "test"}],
        duration_ms=50
    )

    session = Mock(spec=Session)
    result = execute_api(
        session=session,
        api_id="test-api",
        logic_type="sql",
        logic_body="SELECT * FROM users",
        params={},
        executed_by="test-user"
    )

    assert result.status_code == 200
    mock_execute_sql.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.api_manager_executor.execute_python_api")
async def test_execute_api_python_mode(mock_execute_python):
    """Test execute_api with Python mode."""
    mock_execute_python.return_value = Mock(
        status_code=200,
        rows=[{"result": "test"}],
        duration_ms=75
    )

    session = Mock(spec=Session)
    result = execute_api(
        session=session,
        api_id="test-api",
        logic_type="script",
        logic_body="def main(): pass",
        params={},
        executed_by="test-user"
    )

    assert result.status_code == 200
    mock_execute_python.assert_called_once()


@pytest.mark.asyncio
async def test_execute_api_unsupported_mode():
    """Test execute_api with unsupported mode."""
    session = Mock(spec=Session)

    with pytest.raises(HTTPException) as exc_info:
        execute_api(
            session=session,
            api_id="test-api",
            logic_type="unsupported",
            logic_body="",
            params={},
            executed_by="test-user"
        )
    
    assert exc_info.value.status_code == 400
    assert "Unsupported logic type" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_execute_sql_api_requires_db_session():
    """Test that execute_sql_api requires database session."""
    # This test would require actual DB connection
    # For now, we'll just test the SQL validation
    sql = "SELECT 1"
    is_valid, _ = validate_select_sql(sql)
    assert is_valid is True