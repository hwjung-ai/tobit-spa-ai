from unittest.mock import MagicMock

from app.modules.cep_builder import crud
from app.modules.cep_builder.schemas import CepRuleCreate


def test_create_rule_persists_tenant_id() -> None:
    session = MagicMock()
    captured: dict[str, object] = {}

    def _capture_add(obj: object) -> None:
        captured["rule"] = obj

    session.add.side_effect = _capture_add
    session.refresh.side_effect = lambda obj: None

    payload = CepRuleCreate(
        rule_name="Tenant Rule",
        trigger_type="metric",
        trigger_spec={"metric": "cpu_usage", "threshold": 80},
        action_spec={"action": "alert"},
        is_active=True,
        created_by="tester",
    )

    created = crud.create_rule(session, payload, tenant_id="default")

    assert created.tenant_id == "default"
    assert captured["rule"].tenant_id == "default"  # type: ignore[attr-defined]
    session.commit.assert_called_once()
