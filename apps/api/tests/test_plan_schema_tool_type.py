"""Unit tests for Plan schema with tool_type field."""


from app.modules.ops.services.ci.planner.plan_schema import (
    AggregateSpec,
    AutoSpec,
    CepSpec,
    GraphSpec,
    HistorySpec,
    Intent,
    MetricSpec,
    Plan,
    PlanMode,
    PrimarySpec,
    SecondarySpec,
)


class TestSpecToolType:
    """Test tool_type field in all Spec classes."""

    def test_primary_spec_has_tool_type_field(self):
        """PrimarySpec should have tool_type field with default."""
        spec = PrimarySpec(keywords=["test"])
        assert hasattr(spec, "tool_type")
        assert spec.tool_type == "ci_lookup"

    def test_primary_spec_tool_type_override(self):
        """PrimarySpec tool_type should be overridable."""
        spec = PrimarySpec(
            keywords=["test"],
            tool_type="custom_ci_lookup"
        )
        assert spec.tool_type == "custom_ci_lookup"

    def test_secondary_spec_has_tool_type_field(self):
        """SecondarySpec should have tool_type field with default."""
        spec = SecondarySpec(keywords=["test"])
        assert hasattr(spec, "tool_type")
        assert spec.tool_type == "ci_lookup"

    def test_secondary_spec_tool_type_override(self):
        """SecondarySpec tool_type should be overridable."""
        spec = SecondarySpec(
            keywords=["test"],
            tool_type="custom_ci_lookup"
        )
        assert spec.tool_type == "custom_ci_lookup"

    def test_metric_spec_has_tool_type_field(self):
        """MetricSpec should have tool_type field with default."""
        spec = MetricSpec(
            metric_name="cpu_usage",
            agg="avg",
            time_range="last_7d"
        )
        assert hasattr(spec, "tool_type")
        assert spec.tool_type == "metric"

    def test_metric_spec_tool_type_override(self):
        """MetricSpec tool_type should be overridable."""
        spec = MetricSpec(
            metric_name="cpu_usage",
            agg="avg",
            time_range="last_7d",
            tool_type="custom_metric_tool"
        )
        assert spec.tool_type == "custom_metric_tool"

    def test_aggregate_spec_has_tool_type_field(self):
        """AggregateSpec should have tool_type field with default."""
        spec = AggregateSpec(metrics=["cpu", "memory"])
        assert hasattr(spec, "tool_type")
        assert spec.tool_type == "ci_aggregate"

    def test_aggregate_spec_tool_type_override(self):
        """AggregateSpec tool_type should be overridable."""
        spec = AggregateSpec(
            metrics=["cpu"],
            tool_type="custom_agg_tool"
        )
        assert spec.tool_type == "custom_agg_tool"

    def test_history_spec_has_tool_type_field(self):
        """HistorySpec should have tool_type field with default."""
        spec = HistorySpec(enabled=True)
        assert hasattr(spec, "tool_type")
        assert spec.tool_type == "event_log"

    def test_history_spec_tool_type_override(self):
        """HistorySpec tool_type should be overridable."""
        spec = HistorySpec(
            enabled=True,
            tool_type="custom_history_tool"
        )
        assert spec.tool_type == "custom_history_tool"

    def test_graph_spec_has_tool_type_field(self):
        """GraphSpec should have tool_type field with default."""
        spec = GraphSpec(depth=3)
        assert hasattr(spec, "tool_type")
        assert spec.tool_type == "ci_graph"

    def test_graph_spec_tool_type_override(self):
        """GraphSpec tool_type should be overridable."""
        spec = GraphSpec(
            depth=2,
            tool_type="custom_graph_tool"
        )
        assert spec.tool_type == "custom_graph_tool"

    def test_cep_spec_has_tool_type_field(self):
        """CepSpec should have tool_type field with default."""
        spec = CepSpec()
        assert hasattr(spec, "tool_type")
        assert spec.tool_type == "cep_query"

    def test_cep_spec_tool_type_override(self):
        """CepSpec tool_type should be overridable."""
        spec = CepSpec(tool_type="custom_cep_tool")
        assert spec.tool_type == "custom_cep_tool"

    def test_auto_spec_has_tool_type_field(self):
        """AutoSpec should have tool_type field with default."""
        spec = AutoSpec()
        assert hasattr(spec, "tool_type")
        assert spec.tool_type == "auto_analyzer"

    def test_auto_spec_tool_type_override(self):
        """AutoSpec tool_type should be overridable."""
        spec = AutoSpec(tool_type="custom_auto_tool")
        assert spec.tool_type == "custom_auto_tool"


class TestPlanWithToolType:
    """Test Plan with tool_type in various specs."""

    def test_plan_with_primary_tool_type(self):
        """Plan should preserve primary spec tool_type."""
        plan = Plan(
            intent=Intent.LOOKUP,
            mode=PlanMode.CI,
            primary=PrimarySpec(keywords=["test"])
        )
        assert plan.primary.tool_type == "ci_lookup"

    def test_plan_with_custom_primary_tool_type(self):
        """Plan should preserve custom primary tool_type."""
        plan = Plan(
            intent=Intent.LOOKUP,
            primary=PrimarySpec(
                keywords=["test"],
                tool_type="custom_lookup"
            )
        )
        assert plan.primary.tool_type == "custom_lookup"

    def test_plan_with_metric_tool_type(self):
        """Plan should preserve metric spec tool_type."""
        plan = Plan(
            intent=Intent.AGGREGATE,
            metric=MetricSpec(
                metric_name="cpu",
                agg="avg",
                time_range="last_7d"
            )
        )
        assert plan.metric.tool_type == "metric"

    def test_plan_with_multiple_tool_types(self):
        """Plan with multiple specs should preserve all tool_types."""
        plan = Plan(
            intent=Intent.LOOKUP,
            primary=PrimarySpec(keywords=["server"]),
            metric=MetricSpec(
                metric_name="cpu_usage",
                agg="avg",
                time_range="last_7d"
            ),
            graph=GraphSpec(depth=2)
        )
        assert plan.primary.tool_type == "ci_lookup"
        assert plan.metric.tool_type == "metric"
        assert plan.graph.tool_type == "ci_graph"

    def test_plan_with_custom_multiple_tool_types(self):
        """Plan should allow custom tool_type for each spec."""
        plan = Plan(
            intent=Intent.LOOKUP,
            primary=PrimarySpec(
                keywords=["server"],
                tool_type="advanced_lookup"
            ),
            metric=MetricSpec(
                metric_name="cpu",
                agg="avg",
                time_range="last_7d",
                tool_type="advanced_metric"
            )
        )
        assert plan.primary.tool_type == "advanced_lookup"
        assert plan.metric.tool_type == "advanced_metric"


class TestPlanSerialization:
    """Test Plan JSON serialization with tool_type."""

    def test_plan_to_dict_includes_tool_type(self):
        """Plan.model_dump() should include tool_type."""
        plan = Plan(
            intent=Intent.LOOKUP,
            primary=PrimarySpec(keywords=["test"])
        )
        plan_dict = plan.model_dump()
        assert "tool_type" in plan_dict["primary"]
        assert plan_dict["primary"]["tool_type"] == "ci_lookup"

    def test_plan_to_json_includes_tool_type(self):
        """Plan.model_dump_json() should include tool_type."""
        plan = Plan(
            intent=Intent.LOOKUP,
            primary=PrimarySpec(keywords=["test"])
        )
        plan_json = plan.model_dump_json()
        assert '"tool_type"' in plan_json
        assert '"ci_lookup"' in plan_json

    def test_plan_from_dict_with_tool_type(self):
        """Plan should parse dict with tool_type."""
        plan_data = {
            "intent": "LOOKUP",
            "mode": "ci",
            "primary": {
                "keywords": ["test"],
                "tool_type": "custom_lookup"
            }
        }
        plan = Plan(**plan_data)
        assert plan.primary.tool_type == "custom_lookup"

    def test_plan_from_dict_without_tool_type(self):
        """Plan should use default tool_type if not in dict."""
        plan_data = {
            "intent": "LOOKUP",
            "mode": "ci",
            "primary": {
                "keywords": ["test"]
            }
        }
        plan = Plan(**plan_data)
        assert plan.primary.tool_type == "ci_lookup"

    def test_plan_json_parse_with_tool_type(self):
        """Plan should parse JSON string with tool_type."""
        plan_json = """{
            "intent": "LOOKUP",
            "mode": "ci",
            "primary": {
                "keywords": ["test"],
                "tool_type": "custom_lookup"
            }
        }"""
        plan = Plan.model_validate_json(plan_json)
        assert plan.primary.tool_type == "custom_lookup"

    def test_plan_json_parse_without_tool_type(self):
        """Plan should use default tool_type if not in JSON."""
        plan_json = """{
            "intent": "LOOKUP",
            "mode": "ci",
            "primary": {
                "keywords": ["test"]
            }
        }"""
        plan = Plan.model_validate_json(plan_json)
        assert plan.primary.tool_type == "ci_lookup"


class TestBackwardCompatibility:
    """Test backward compatibility with existing code."""

    def test_plan_created_without_tool_type_has_defaults(self):
        """Old code creating Plan without tool_type should work."""
        # This simulates existing code that doesn't know about tool_type
        plan = Plan(
            intent=Intent.LOOKUP,
            primary=PrimarySpec(keywords=["server"])
        )
        # Should have default tool_type
        assert plan.primary.tool_type == "ci_lookup"

    def test_plan_comparison_with_and_without_tool_type(self):
        """Plan should work with both old and new code."""
        # Old way (without tool_type)
        old_plan_data = {
            "intent": "LOOKUP",
            "primary": {"keywords": ["test"]}
        }

        # New way (with explicit tool_type)
        new_plan_data = {
            "intent": "LOOKUP",
            "primary": {"keywords": ["test"], "tool_type": "ci_lookup"}
        }

        old_plan = Plan(**old_plan_data)
        new_plan = Plan(**new_plan_data)

        # Both should have same tool_type
        assert old_plan.primary.tool_type == new_plan.primary.tool_type

    def test_all_spec_defaults_are_set(self):
        """All Spec classes should have tool_type defaults."""
        specs = [
            ("PrimarySpec", PrimarySpec(keywords=["test"]), "ci_lookup"),
            ("SecondarySpec", SecondarySpec(keywords=["test"]), "ci_lookup"),
            ("MetricSpec", MetricSpec(metric_name="cpu", agg="avg", time_range="7d"), "metric"),
            ("AggregateSpec", AggregateSpec(metrics=["cpu"]), "ci_aggregate"),
            ("GraphSpec", GraphSpec(depth=2), "ci_graph"),
            ("HistorySpec", HistorySpec(enabled=True), "event_log"),
            ("CepSpec", CepSpec(), "cep_query"),
            ("AutoSpec", AutoSpec(), "auto_analyzer"),
        ]

        for name, spec, expected_tool_type in specs:
            assert hasattr(spec, "tool_type"), f"{name} missing tool_type"
            assert spec.tool_type == expected_tool_type, \
                f"{name} tool_type mismatch: got {spec.tool_type}, expected {expected_tool_type}"
