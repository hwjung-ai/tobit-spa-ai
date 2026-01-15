import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.ops.services.ci.planner import planner_llm
from app.modules.ops.services.ci.planner.plan_schema import Intent


def test_llm_list_payload_forces_list_intent(monkeypatch):
    monkeypatch.setattr(
        planner_llm,
        "_call_output_parser_llm",
        lambda _text: {
            "output_types": ["table"],
            "ci_identifiers": [],
            "metric": None,
            "ambiguity": False,
            "list": {"enabled": True, "limit": 10, "offset": 0},
        },
    )
    plan = planner_llm.create_plan("ci 이름좀 10개만 뽑아주라")
    assert plan.intent == Intent.LIST
    assert plan.list.enabled is True
    assert plan.list.limit == 10
    assert plan.primary.keywords == []
    assert plan.output.primary == "table"
    assert plan.output.blocks == ["table"]


def test_llm_list_default_limit_applies(monkeypatch):
    monkeypatch.setattr(
        planner_llm,
        "_call_output_parser_llm",
        lambda _text: {
            "output_types": ["table"],
            "ci_identifiers": [],
            "metric": None,
            "ambiguity": False,
            "list": {"enabled": True},
        },
    )
    plan = planner_llm.create_plan("ci 리스트")
    assert plan.intent == Intent.LIST
    assert plan.list.enabled is True
    assert plan.list.limit == 50
