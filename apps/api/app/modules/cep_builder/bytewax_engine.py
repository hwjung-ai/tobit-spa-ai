"""Bytewax-based Complex Event Processing engine for Rule composition and pattern matching"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CEPRuleDefinition:
    """CEP Rule Definition for Bytewax processing"""

    def __init__(
        self,
        rule_id: str,
        name: str,
        rule_type: str,  # "pattern", "aggregation", "windowing", "enrichment"
        filters: Optional[List[dict]] = None,
        aggregation: Optional[dict] = None,
        window_config: Optional[dict] = None,
        enrichment: Optional[List[dict]] = None,
        actions: Optional[List[dict]] = None,
    ):
        self.rule_id = rule_id
        self.name = name
        self.rule_type = rule_type
        self.filters = filters or []
        self.aggregation = aggregation
        self.window_config = window_config
        self.enrichment = enrichment or []
        self.actions = actions or []
        self.created_at = datetime.utcnow()


class EventProcessor(ABC):
    """Base class for event processing stages"""

    @abstractmethod
    def process(self, event: dict, context: dict) -> Optional[dict]:
        """Process event and return result or None to filter out"""
        pass


class FilterProcessor(EventProcessor):
    """Filter events based on conditions"""

    def __init__(self, filters: List[dict]):
        self.filters = filters

    def process(self, event: dict, context: dict) -> Optional[dict]:
        """Apply all filters to event"""
        for filter_spec in self.filters:
            if not self._evaluate_filter(event, filter_spec):
                return None
        return event

    def _evaluate_filter(self, event: dict, filter_spec: dict) -> bool:
        """Evaluate a single filter expression"""
        field = filter_spec.get("field")
        operator = filter_spec.get("operator")
        value = filter_spec.get("value")

        event_value = event.get(field)
        if event_value is None:
            return False

        match operator:
            case "==":
                return event_value == value
            case "!=":
                return event_value != value
            case ">":
                try:
                    return float(event_value) > float(value)
                except (ValueError, TypeError):
                    return False
            case ">=":
                try:
                    return float(event_value) >= float(value)
                except (ValueError, TypeError):
                    return False
            case "<":
                try:
                    return float(event_value) < float(value)
                except (ValueError, TypeError):
                    return False
            case "<=":
                try:
                    return float(event_value) <= float(value)
                except (ValueError, TypeError):
                    return False
            case "in":
                return event_value in value
            case "contains":
                return str(value) in str(event_value)
            case _:
                return False


class AggregationProcessor(EventProcessor):
    """Aggregate events based on configuration"""

    def __init__(self, aggregation_spec: dict):
        self.aggregation_spec = aggregation_spec
        self.state: Dict[str, Any] = {}

    def process(self, event: dict, context: dict) -> Optional[dict]:
        """Apply aggregation to event"""
        group_by_field = self.aggregation_spec.get("group_by")
        agg_type = self.aggregation_spec.get("type")  # count, sum, avg, min, max
        metric_field = self.aggregation_spec.get("field")

        # Get group key
        group_key = event.get(group_by_field, "default")
        if group_key not in self.state:
            self.state[group_key] = {
                "count": 0,
                "sum": 0,
                "values": [],
                "min": float("inf"),
                "max": float("-inf"),
            }

        state = self.state[group_key]

        # Update state
        state["count"] += 1
        if metric_field and metric_field in event:
            try:
                metric_value = float(event[metric_field])
                state["sum"] += metric_value
                state["values"].append(metric_value)
                state["min"] = min(state["min"], metric_value)
                state["max"] = max(state["max"], metric_value)
            except (ValueError, TypeError):
                pass

        # Calculate aggregated value based on type
        if agg_type == "count":
            return {
                "group": group_key,
                "aggregated_value": state["count"],
                "aggregation_type": "count",
            }
        elif agg_type == "sum":
            return {
                "group": group_key,
                "aggregated_value": state["sum"],
                "aggregation_type": "sum",
            }
        elif agg_type == "avg":
            avg = state["sum"] / state["count"] if state["count"] > 0 else 0
            return {
                "group": group_key,
                "aggregated_value": avg,
                "aggregation_type": "avg",
            }
        elif agg_type == "min":
            return {
                "group": group_key,
                "aggregated_value": state["min"],
                "aggregation_type": "min",
            }
        elif agg_type == "max":
            return {
                "group": group_key,
                "aggregated_value": state["max"],
                "aggregation_type": "max",
            }

        return None


class WindowProcessor(EventProcessor):
    """Window events for time-based aggregation"""

    def __init__(self, window_config: dict):
        self.window_config = window_config
        self.window_type = window_config.get("type")  # tumbling, sliding
        self.window_size_seconds = window_config.get("size_seconds")
        self.slide_seconds = window_config.get("slide_seconds")
        self.windows: Dict[int, List[dict]] = {}

    def process(self, event: dict, context: dict) -> Optional[dict]:
        """Add event to appropriate window(s)"""
        now = datetime.utcnow()
        timestamp = event.get("timestamp", now)

        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp)
            except (ValueError, TypeError):
                timestamp = now

        window_id = int(timestamp.timestamp() // self.window_size_seconds)

        if window_id not in self.windows:
            self.windows[window_id] = []

        self.windows[window_id].append(event)

        # Return windowed events
        return {
            "window_id": window_id,
            "events": self.windows[window_id],
            "event_count": len(self.windows[window_id]),
            "window_type": self.window_type,
        }


class EnrichmentProcessor(EventProcessor):
    """Enrich events with additional data"""

    def __init__(self, enrichment_specs: List[dict]):
        self.enrichment_specs = enrichment_specs

    def process(self, event: dict, context: dict) -> Optional[dict]:
        """Enrich event with additional data"""
        enriched = event.copy()

        for enrichment_spec in self.enrichment_specs:
            enrichment_type = enrichment_spec.get("type")

            if enrichment_type == "lookup":
                # In production: lookup from database or cache
                lookup_key = enrichment_spec.get("key")
                lookup_table = enrichment_spec.get("table")
                enriched[f"{lookup_key}_enriched"] = f"lookup_{lookup_table}"

            elif enrichment_type == "calculate":
                # Calculate derived field
                field_name = enrichment_spec.get("name")
                enrichment_spec.get("formula")
                # Simple field mapping for now
                enriched[field_name] = "calculated_value"

        return enriched


class BytewaxCEPEngine:
    """Bytewax-based Complex Event Processing Engine"""

    def __init__(self):
        self.rules: Dict[str, CEPRuleDefinition] = {}
        self.processors: Dict[str, List[EventProcessor]] = {}
        self.dataflows: Dict[str, Dict] = {}
        self.state_store: Dict[str, Any] = {}

    def register_rule(self, rule: CEPRuleDefinition) -> None:
        """Register a new CEP rule"""
        self.rules[rule.rule_id] = rule
        self._create_processor_chain(rule)
        logger.info(f"Registered CEP rule: {rule.rule_id} ({rule.name})")

    def _create_processor_chain(self, rule: CEPRuleDefinition) -> None:
        """Create processor chain for rule"""
        processors: List[EventProcessor] = []

        # Add filter processor if filters exist
        if rule.filters:
            processors.append(FilterProcessor(rule.filters))

        # Add aggregation processor if aggregation is specified
        if rule.aggregation:
            processors.append(AggregationProcessor(rule.aggregation))

        # Add window processor if windowing is configured
        if rule.window_config:
            processors.append(WindowProcessor(rule.window_config))

        # Add enrichment processor if enrichment is specified
        if rule.enrichment:
            processors.append(EnrichmentProcessor(rule.enrichment))

        self.processors[rule.rule_id] = processors
        logger.debug(f"Created processor chain for rule {rule.rule_id} with {len(processors)} stages")

    def process_event(self, rule_id: str, event: dict) -> Optional[List[dict]]:
        """Process event through rule's processor chain"""
        if rule_id not in self.rules:
            logger.warning(f"Rule {rule_id} not found")
            return None

        processors = self.processors.get(rule_id, [])
        context = {"rule_id": rule_id, "processed_at": datetime.utcnow()}
        results = [event]

        for processor in processors:
            new_results = []
            for result in results:
                processed = processor.process(result, context)
                if processed is not None:
                    new_results.append(processed)
            results = new_results

        return results if results else None

    def execute_actions(
        self,
        rule_id: str,
        matched_events: List[dict]
    ) -> List[Dict[str, Any]]:
        """Execute actions for matched events"""
        rule = self.rules.get(rule_id)
        if not rule:
            return []

        action_results = []

        for action in rule.actions:
            action_type = action.get("type")

            if action_type == "notify":
                # Return notification payload (actual sending handled elsewhere)
                action_results.append({
                    "type": "notification",
                    "channels": action.get("channels"),
                    "message": action.get("message"),
                    "events_count": len(matched_events),
                })

            elif action_type == "store":
                # Return storage payload
                action_results.append({
                    "type": "storage",
                    "table": action.get("table"),
                    "events": matched_events,
                })

            elif action_type == "trigger":
                # Return trigger payload
                action_results.append({
                    "type": "trigger",
                    "target_rule_id": action.get("target_rule_id"),
                    "events": matched_events,
                })

        return action_results

    def get_rule_stats(self, rule_id: str) -> Dict[str, Any]:
        """Get statistics for a rule"""
        rule = self.rules.get(rule_id)
        if not rule:
            return {}

        state = self.state_store.get(rule_id, {})

        return {
            "rule_id": rule_id,
            "name": rule.name,
            "type": rule.rule_type,
            "created_at": rule.created_at.isoformat(),
            "events_processed": state.get("events_processed", 0),
            "events_matched": state.get("events_matched", 0),
            "last_execution": state.get("last_execution"),
            "error_count": state.get("error_count", 0),
        }

    def disable_rule(self, rule_id: str) -> bool:
        """Disable a rule"""
        if rule_id in self.rules:
            # Mark as disabled in state
            if rule_id not in self.state_store:
                self.state_store[rule_id] = {}
            self.state_store[rule_id]["enabled"] = False
            logger.info(f"Disabled rule: {rule_id}")
            return True
        return False

    def enable_rule(self, rule_id: str) -> bool:
        """Enable a rule"""
        if rule_id in self.rules:
            if rule_id not in self.state_store:
                self.state_store[rule_id] = {}
            self.state_store[rule_id]["enabled"] = True
            logger.info(f"Enabled rule: {rule_id}")
            return True
        return False

    def delete_rule(self, rule_id: str) -> bool:
        """Delete a rule"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            if rule_id in self.processors:
                del self.processors[rule_id]
            if rule_id in self.state_store:
                del self.state_store[rule_id]
            logger.info(f"Deleted rule: {rule_id}")
            return True
        return False

    def list_rules(self) -> List[Dict[str, Any]]:
        """List all registered rules"""
        return [
            {
                "rule_id": rule.rule_id,
                "name": rule.name,
                "type": rule.rule_type,
                "created_at": rule.created_at.isoformat(),
            }
            for rule in self.rules.values()
        ]
