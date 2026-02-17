from __future__ import annotations

from types import SimpleNamespace

from app.modules.asset_registry.crud import build_schema_catalog


def test_build_schema_catalog_normalizes_legacy_table_shape() -> None:
    asset = SimpleNamespace(
        asset_id="11111111-1111-4111-8111-111111111111",
        name="legacy_catalog",
        content={
            "source_ref": "default_postgres",
            "catalog": {
                "name": "legacy_catalog",
                "tables": [
                    {
                        "name": "tb_user",
                        "schema_name": "public",
                        "columns": [
                            {
                                "column_name": "id",
                                "data_type": "uuid",
                                "is_nullable": "NO",
                                "is_primary_key": True,
                            },
                            {
                                "column_name": "username",
                                "data_type": "varchar",
                                "is_nullable": "YES",
                            },
                        ],
                        "indexes": [
                            {"name": "tb_user_pkey", "definition": "PRIMARY KEY (id)"}
                        ],
                    }
                ],
            },
        },
    )

    catalog = build_schema_catalog(asset)  # type: ignore[arg-type]

    assert catalog.name == "legacy_catalog"
    assert catalog.source_ref == "default_postgres"
    assert len(catalog.tables) == 1
    assert catalog.tables[0].name == "tb_user"
    assert catalog.tables[0].columns[0].name == "id"
    assert catalog.tables[0].columns[0].is_nullable is False
    assert catalog.tables[0].columns[1].name == "username"
    assert catalog.tables[0].columns[1].is_nullable is True
    assert isinstance(catalog.tables[0].indexes, dict)
    assert "items" in (catalog.tables[0].indexes or {})

