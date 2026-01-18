"""API Manager routes for dynamic API management"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from core.auth import get_current_user
from .services.sql_validator import SQLValidator
from .services.api_service import ApiManagerService
from .services.test_runner import ApiTestRunner

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api-manager", tags=["api-manager"])

# Initialize services
sql_validator = SQLValidator()
api_service = ApiManagerService(sql_validator=sql_validator)
test_runner = ApiTestRunner(api_service=api_service)


class CreateApiRequest(BaseModel):
    """Request to create new API"""

    name: str
    method: str
    path: str
    mode: str  # sql, python, workflow
    logic: str
    scope: str = "custom"
    input_schema: dict = {}
    output_schema: dict = {}
    description: Optional[str] = None


class UpdateApiRequest(BaseModel):
    """Request to update API"""

    name: Optional[str] = None
    logic: Optional[str] = None
    input_schema: Optional[dict] = None
    output_schema: Optional[dict] = None
    description: Optional[str] = None


class ExecuteApiRequest(BaseModel):
    """Request to execute API"""

    params: dict = {}


@router.post("/create", response_model=dict)
async def create_api(
    request: CreateApiRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create new dynamic API

    Modes:
    - sql: Execute SQL queries
    - python: Execute Python code
    - workflow: Compose tools

    Returns created API definition with version 1
    """

    try:
        api = await api_service.create_api(request.dict(), current_user)

        return {
            "status": "ok",
            "data": api
        }

    except Exception as e:
        logger.error(f"Create API failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/{api_id}", response_model=dict)
async def get_api(
    api_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get API definition"""

    try:
        # In real implementation: db.get(ApiDefinition, api_id)
        api = {
            "id": api_id,
            "name": "Example API",
            "version": 1,
            "status": "active"
        }

        return {
            "status": "ok",
            "data": api
        }

    except Exception as e:
        logger.error(f"Get API failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.put("/{api_id}", response_model=dict)
async def update_api(
    api_id: str,
    request: UpdateApiRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update API with version tracking

    Creates new version on update
    """

    try:
        api = await api_service.update_api(api_id, request.dict(exclude_none=True), current_user)

        return {
            "status": "ok",
            "data": api
        }

    except Exception as e:
        logger.error(f"Update API failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/{api_id}/rollback", response_model=dict)
async def rollback_api(
    api_id: str,
    target_version: int = Query(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Rollback API to previous version

    Args:
        api_id: API ID
        target_version: Version to rollback to
    """

    try:
        api = await api_service.rollback_api(api_id, target_version, current_user)

        return {
            "status": "ok",
            "message": f"Rolled back to version {target_version}",
            "data": api
        }

    except Exception as e:
        logger.error(f"Rollback failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/{api_id}/versions", response_model=dict)
async def get_versions(
    api_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get version history"""

    try:
        versions = await api_service.get_api_versions(api_id)

        return {
            "status": "ok",
            "api_id": api_id,
            "versions": versions
        }

    except Exception as e:
        logger.error(f"Get versions failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/{api_id}/validate-sql", response_model=dict)
async def validate_sql(
    api_id: str,
    sql: str = Query(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Validate SQL query

    Checks for:
    - Security issues (dangerous keywords, SQL injection)
    - Table access permissions
    - Performance problems
    """

    try:
        validation = sql_validator.validate(sql)

        return {
            "status": "ok",
            "is_safe": validation.is_safe,
            "is_valid": validation.is_valid,
            "errors": validation.errors,
            "warnings": validation.warnings,
            "metadata": validation.metadata
        }

    except Exception as e:
        logger.error(f"SQL validation failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/{api_id}/execute", response_model=dict)
async def execute_api(
    api_id: str,
    request: ExecuteApiRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Execute API with parameters

    Returns result data and execution metadata
    """

    try:
        result = await api_service.execute_api(api_id, request.params, current_user)

        return {
            "status": "ok" if result.get("status") == "success" else "error",
            "data": result
        }

    except Exception as e:
        logger.error(f"API execution failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/{api_id}/test", response_model=dict)
async def run_tests(
    api_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Run all tests for API

    Returns test results summary
    """

    try:
        test_result = await test_runner.run_tests(api_id)

        return {
            "status": "ok",
            "api_id": api_id,
            "total": test_result.total,
            "passed": test_result.passed,
            "failed": test_result.failed,
            "errors": test_result.errors,
            "results": [
                {
                    "test_id": r.test_id,
                    "status": r.status,
                    "error": r.error_message
                }
                for r in test_result.results
            ]
        }

    except Exception as e:
        logger.error(f"Test execution failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/{api_id}/execution-logs", response_model=dict)
async def get_logs(
    api_id: str,
    limit: int = Query(50, ge=1, le=500),
    current_user: dict = Depends(get_current_user)
):
    """Get API execution history"""

    try:
        logs = await api_service.get_execution_logs(api_id, limit)

        return {
            "status": "ok",
            "api_id": api_id,
            "logs": logs
        }

    except Exception as e:
        logger.error(f"Get logs failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.delete("/{api_id}", response_model=dict)
async def delete_api(
    api_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete API (soft delete)"""

    try:
        # In real implementation: mark as deleted in DB

        return {
            "status": "ok",
            "message": f"API {api_id} deleted"
        }

    except Exception as e:
        logger.error(f"Delete failed: {str(e)}")
        raise HTTPException(500, str(e))
