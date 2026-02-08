"""Scheduled regression testing service for automatic execution of golden queries."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from croniter import croniter
from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.redis import get_redis_client
from app.modules.inspector.crud import (
    create_regression_run,
    get_golden_query,
    get_latest_regression_baseline,
    list_regression_runs,
)
from app.modules.inspector.models import TbGoldenQuery, TbRegressionRun
from app.modules.ops.services.regression_executor import (
    compute_regression_diff,
    determine_judgment,
)
from app.modules.ops.services.orchestrator.orchestrator import handle_ops_query

logger = logging.getLogger(__name__)


class RegressionScheduler:
    """Schedules and executes regression tests for golden queries."""
    
    def __init__(self, redis_client=None):
        """Initialize the regression scheduler."""
        self.redis_client = redis_client or get_redis_client()
        self.is_running = False
        self.schedule_lock_key = "regression:scheduler:lock"
        
    async def start(self):
        """Start the scheduler in background."""
        if self.is_running:
            logger.warning("Regression scheduler is already running")
            return
            
        self.is_running = True
        logger.info("Starting regression scheduler")
        
        # Run scheduler loop
        while self.is_running:
            try:
                await self._schedule_iteration()
            except Exception as e:
                logger.error(f"Error in scheduler iteration: {e}", exc_info=True)
            
            # Sleep for 1 minute before next iteration
            await asyncio.sleep(60)
    
    def stop(self):
        """Stop the scheduler."""
        logger.info("Stopping regression scheduler")
        self.is_running = False
    
    async def _schedule_iteration(self):
        """Execute one iteration of the scheduler."""
        # Check if we have the schedule lock (distributed lock)
        if not await self._acquire_lock():
            logger.debug("Another scheduler instance is running")
            return
            
        try:
            # Get all enabled golden queries with schedules
            scheduled_queries = await self._get_scheduled_queries()
            
            for query in scheduled_queries:
                try:
                    await self._check_and_execute_query(query)
                except Exception as e:
                    logger.error(f"Failed to execute scheduled regression for query {query.id}: {e}", exc_info=True)
                    
        finally:
            await self._release_lock()
    
    async def _acquire_lock(self) -> bool:
        """Acquire distributed lock for scheduler execution."""
        try:
            # Try to set lock with 60 second TTL
            result = self.redis_client.set(
                self.schedule_lock_key,
                "locked",
                nx=True,
                ex=60
            )
            return bool(result)
        except Exception as e:
            logger.error(f"Failed to acquire scheduler lock: {e}")
            return False
    
    async def _release_lock(self):
        """Release distributed lock."""
        try:
            self.redis_client.delete(self.schedule_lock_key)
        except Exception as e:
            logger.error(f"Failed to release scheduler lock: {e}")
    
    async def _get_scheduled_queries(self) -> List[Dict[str, any]]:
        """Get all golden queries that have schedules enabled."""
        # This would query the database for queries with schedule info
        # For now, return a mock list - in production this would query TbGoldenQuery
        queries = []
        
        # TODO: Query database for scheduled queries
        # Example:
        # with Session(get_engine()) as session:
        #     result = session.exec(
        #         select(TbGoldenQuery).where(
        #             TbGoldenQuery.enabled == True,
        #             TbGoldenQuery.options.isnot(None)
        #         )
        #     )
        #     queries = result.all()
        
        return queries
    
    async def _check_and_execute_query(self, query: Dict[str, any]):
        """Check if query is due for execution and run regression test."""
        query_id = query.get("id")
        options = query.get("options", {})
        
        if not options or "schedule" not in options:
            return
            
        schedule_config = options["schedule"]
        cron_expression = schedule_config.get("cron_expression")
        
        if not cron_expression:
            return
            
        # Get last execution time
        last_run_key = f"regression:last_run:{query_id}"
        last_run_str = self.redis_client.get(last_run_key)
        
        # Determine if we should run now
        should_run = False
        if not last_run_str:
            # Never run before, run now
            should_run = True
        else:
            last_run = datetime.fromisoformat(last_run_str)
            # Parse cron expression and get next run time
            try:
                cron = croniter(cron_expression, last_run)
                next_run = cron.get_next(datetime.utcnow())
                
                # If next run time is in the past, run now
                if next_run <= datetime.utcnow():
                    should_run = True
            except Exception as e:
                logger.error(f"Invalid cron expression for query {query_id}: {e}")
        
        if should_run:
            logger.info(f"Executing scheduled regression for query {query_id}")
            await self._execute_regression(query_id)
            
            # Update last run time
            self.redis_client.set(
                last_run_key,
                datetime.utcnow().isoformat(),
                ex=86400  # 24 hours
            )
    
    async def _execute_regression(self, query_id: str):
        """Execute regression test for a golden query."""
        with Session(get_settings().database_url.replace("postgresql://", "postgresql+psycopg://")) as session:
            try:
                # Get golden query
                query = get_golden_query(session, query_id)
                if not query:
                    logger.error(f"Golden query not found: {query_id}")
                    return
                    
                # Get baseline
                baseline = get_latest_regression_baseline(session, query_id)
                if not baseline:
                    logger.warning(f"No baseline set for query {query_id}")
                    return
                    
                # Execute golden query
                answer_envelope = handle_ops_query(query.ops_type, query.query_text)
                
                # Compute regression diff
                baseline_trace = {"baseline": "placeholder"}  # TODO: Get actual baseline trace
                current_trace = answer_envelope.model_dump()
                
                diff = compute_regression_diff(
                    baseline_trace,
                    current_trace,
                    schedule_config=query.options.get("schedule", {})
                )
                
                # Determine judgment
                judgment = determine_judgment(diff)
                
                # Create regression run record
                run = create_regression_run(
                    session=session,
                    golden_query_id=query_id,
                    baseline_id=baseline.id,
                    status=judgment,
                    diff_summary=diff.get("summary", {}),
                    triggered_by="schedule",
                )
                
                session.commit()
                logger.info(f"Regression run completed for query {query_id}: {judgment}")
                
            except Exception as e:
                logger.error(f"Failed to execute regression for query {query_id}: {e}", exc_info=True)


# Global scheduler instance
regression_scheduler = RegressionScheduler()


async def run_scheduled_regressions(session: Session, golden_query_id: str):
    """
    Execute regression test for a golden query (called from API endpoint).
    
    This is the entry point for API-triggered regression runs.
    """
    try:
        query = get_golden_query(session, golden_query_id)
        if not query:
            return {"success": False, "error": "Golden query not found"}
            
        baseline = get_latest_regression_baseline(session, golden_query_id)
        if not baseline:
            return {"success": False, "error": "No baseline set"}
            
        # Execute query
        answer_envelope = handle_ops_query(query.ops_type, query.query_text)
        
        # Compute diff
        baseline_trace = {"baseline": "placeholder"}  # TODO: Get actual baseline trace
        current_trace = answer_envelope.model_dump()
        
        diff = compute_regression_diff(
            baseline_trace,
            current_trace,
            schedule_config=query.options.get("schedule", {})
        )
        
        judgment = determine_judgment(diff)
        
        # Create run record
        run = create_regression_run(
            session=session,
            golden_query_id=golden_query_id,
            baseline_id=baseline.id,
            status=judgment,
            diff_summary=diff.get("summary", {}),
            triggered_by="api",
        )
        
        session.commit()
        
        return {
            "success": True,
            "run_id": run.id,
            "judgment": judgment,
            "diff": diff
        }
        
    except Exception as e:
        logger.error(f"Failed to run regression: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def parse_cron_expression(cron_str: str) -> Optional[croniter]:
    """
    Parse cron expression string.
    
    Examples:
        - "0 * * * *" - Every hour
        - "0 */6 * * *" - Every 6 hours
        - "0 0 * * *" - Every day at midnight
        - "0 0 * * 0" - Every Sunday at midnight
        - "0 0 1 * *" - Every 1st of month at midnight
    """
    try:
        return croniter(cron_str)
    except Exception as e:
        logger.error(f"Invalid cron expression: {cron_str}, error: {e}")
        return None


def validate_schedule_config(schedule_config: Dict[str, any]) -> tuple[bool, str]:
    """
    Validate schedule configuration.
    
    Args:
        schedule_config: Dictionary with schedule configuration
        
    Returns:
        (is_valid, error_message)
    """
    if not isinstance(schedule_config, dict):
        return False, "Schedule config must be a dictionary"
        
    cron_expression = schedule_config.get("cron_expression")
    if not cron_expression:
        return False, "cron_expression is required"
        
    if not isinstance(cron_expression, str):
        return False, "cron_expression must be a string"
        
    cron = parse_cron_expression(cron_expression)
    if cron is None:
        return False, f"Invalid cron expression: {cron_expression}"
        
    return True, ""


def get_next_run_time(cron_expression: str, from_time: datetime = None) -> Optional[datetime]:
    """
    Get next run time for a cron expression.
    
    Args:
        cron_expression: Cron expression string
        from_time: Reference time for calculation (defaults to current UTC time)
        
    Returns:
        Next run time or None if invalid expression
    """
    if from_time is None:
        from_time = datetime.utcnow()
        
    cron = parse_cron_expression(cron_expression)
    if cron is None:
        return None
        
    return cron.get_next(from_time)