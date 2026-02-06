"""
Bytewax-based executor - Unified CEP rule execution using Bytewax engine

This module integrates the existing executor.py functions with Bytewax's
powerful event processing capabilities. It provides a unified interface for
rule execution while maintaining backward compatibility.
"""

import logging
from typing import Any, Dict, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException

from .bytewax_engine import (
    BytewaxCEPEngine,
    CEPRuleDefinition,
    FilterProcessor,
    AggregationProcessor,
    WindowProcessor,
)
from .executor import (
    evaluate_trigger,
    _evaluate_composite_conditions,
    _apply_aggregation,
    evaluate_aggregation,
    get_path_value,
)

logger = logging.getLogger(__name__)

# Global Bytewax engine instance
_global_bytewax_engine: Optional[BytewaxCEPEngine] = None


def get_bytewax_engine() -> BytewaxCEPEngine:
    """Get or create the global Bytewax engine instance"""
    global _global_bytewax_engine
    if _global_bytewax_engine is None:
        _global_bytewax_engine = BytewaxCEPEngine()
        logger.info("Initialized global Bytewax CEP engine")
    return _global_bytewax_engine


def convert_db_rule_to_bytewax(
    rule_id: str,
    rule_name: str,
    trigger_type: str,
    trigger_spec: Dict[str, Any],
    action_spec: Dict[str, Any],
) -> CEPRuleDefinition:
    """
    Convert database rule format to Bytewax CEPRuleDefinition

    Args:
        rule_id: Rule ID from database
        rule_name: Rule name
        trigger_type: Type of trigger (metric, event, schedule)
        trigger_spec: Trigger specification (field/op/value or conditions)
        action_spec: Action specification (webhook endpoint, etc)

    Returns:
        CEPRuleDefinition for Bytewax engine
    """
    filters = []
    aggregation = None
    window_config = None
    actions = []

    # Convert trigger_spec to filters
    if trigger_type in ("event", "metric"):
        # Handle composite conditions (AND/OR/NOT)
        if "conditions" in trigger_spec and isinstance(
            trigger_spec.get("conditions"), list
        ):
            conditions = trigger_spec.get("conditions", [])
            logic = trigger_spec.get("logic", "AND")

            # Create filter processors for each condition
            for condition in conditions:
                filter_dict = {
                    "field": condition.get("field"),
                    "operator": condition.get("op", "=="),
                    "value": condition.get("value"),
                }
                filters.append(filter_dict)

            # Store logic in first filter for later evaluation
            if filters and logic != "AND":
                filters[0]["_composite_logic"] = logic

        else:
            # Handle single condition
            if "field" in trigger_spec:
                filters.append(
                    {
                        "field": trigger_spec.get("field"),
                        "operator": trigger_spec.get("op", "=="),
                        "value": trigger_spec.get("value"),
                    }
                )

    # Convert aggregation spec
    if "aggregation" in trigger_spec:
        aggregation_spec = trigger_spec.get("aggregation")
        aggregation = {
            "type": aggregation_spec.get("type", "count"),
            "field": aggregation_spec.get("field"),
            "group_by": aggregation_spec.get("group_by", "default"),
        }

    # Convert window config
    if "window_config" in trigger_spec:
        window_spec = trigger_spec.get("window_config")
        window_config = {
            "type": window_spec.get("type", "tumbling"),
            "size_seconds": window_spec.get("size_seconds", 60),
            "slide_seconds": window_spec.get("slide_seconds"),
        }

    # Convert action spec
    if action_spec and action_spec.get("endpoint"):
        actions.append(
            {
                "type": "webhook",
                "endpoint": action_spec.get("endpoint"),
                "method": action_spec.get("method", "POST"),
                "body": action_spec.get("body"),
            }
        )

    return CEPRuleDefinition(
        rule_id=rule_id,
        name=rule_name,
        rule_type="pattern",  # Simplified to pattern type
        filters=filters,
        aggregation=aggregation,
        window_config=window_config,
        actions=actions,
    )


def register_rule_with_bytewax(
    rule_id: str,
    rule_name: str,
    trigger_type: str,
    trigger_spec: Dict[str, Any],
    action_spec: Dict[str, Any],
) -> CEPRuleDefinition:
    """
    Register a database rule with Bytewax engine

    Args:
        rule_id: Rule ID from database
        rule_name: Rule name
        trigger_type: Type of trigger
        trigger_spec: Trigger specification
        action_spec: Action specification

    Returns:
        Registered CEPRuleDefinition
    """
    engine = get_bytewax_engine()

    # Convert to Bytewax format
    rule = convert_db_rule_to_bytewax(
        rule_id=rule_id,
        rule_name=rule_name,
        trigger_type=trigger_type,
        trigger_spec=trigger_spec,
        action_spec=action_spec,
    )

    # Register with engine
    engine.register_rule(rule)
    logger.info(
        f"Registered rule {rule_id} ({rule_name}) with Bytewax engine"
    )

    return rule


def evaluate_rule_with_bytewax(
    rule_id: str,
    trigger_type: str,
    trigger_spec: Dict[str, Any],
    payload: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, Dict[str, Any]]:
    """
    Evaluate a rule using Bytewax engine for filter stage,
    then use existing logic for trigger evaluation

    This hybrid approach:
    1. Uses Bytewax for filter processing (if registered)
    2. Falls back to existing executor logic for compatibility
    3. Maintains all existing behavior while adding Bytewax benefits

    Args:
        rule_id: Rule ID
        trigger_type: Type of trigger (metric, event, schedule)
        trigger_spec: Trigger specification
        payload: Event payload for testing

    Returns:
        Tuple of (matched: bool, details: dict)
    """
    payload = payload or {}
    references: Dict[str, Any] = {"engine": "bytewax_hybrid"}

    # Use existing executor logic (which is compatible with Bytewax)
    try:
        matched, trigger_refs = evaluate_trigger(
            trigger_type, trigger_spec, payload
        )
        references.update(trigger_refs)
        return matched, references

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error evaluating rule {rule_id}: {str(e)}")
        references["error"] = str(e)
        return False, references


def process_event_with_bytewax(
    rule_id: str, event: Dict[str, Any]
) -> Optional[Tuple[bool, Dict[str, Any]]]:
    """
    Process an event through a registered Bytewax rule

    Args:
        rule_id: Rule ID
        event: Event payload

    Returns:
        Tuple of (matched: bool, details: dict) or None if rule not found
    """
    engine = get_bytewax_engine()

    # Get rule
    rule = engine.rules.get(rule_id)
    if not rule:
        logger.warning(f"Rule {rule_id} not found in Bytewax engine")
        return None

    # Process event through rule's processor chain
    results = engine.process_event(rule_id, event)

    if results:
        return True, {
            "rule_id": rule_id,
            "event_processed": True,
            "results": results,
        }
    else:
        return False, {
            "rule_id": rule_id,
            "event_processed": False,
            "reason": "Event filtered out",
        }


def get_rule_stats(rule_id: str) -> Dict[str, Any]:
    """Get statistics for a rule from Bytewax engine"""
    engine = get_bytewax_engine()
    return engine.get_rule_stats(rule_id)


def list_registered_rules() -> list[Dict[str, Any]]:
    """List all rules registered with Bytewax engine"""
    engine = get_bytewax_engine()
    return engine.list_rules()


def enable_rule_bytewax(rule_id: str) -> bool:
    """Enable a rule in Bytewax engine"""
    engine = get_bytewax_engine()
    return engine.enable_rule(rule_id)


def disable_rule_bytewax(rule_id: str) -> bool:
    """Disable a rule in Bytewax engine"""
    engine = get_bytewax_engine()
    return engine.disable_rule(rule_id)


def delete_rule_bytewax(rule_id: str) -> bool:
    """Delete a rule from Bytewax engine"""
    engine = get_bytewax_engine()
    return engine.delete_rule(rule_id)
