from app.modules.ops.services.orchestration.planner import planner_llm


def test_build_output_parser_messages_uses_catalog_tables_and_columns(monkeypatch):
    def fake_prompt_definition():
        return {
            "templates": {
                "system": "system-prompt",
                "user": "question={question}",
            },
            "source": "test",
            "name": "test_prompt",
            "version": 1,
        }

    monkeypatch.setattr(
        planner_llm,
        "_load_planner_prompt_definition",
        fake_prompt_definition,
    )

    schema_context = {
        "catalog": {
            "tables": [
                {
                    "name": "ci",
                    "columns": [
                        {"column_name": "ci_id", "data_type": "uuid"},
                        {"name": "ci_name", "data_type": "text"},
                    ],
                }
            ]
        }
    }
    source_context = {
        "source_type": "postgresql",
        "connection": {"host": "db.example.local"},
    }

    messages = planner_llm._build_output_parser_messages(
        "show ci",
        schema_context=schema_context,
        source_context=source_context,
    )

    assert messages is not None
    assert len(messages) == 2
    user_content = messages[1]["content"]
    assert "Available tables: ci(ci_id, ci_name)" in user_content
    assert "Data source type: postgresql (Host: db.example.local)" in user_content
