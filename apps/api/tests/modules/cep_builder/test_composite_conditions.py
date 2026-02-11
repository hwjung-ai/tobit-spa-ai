"""Test composite condition evaluation in executor.py"""

import pytest
from app.modules.cep_builder.executor import (
    _evaluate_composite_conditions,
    _evaluate_event_trigger,
    _evaluate_single_condition,
)


class TestSingleCondition:
    """Test single condition evaluation"""

    def test_single_condition_gt_match(self):
        """Test greater than operator matching"""
        condition = {"field": "cpu", "op": ">", "value": 80}
        payload = {"cpu": 85}
        matched, refs = _evaluate_single_condition(condition, payload)
        assert matched is True
        assert refs["condition_evaluated"] is True
        assert refs["actual"] == 85.0
        assert refs["expected"] == 80.0

    def test_single_condition_gt_no_match(self):
        """Test greater than operator not matching"""
        condition = {"field": "cpu", "op": ">", "value": 80}
        payload = {"cpu": 75}
        matched, refs = _evaluate_single_condition(condition, payload)
        assert matched is False
        assert refs["condition_evaluated"] is True
        assert refs["actual"] == 75.0

    def test_single_condition_eq_match(self):
        """Test equality operator matching"""
        condition = {"field": "status", "op": "==", "value": "error"}
        payload = {"status": "error"}
        matched, refs = _evaluate_single_condition(condition, payload)
        assert matched is True
        assert refs["condition_evaluated"] is True

    def test_single_condition_missing_field(self):
        """Test condition with missing field"""
        condition = {"field": "nonexistent", "op": ">", "value": 80}
        payload = {"cpu": 85}
        matched, refs = _evaluate_single_condition(condition, payload)
        assert matched is False
        assert refs["condition_evaluated"] is False
        assert refs["reason"] == "field missing"

    def test_single_condition_metrics_block(self):
        """Test condition with metrics block"""
        condition = {"field": "memory", "op": ">", "value": 70}
        payload = {"metrics": {"memory": 75}}
        matched, refs = _evaluate_single_condition(condition, payload)
        assert matched is True
        assert refs["actual"] == 75.0


class TestCompositeConditions:
    """Test composite condition evaluation (AND/OR/NOT)"""

    def test_and_all_true(self):
        """Test AND logic when all conditions are true"""
        conditions = [
            {"field": "cpu", "op": ">", "value": 80},
            {"field": "memory", "op": ">", "value": 70},
        ]
        payload = {"cpu": 85, "memory": 75}
        matched, refs = _evaluate_composite_conditions(conditions, "AND", payload)
        assert matched is True
        assert refs["composite_logic"] == "AND"
        assert len(refs["conditions_evaluated"]) == 2
        assert refs["final_result"] is True

    def test_and_one_false(self):
        """Test AND logic when one condition is false"""
        conditions = [
            {"field": "cpu", "op": ">", "value": 80},
            {"field": "memory", "op": ">", "value": 70},
        ]
        payload = {"cpu": 75, "memory": 75}
        matched, refs = _evaluate_composite_conditions(conditions, "AND", payload)
        assert matched is False
        assert refs["final_result"] is False

    def test_or_one_true(self):
        """Test OR logic when one condition is true"""
        conditions = [
            {"field": "cpu", "op": ">", "value": 80},
            {"field": "memory", "op": ">", "value": 70},
        ]
        payload = {"cpu": 75, "memory": 75}
        matched, refs = _evaluate_composite_conditions(conditions, "OR", payload)
        assert matched is True
        assert refs["composite_logic"] == "OR"
        assert refs["final_result"] is True

    def test_or_all_false(self):
        """Test OR logic when all conditions are false"""
        conditions = [
            {"field": "cpu", "op": ">", "value": 80},
            {"field": "memory", "op": ">", "value": 70},
        ]
        payload = {"cpu": 75, "memory": 65}
        matched, refs = _evaluate_composite_conditions(conditions, "OR", payload)
        assert matched is False
        assert refs["final_result"] is False

    def test_not_all_false(self):
        """Test NOT logic when all conditions are false"""
        conditions = [
            {"field": "cpu", "op": ">", "value": 80},
            {"field": "memory", "op": ">", "value": 70},
        ]
        payload = {"cpu": 75, "memory": 65}
        matched, refs = _evaluate_composite_conditions(conditions, "NOT", payload)
        assert matched is True
        assert refs["composite_logic"] == "NOT"
        assert refs["final_result"] is True

    def test_not_one_true(self):
        """Test NOT logic when one condition is true"""
        conditions = [
            {"field": "cpu", "op": ">", "value": 80},
            {"field": "memory", "op": ">", "value": 70},
        ]
        payload = {"cpu": 85, "memory": 75}
        matched, refs = _evaluate_composite_conditions(conditions, "NOT", payload)
        assert matched is False
        assert refs["final_result"] is False

    def test_empty_conditions(self):
        """Test empty conditions list"""
        conditions = []
        payload = {"cpu": 85}
        matched, refs = _evaluate_composite_conditions(conditions, "AND", payload)
        assert matched is True  # Empty AND returns True
        assert refs["composite_logic"] == "AND"
        assert len(refs["conditions_evaluated"]) == 0

    def test_invalid_logic(self):
        """Test invalid logic operator"""
        conditions = [{"field": "cpu", "op": ">", "value": 80}]
        payload = {"cpu": 85}
        with pytest.raises(Exception) as excinfo:
            _evaluate_composite_conditions(conditions, "INVALID", payload)
        assert "Unsupported composite logic" in str(excinfo.value)


class TestEventTriggerBackwardCompatibility:
    """Test backward compatibility with existing single condition format"""

    def test_old_format_single_condition(self):
        """Test old single condition format still works"""
        trigger_spec = {"field": "cpu", "op": ">", "value": 80}
        payload = {"cpu": 85}
        matched, refs = _evaluate_event_trigger(trigger_spec, payload)
        assert matched is True
        assert refs["condition_evaluated"] is True

    def test_new_format_composite_conditions(self):
        """Test new composite condition format"""
        trigger_spec = {
            "conditions": [
                {"field": "cpu", "op": ">", "value": 80},
                {"field": "memory", "op": ">", "value": 70},
            ],
            "logic": "AND",
        }
        payload = {"cpu": 85, "memory": 75}
        matched, refs = _evaluate_event_trigger(trigger_spec, payload)
        assert matched is True
        assert "composite_logic" in refs
        assert refs["composite_logic"] == "AND"

    def test_complex_or_logic(self):
        """Test complex OR condition"""
        trigger_spec = {
            "conditions": [
                {"field": "cpu", "op": ">", "value": 80},
                {"field": "memory", "op": ">", "value": 70},
                {"field": "disk", "op": ">", "value": 90},
            ],
            "logic": "OR",
        }
        payload = {"cpu": 75, "memory": 75, "disk": 45}
        matched, refs = _evaluate_event_trigger(trigger_spec, payload)
        assert matched is True  # memory > 70 is true


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_numeric_string_comparison(self):
        """Test numeric string comparison"""
        condition = {"field": "count", "op": ">", "value": 5}
        payload = {"count": "10"}
        matched, refs = _evaluate_single_condition(condition, payload)
        assert matched is True  # "10" converts to 10.0

    def test_string_comparison(self):
        """Test string comparison"""
        condition = {"field": "status", "op": "!=", "value": "success"}
        payload = {"status": "error"}
        matched, refs = _evaluate_single_condition(condition, payload)
        assert matched is True

    def test_none_payload(self):
        """Test with None payload"""
        trigger_spec = {"field": "cpu", "op": ">", "value": 80}
        matched, refs = _evaluate_event_trigger(trigger_spec, None)
        assert matched is False
        assert refs["reason"] == "field missing"

    def test_metrics_block_access(self):
        """Test accessing field from metrics block"""
        trigger_spec = {
            "conditions": [{"field": "cpu", "op": ">", "value": 80}],
            "logic": "AND",
        }
        payload = {"metrics": {"cpu": 85}}
        matched, refs = _evaluate_event_trigger(trigger_spec, payload)
        assert matched is True
