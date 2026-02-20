from app.modules.ops.services.orchestration.planner import planner_llm
from app.modules.ops.services.orchestration.planner.plan_schema import (
    Intent,
    Plan,
    PlanOutput,
    PlanOutputKind,
)


def test_create_plan_output_for_document_query_forces_document_only(
    monkeypatch,
) -> None:
    async def fake_plan_llm_query(query: str, source_ref=None) -> PlanOutput:
        plan = Plan(intent=Intent.AGGREGATE)
        plan.primary.tool_type = "database_query"
        plan.primary.keywords = ["cpu"]
        plan.document = None
        return PlanOutput(kind=PlanOutputKind.PLAN, plan=plan)

    monkeypatch.setattr(planner_llm, "_call_output_parser_llm", lambda *args, **kwargs: None)
    monkeypatch.setattr(planner_llm, "plan_llm_query", fake_plan_llm_query)

    result = planner_llm.create_plan_output("매뉴얼에서 ip 명령어 옵션 알려줘", mode="all")

    assert result.kind == PlanOutputKind.PLAN
    assert result.plan is not None
    assert result.plan.intent == Intent.DOCUMENT
    assert result.plan.document is not None
    assert result.plan.document.get("enabled") is True
    assert result.plan.document.get("tool_type") == "document_search"
    assert result.plan.document.get("query") == "매뉴얼에서 ip 명령어 옵션 알려줘"
    assert result.plan.primary.keywords == []

