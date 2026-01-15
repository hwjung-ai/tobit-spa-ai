import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.ops.services.ci.orchestrator.runner import _find_exact_candidate


def test_find_exact_candidate_matches_ci_name_case_insensitive() -> None:
    candidates = [
        {"ci_id": "1", "ci_code": "app-x-01", "ci_name": "Other"},
        {"ci_id": "2", "ci_code": "app-apm-scheduler-05-1", "ci_name": "APM_App_Scheduler_05-1"},
    ]
    selected = _find_exact_candidate(candidates, ["apm_app_scheduler_05-1"])
    assert selected is not None
    assert selected["ci_id"] == "2"


def test_find_exact_candidate_matches_ci_code() -> None:
    candidates = [
        {"ci_id": "2", "ci_code": "os-erp-02", "ci_name": "ERP_OS_02"},
        {"ci_id": "3", "ci_code": "os-erp-03", "ci_name": "ERP_OS_03"},
    ]
    selected = _find_exact_candidate(candidates, ["OS-ERP-02"])
    assert selected is not None
    assert selected["ci_id"] == "2"


def test_find_exact_candidate_returns_none_when_no_exact_match() -> None:
    candidates = [{"ci_id": "1", "ci_code": "app-x-01", "ci_name": "Other"}]
    assert _find_exact_candidate(candidates, ["x"]) is None
