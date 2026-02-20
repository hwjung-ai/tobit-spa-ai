from app.modules.ops.services.orchestration.orchestrator.tool_orchestration import (
    DependencyAnalyzer,
)
from app.modules.ops.services.orchestration.planner.plan_schema import Intent, Plan


def test_dependency_analyzer_skips_default_primary_for_document_only_plan() -> None:
    plan = Plan(intent=Intent.DOCUMENT)
    plan.primary.keywords = []
    plan.secondary.keywords = []
    plan.aggregate.group_by = []
    plan.aggregate.metrics = []
    plan.aggregate.filters = []
    plan.history.enabled = False
    plan.metric = None
    plan.document = {
        "enabled": True,
        "query": "매뉴얼에서 ip 명령어 옵션 알려줘",
        "tool_type": "document_search",
    }

    analyzer = DependencyAnalyzer(question="매뉴얼에서 ip 명령어 옵션 알려줘")
    deps = analyzer.extract_dependencies(plan)
    tool_ids = [dep.tool_id for dep in deps]

    assert "document" in tool_ids
    assert "primary" not in tool_ids
    assert "aggregate" not in tool_ids

