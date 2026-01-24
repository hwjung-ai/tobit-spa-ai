"""CEP Engine API routes for rule management, execution, and monitoring"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.auth import get_current_user
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from .bytewax_engine import BytewaxCEPEngine, CEPRuleDefinition
from .notification_channels import NotificationService
from .rule_monitor import RulePerformanceMonitor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cep", tags=["cep"])

# Initialize services
cep_engine = BytewaxCEPEngine()
notification_service = NotificationService()
performance_monitor = RulePerformanceMonitor()


class CreateRuleRequest(BaseModel):
    """Request for creating a CEP rule"""

    name: str
    rule_type: str  # pattern, aggregation, windowing, enrichment
    description: Optional[str] = None
    filters: Optional[List[Dict[str, Any]]] = None
    aggregation: Optional[Dict[str, Any]] = None
    window_config: Optional[Dict[str, Any]] = None
    enrichment: Optional[List[Dict[str, Any]]] = None
    actions: Optional[List[Dict[str, Any]]] = None


class RuleResponse(BaseModel):
    """Response for CEP rule"""

    rule_id: str
    name: str
    rule_type: str
    created_at: str


class ExecuteRuleRequest(BaseModel):
    """Request for executing a rule with event"""

    event: Dict[str, Any]


class ProcessEventRequest(BaseModel):
    """Request for processing an event through a rule"""

    event: Dict[str, Any]


class NotificationChannelRequest(BaseModel):
    """Request for registering a notification channel"""

    channel_id: str
    channel_type: str  # slack, email, sms, webhook
    config: Dict[str, Any]


class PerformanceStatsResponse(BaseModel):
    """Response for rule performance statistics"""

    rule_id: str
    total_executions: int
    avg_execution_time_ms: float
    success_rate: float
    total_errors: int


@router.post("/rules", response_model=RuleResponse)
async def create_rule(
    request: CreateRuleRequest, current_user: dict = Depends(get_current_user)
):
    """
    Create a new CEP rule

    Rule Types:
    - pattern: Pattern matching on event sequences
    - aggregation: Group and aggregate metrics
    - windowing: Time-based event windows
    - enrichment: Enhance events with additional data

    Each rule can have:
    - Filters: Conditions to match
    - Aggregation: Group by and aggregate specs
    - Windows: Tumbling or sliding windows
    - Enrichment: Data lookup or calculation
    - Actions: Notifications or storage
    """

    try:
        if not request.name or len(request.name.strip()) < 2:
            raise HTTPException(400, "Rule name must be at least 2 characters")

        if request.rule_type not in [
            "pattern",
            "aggregation",
            "windowing",
            "enrichment",
        ]:
            raise HTTPException(
                400, "Rule type must be: pattern, aggregation, windowing, or enrichment"
            )

        logger.info(
            f"Creating CEP rule: {request.name} (type: {request.rule_type}), "
            f"user: {current_user.get('id')}"
        )

        # In real implementation:
        # - Validate filter/aggregation/window configs
        # - Save rule to database
        # - Register with CEP engine

        # Create rule (placeholder ID)
        rule_id = f"rule_{datetime.utcnow().isoformat().replace(':', '-')}"
        rule = CEPRuleDefinition(
            rule_id=rule_id,
            name=request.name,
            rule_type=request.rule_type,
            filters=request.filters,
            aggregation=request.aggregation,
            window_config=request.window_config,
            enrichment=request.enrichment,
            actions=request.actions,
        )

        cep_engine.register_rule(rule)

        return {
            "rule_id": rule_id,
            "name": request.name,
            "rule_type": request.rule_type,
            "created_at": rule.created_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create rule: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/rules/{rule_id}", response_model=RuleResponse)
async def get_rule(rule_id: str, current_user: dict = Depends(get_current_user)):
    """Get CEP rule details"""

    try:
        logger.info(f"Fetching rule: {rule_id}")

        # In real implementation: fetch from database
        rule = cep_engine.rules.get(rule_id)
        if not rule:
            raise HTTPException(404, f"Rule not found: {rule_id}")

        return {
            "rule_id": rule.rule_id,
            "name": rule.name,
            "rule_type": rule.rule_type,
            "created_at": rule.created_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get rule: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/rules/{rule_id}/execute")
async def execute_rule(
    rule_id: str,
    request: ExecuteRuleRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Execute a CEP rule with an event

    Process event through rule's:
    - Filters
    - Aggregations
    - Windows
    - Enrichments
    - Actions
    """

    try:
        logger.info(f"Executing rule {rule_id} with event")

        rule = cep_engine.rules.get(rule_id)
        if not rule:
            raise HTTPException(404, f"Rule not found: {rule_id}")

        # Process event through the rule
        results = cep_engine.process_event(rule_id, request.event)

        if not results:
            return {
                "status": "ok",
                "rule_id": rule_id,
                "matched": False,
                "results": [],
                "message": "Event did not match rule conditions",
            }

        # Execute actions for matched events
        action_results = cep_engine.execute_actions(rule_id, results)

        return {
            "status": "ok",
            "rule_id": rule_id,
            "matched": True,
            "matched_count": len(results),
            "results": results,
            "actions": action_results,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rule execution failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/rules", response_model=dict)
async def list_rules(current_user: dict = Depends(get_current_user)):
    """List all CEP rules"""

    try:
        logger.info("Listing CEP rules")

        rules = cep_engine.list_rules()

        return {
            "status": "ok",
            "total": len(rules),
            "rules": rules,
        }

    except Exception as e:
        logger.error(f"Failed to list rules: {str(e)}")
        raise HTTPException(500, str(e))


@router.delete("/rules/{rule_id}", response_model=dict)
async def delete_rule(rule_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a CEP rule"""

    try:
        logger.info(f"Deleting rule: {rule_id}")

        if not cep_engine.delete_rule(rule_id):
            raise HTTPException(404, f"Rule not found: {rule_id}")

        return {"status": "ok", "message": f"Rule {rule_id} deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/rules/{rule_id}/disable", response_model=dict)
async def disable_rule(rule_id: str, current_user: dict = Depends(get_current_user)):
    """Disable a CEP rule"""

    try:
        logger.info(f"Disabling rule: {rule_id}")

        if not cep_engine.disable_rule(rule_id):
            raise HTTPException(404, f"Rule not found: {rule_id}")

        return {"status": "ok", "message": f"Rule {rule_id} disabled"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Disable failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/rules/{rule_id}/enable", response_model=dict)
async def enable_rule(rule_id: str, current_user: dict = Depends(get_current_user)):
    """Enable a CEP rule"""

    try:
        logger.info(f"Enabling rule: {rule_id}")

        if not cep_engine.enable_rule(rule_id):
            raise HTTPException(404, f"Rule not found: {rule_id}")

        return {"status": "ok", "message": f"Rule {rule_id} enabled"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Enable failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/notifications/channels", response_model=dict)
async def register_notification_channel(
    request: NotificationChannelRequest, current_user: dict = Depends(get_current_user)
):
    """
    Register a notification channel

    Channel Types:
    - slack: Slack webhook
    - email: SMTP email
    - sms: Twilio SMS
    - webhook: Generic HTTP webhook
    """

    try:
        logger.info(
            f"Registering notification channel: {request.channel_id} "
            f"(type: {request.channel_type})"
        )

        if not notification_service.register_channel_from_config(
            request.channel_id, request.channel_type, request.config
        ):
            raise HTTPException(
                400,
                f"Failed to register {request.channel_type} channel. Check configuration.",
            )

        return {
            "status": "ok",
            "channel_id": request.channel_id,
            "channel_type": request.channel_type,
            "message": "Notification channel registered",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Channel registration failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/notifications/channels", response_model=dict)
async def list_notification_channels(current_user: dict = Depends(get_current_user)):
    """List registered notification channels"""

    try:
        channels = notification_service.list_channels()

        return {
            "status": "ok",
            "total": len(channels),
            "channels": channels,
        }

    except Exception as e:
        logger.error(f"Failed to list channels: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/performance/{rule_id}", response_model=dict)
async def get_rule_performance(
    rule_id: str,
    time_range_minutes: int = Query(60, ge=1, le=1440),
    current_user: dict = Depends(get_current_user),
):
    """
    Get rule performance statistics

    Shows:
    - Execution count and average time
    - Min/max/p95/p99 execution times
    - Events processed and matched
    - Success rate and error count
    """

    try:
        logger.info(f"Getting performance stats for rule {rule_id}")

        stats = performance_monitor.get_rule_performance(rule_id, time_range_minutes)

        return {
            "status": "ok",
            "rule_id": rule_id,
            "time_range_minutes": time_range_minutes,
            "stats": stats.to_dict(),
        }

    except Exception as e:
        logger.error(f"Failed to get performance stats: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/performance", response_model=dict)
async def get_all_performance_stats(current_user: dict = Depends(get_current_user)):
    """Get performance statistics for all rules"""

    try:
        logger.info("Getting performance stats for all rules")

        all_stats = performance_monitor.get_all_performance_stats()

        return {
            "status": "ok",
            "total_rules": len(all_stats),
            "stats": [s.to_dict() for s in all_stats],
        }

    except Exception as e:
        logger.error(f"Failed to get all performance stats: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/health", response_model=dict)
async def get_system_health(current_user: dict = Depends(get_current_user)):
    """Get overall CEP system health"""

    try:
        logger.info("Getting system health status")

        health = performance_monitor.get_system_health()

        return {
            "status": "ok",
            "health": health,
        }

    except Exception as e:
        logger.error(f"Failed to get health status: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/{rule_id}/errors", response_model=dict)
async def get_rule_errors(
    rule_id: str,
    limit: int = Query(50, ge=1, le=500),
    current_user: dict = Depends(get_current_user),
):
    """Get recent errors for a rule"""

    try:
        logger.info(f"Getting errors for rule {rule_id}")

        errors = performance_monitor.get_rule_errors(rule_id, limit)

        return {
            "status": "ok",
            "rule_id": rule_id,
            "error_count": len(errors),
            "errors": errors,
        }

    except Exception as e:
        logger.error(f"Failed to get rule errors: {str(e)}")
        raise HTTPException(500, str(e))
