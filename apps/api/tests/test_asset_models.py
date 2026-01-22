"""
Tests for OPS Asset Models (Source, Schema, Resolver).

Tests the new asset types introduced in Phase 2:
- Source Asset (database connections)
- Schema Catalog Asset (table/column metadata)
- Resolver Config Asset (alias and transformation rules)
"""


from app.modules.asset_registry.resolver_models import (
    AliasMapping,
    PatternRule,
    ResolverAsset,
    ResolverConfig,
    ResolverRule,
    ResolverType,
    TransformationRule,
)
from app.modules.asset_registry.schema_models import (
    SchemaAsset,
    SchemaCatalog,
    SchemaColumn,
    SchemaTable,
)
from app.modules.asset_registry.source_models import (
    SourceAsset,
    SourceConnection,
    SourceType,
)


class TestSourceAsset:
    """Test suite for Source Asset models."""

    def test_source_type_enum(self):
        """Test SourceType enum values."""
        assert SourceType.POSTGRESQL == "postgresql"
        assert SourceType.MYSQL == "mysql"
        assert SourceType.REDIS == "redis"
        assert SourceType.MONGODB == "mongodb"

    def test_source_connection_creation(self):
        """Test creating a source connection."""
        conn = SourceConnection(
            host="localhost",
            port=5432,
            username="test_user",
            database="test_db",
            secret_key_ref="db_password_key",
            ssl_mode="require",
            connection_params={"application_name": "tobit-spa-ai"},
            test_query="SELECT 1",
        )

        assert conn.host == "localhost"
        assert conn.port == 5432
        assert conn.username == "test_user"
        assert conn.database == "test_db"
        # P0-9 compliance: should use secret_key_ref, not direct password
        assert conn.secret_key_ref == "db_password_key"

    def test_source_connection_defaults(self):
        """Test source connection default values."""
        conn = SourceConnection(
            host="localhost",
            username="test_user",
        )

        assert conn.port == 5432  # Default port
        assert conn.ssl_mode == "verify-full"  # Default SSL mode
        assert conn.connection_params == {}

    def test_source_asset_creation(self):
        """Test creating a source asset."""
        connection = SourceConnection(
            host="prod-db.example.com",
            port=5432,
            username="analytics",
            database="analytics_db",
            secret_key_ref="analytics_db_secret",
        )

        asset = SourceAsset(
            name="Production Analytics Database",
            description="Primary PostgreSQL database for analytics",
            version=1,
            status="published",
            source_type=SourceType.POSTGRESQL,
            connection=connection,
        )

        assert asset.source_type == SourceType.POSTGRESQL
        assert asset.asset_type == "source"
        assert "analytics" in asset.description

    def test_source_asset_spec_json_pattern(self):
        """Test source asset spec_json pattern (P0-7 compliance)."""
        connection = SourceConnection(
            host="redis.example.com",
            port=6379,
            username="redis_user",
        )

        asset = SourceAsset(
            name="Redis Cache",
            version=1,
            status="published",
            source_type=SourceType.REDIS,
            connection=connection,
        )

        # Should have spec property
        spec = asset.spec
        assert isinstance(spec, dict)
        assert "source_type" in spec or "host" in spec


class TestSchemaAsset:
    """Test suite for Schema Catalog Asset models."""

    def test_schema_column_creation(self):
        """Test creating a schema column."""
        column = SchemaColumn(
            name="user_id",
            data_type="INTEGER",
            is_nullable=False,
            is_primary_key=True,
            default_value=None,
            description="Unique user identifier",
        )

        assert column.name == "user_id"
        assert column.data_type == "INTEGER"
        assert column.is_nullable is False
        assert column.is_primary_key is True

    def test_schema_table_creation(self):
        """Test creating a schema table."""
        columns = [
            SchemaColumn(
                name="id",
                data_type="INTEGER",
                is_primary_key=True,
            ),
            SchemaColumn(
                name="email",
                data_type="VARCHAR",
                is_nullable=False,
            ),
            SchemaColumn(
                name="created_at",
                data_type="TIMESTAMP",
                is_nullable=False,
            ),
        ]

        table = SchemaTable(
            name="users",
            schema_name="public",
            columns=columns,
            indexes={"idx_users_email": {}},
            constraints={"users_email_unique": {}},
        )

        assert table.name == "users"
        assert len(table.columns) == 3
        assert "idx_users_email" in table.indexes

    def test_schema_catalog_creation(self):
        """Test creating a schema catalog."""
        tables = [
            SchemaTable(
                name="users",
                schema_name="public",
                columns=[
                    SchemaColumn(name="id", data_type="INTEGER"),
                ],
            ),
            SchemaTable(
                name="orders",
                schema_name="public",
                columns=[
                    SchemaColumn(name="order_id", data_type="INTEGER"),
                ],
            ),
        ]

        catalog = SchemaCatalog(
            name="prod-analytics-schema",
            source_ref="prod-analytics-db:1.0.0",
            tables=tables,
            scan_status="completed",
        )

        assert catalog.source_ref == "prod-analytics-db:1.0.0"
        assert len(catalog.tables) == 2
        assert catalog.scan_status == "completed"

    def test_schema_catalog_computed_properties(self):
        """Test schema catalog computed properties."""
        tables = [
            SchemaTable(
                name="table1",
                schema_name="public",
                columns=[
                    SchemaColumn(name="col1", data_type="INTEGER"),
                    SchemaColumn(name="col2", data_type="VARCHAR"),
                ],
            ),
            SchemaTable(
                name="table2",
                schema_name="public",
                columns=[
                    SchemaColumn(name="col3", data_type="INTEGER"),
                ],
            ),
        ]

        catalog = SchemaCatalog(
            name="test-schema",
            source_ref="test-db:1.0.0",
            tables=tables,
        )

        # Test computed properties
        assert catalog.table_count == 2
        assert catalog.column_count == 3

    def test_schema_catalog_get_table(self):
        """Test getting a table by name from catalog."""
        tables = [
            SchemaTable(
                name="users",
                schema_name="public",
                columns=[],
            ),
            SchemaTable(
                name="orders",
                schema_name="public",
                columns=[],
            ),
        ]

        catalog = SchemaCatalog(
            name="test-schema",
            source_ref="test-db:1.0.0",
            tables=tables,
        )

        users_table = catalog.get_table("users")
        assert users_table is not None
        assert users_table.name == "users"

        missing_table = catalog.get_table("nonexistent")
        assert missing_table is None

    def test_schema_asset_creation(self):
        """Test creating a schema asset."""
        catalog = SchemaCatalog(
            name="prod-schema",
            source_ref="prod-db:1.0.0",
            tables=[],
            scan_status="completed",
        )

        asset = SchemaAsset(
            name="Production Database Schema",
            version=1,
            status="published",
            catalog=catalog,
        )

        assert asset.catalog.source_ref == "prod-db:1.0.0"

    def test_schema_asset_spec_json_pattern(self):
        """Test schema asset spec_json pattern (P0-7 compliance)."""
        catalog = SchemaCatalog(
            name="test-schema",
            source_ref="test-db:1.0.0",
            tables=[],
        )

        asset = SchemaAsset(
            name="Test Schema",
            version=1,
            status="published",
            catalog=catalog,
        )

        # Should have spec property
        spec = asset.spec
        assert isinstance(spec, dict)


class TestResolverAsset:
    """Test suite for Resolver Config Asset models."""

    def test_resolver_type_enum(self):
        """Test ResolverType enum values."""
        assert ResolverType.ALIAS_MAPPING == "alias_mapping"
        assert ResolverType.PATTERN_RULE == "pattern_rule"
        assert ResolverType.TRANSFORMATION == "transformation"

    def test_alias_mapping_creation(self):
        """Test creating an alias mapping."""
        mapping = AliasMapping(
            source_entity="cpu_usage",
            target_entity="cpu_utilization_percent",
            namespace="metrics",
        )

        assert mapping.source_entity == "cpu_usage"
        assert mapping.target_entity == "cpu_utilization_percent"
        assert mapping.namespace == "metrics"

    def test_pattern_rule_creation(self):
        """Test creating a pattern rule."""
        rule = PatternRule(
            name="metric_to_monitoring",
            pattern="^metric_(.+)$",
            replacement="monitoring.\\1",
            description="Convert metric_ prefix to monitoring namespace",
        )

        assert rule.name == "metric_to_monitoring"
        assert rule.pattern == "^metric_(.+)$"
        assert rule.replacement == "monitoring.\\1"

    def test_transformation_rule_creation(self):
        """Test creating a transformation rule."""
        rule = TransformationRule(
            name="snake_to_camel",
            transformation_type="format",
            field_name="all_fields",
            description="Convert snake_case to camelCase",
            parameters={"input_format": "snake_case", "output_format": "camelCase"},
        )

        assert rule.name == "snake_to_camel"
        assert rule.transformation_type == "format"
        assert rule.field_name == "all_fields"

    def test_resolver_rule_with_alias(self):
        """Test resolver rule with alias mapping."""
        alias = AliasMapping(
            source_entity="old_entity",
            target_entity="new_entity",
        )

        rule = ResolverRule(
            name="rename_old_to_new",
            rule_type=ResolverType.ALIAS_MAPPING,
            rule_data=alias,
            is_active=True,
            priority=1,
        )

        assert rule.name == "rename_old_to_new"
        assert rule.rule_type == ResolverType.ALIAS_MAPPING
        assert rule.rule_data.source_entity == "old_entity"
        assert rule.is_active is True

    def test_resolver_config_creation(self):
        """Test creating a resolver config."""
        rules = [
            ResolverRule(
                name="rule1",
                rule_type=ResolverType.ALIAS_MAPPING,
                rule_data=AliasMapping(source_entity="a", target_entity="b"),
                priority=1,
            ),
            ResolverRule(
                name="rule2",
                rule_type=ResolverType.PATTERN_RULE,
                rule_data=PatternRule(name="pattern1", pattern=".*", replacement="prefix.*"),
                priority=2,
            ),
        ]

        config = ResolverConfig(
            name="test_config",
            rules=rules,
            version=1,
        )

        assert len(config.rules) == 2
        assert config.version == 1

    def test_resolver_config_get_rule_by_name(self):
        """Test getting a rule by name from config."""
        rules = [
            ResolverRule(
                name="test_rule",
                rule_type=ResolverType.ALIAS_MAPPING,
                rule_data=AliasMapping(source_entity="x", target_entity="y"),
                priority=1,
            ),
        ]

        config = ResolverConfig(name="test_config", rules=rules)

        found_rule = config.get_rule_by_name("test_rule")
        assert found_rule is not None
        assert found_rule.name == "test_rule"

        missing_rule = config.get_rule_by_name("nonexistent")
        assert missing_rule is None

    def test_resolver_config_get_rules_by_type(self):
        """Test getting rules by type from config."""
        rules = [
            ResolverRule(
                name="alias1",
                rule_type=ResolverType.ALIAS_MAPPING,
                rule_data=AliasMapping(source_entity="a", target_entity="b"),
                priority=1,
            ),
            ResolverRule(
                name="alias2",
                rule_type=ResolverType.ALIAS_MAPPING,
                rule_data=AliasMapping(source_entity="c", target_entity="d"),
                priority=2,
            ),
            ResolverRule(
                name="pattern1",
                rule_type=ResolverType.PATTERN_RULE,
                rule_data=PatternRule(name="pattern_data", pattern=".*", replacement=".*"),
                priority=3,
            ),
        ]

        config = ResolverConfig(name="type_test", rules=rules)

        alias_rules = config.get_rules_by_type(ResolverType.ALIAS_MAPPING)
        assert len(alias_rules) == 2

        pattern_rules = config.get_rules_by_type(ResolverType.PATTERN_RULE)
        assert len(pattern_rules) == 1

    def test_resolver_config_add_remove_rule(self):
        """Test adding and removing rules from config."""
        config = ResolverConfig(name="test_add_remove", rules=[])

        new_rule = ResolverRule(
            name="new_rule",
            rule_type=ResolverType.ALIAS_MAPPING,
            rule_data=AliasMapping(source_entity="old", target_entity="new"),
            priority=1,
        )

        # Add rule
        config.add_rule(new_rule)
        assert len(config.rules) == 1

        # Remove rule
        config.remove_rule("new_rule")
        assert len(config.rules) == 0

    def test_resolver_asset_creation(self):
        """Test creating a resolver asset."""
        config = ResolverConfig(name="prod-config", rules=[], version=1)

        asset = ResolverAsset(
            name="Production Resolver Config",
            version=1,
            status="published",
            config=config,
        )

        assert asset.name == "Production Resolver Config"
        assert asset.config.version == 1

    def test_rule_priority_ordering(self):
        """Test that rules can be ordered by priority."""
        rules = [
            ResolverRule(
                name="low",
                rule_type=ResolverType.ALIAS_MAPPING,
                rule_data=AliasMapping(source_entity="a", target_entity="b"),
                priority=10,
            ),
            ResolverRule(
                name="high",
                rule_type=ResolverType.ALIAS_MAPPING,
                rule_data=AliasMapping(source_entity="c", target_entity="d"),
                priority=1,
            ),
            ResolverRule(
                name="medium",
                rule_type=ResolverType.ALIAS_MAPPING,
                rule_data=AliasMapping(source_entity="e", target_entity="f"),
                priority=5,
            ),
        ]

        config = ResolverConfig(name="priority_test", rules=rules)

        sorted_rules = sorted(config.rules, key=lambda r: r.priority)

        assert sorted_rules[0].name == "high"
        assert sorted_rules[1].name == "medium"
        assert sorted_rules[2].name == "low"


class TestAssetIntegration:
    """Integration tests for assets working together."""

    def test_source_to_schema_reference(self):
        """Test referencing source from schema catalog."""
        source_asset_id = "prod-db:1.0.0"

        # Create source
        source_conn = SourceConnection(
            host="prod.example.com",
            username="prod_user",
        )
        source = SourceAsset(
            name="Production DB",
            version=1,
            status="published",
            source_type=SourceType.POSTGRESQL,
            connection=source_conn,
        )

        # Create schema referencing the source
        catalog = SchemaCatalog(
            name="prod_catalog",
            source_ref=source_asset_id,
            tables=[],
        )
        schema = SchemaAsset(
            name="Production Schema",
            version=1,
            status="published",
            catalog=catalog,
        )

        assert schema.catalog.source_ref == source_asset_id

    def test_resolver_with_multiple_rule_types(self):
        """Test resolver config with mixed rule types."""
        rules = [
            ResolverRule(
                name="alias_rule",
                rule_type=ResolverType.ALIAS_MAPPING,
                rule_data=AliasMapping(source_entity="old", target_entity="new"),
                priority=1,
            ),
            ResolverRule(
                name="pattern_rule",
                rule_type=ResolverType.PATTERN_RULE,
                rule_data=PatternRule(name="pattern_data", pattern="^test_", replacement="prod_"),
                priority=2,
            ),
            ResolverRule(
                name="transform_rule",
                rule_type=ResolverType.TRANSFORMATION,
                rule_data=TransformationRule(
                    name="transform_data",
                    transformation_type="format",
                    field_name="all_fields",
                ),
                priority=3,
            ),
        ]

        config = ResolverConfig(name="multi_type_config", rules=rules)

        assert len(config.rules) == 3
        assert len(config.get_rules_by_type(ResolverType.ALIAS_MAPPING)) == 1
        assert len(config.get_rules_by_type(ResolverType.PATTERN_RULE)) == 1
        assert len(config.get_rules_by_type(ResolverType.TRANSFORMATION)) == 1
