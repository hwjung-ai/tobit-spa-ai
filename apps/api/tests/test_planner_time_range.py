
from app.modules.ops.services.ci.planner.planner_llm import (
    _determine_history_spec,
    _determine_metric_spec,
    _normalize_time_range,
)


def test_normalize_time_range_all_time_korean():
    assert _normalize_time_range("전체기간") == "all_time"
    assert _normalize_time_range("전체 기간") == "all_time"


def test_determine_metric_spec_all_time_korean():
    spec = _determine_metric_spec("전체기간 cpu 사용률이 가장 높은 ci")
    assert spec is not None
    assert spec.time_range == "all_time"


def test_determine_history_spec_all_time_korean():
    spec = _determine_history_spec("전체기간 작업이력")
    assert spec is not None
    assert spec.time_range == "all_time"
