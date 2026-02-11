"""Unit tests for Catalog Loading (Phase 3)."""

from datetime import datetime

from app.modules.asset_registry.schema_models import (
    SchemaCatalog,
    SchemaColumn,
    SchemaTable,
)


class TestSchemaColumnEnhancements:
    """Test enhanced SchemaColumn with size and statistics."""

    def test_schema_column_size_fields(self):
        """SchemaColumn should support size specifications."""
        col = SchemaColumn(
            name="username",
            data_type="VARCHAR",
            column_size=255
        )
        assert col.column_size == 255

    def test_schema_column_numeric_precision(self):
        """SchemaColumn should support numeric precision."""
        col = SchemaColumn(
            name="price",
            data_type="NUMERIC",
            numeric_precision=10,
            numeric_scale=2
        )
        assert col.numeric_precision == 10
        assert col.numeric_scale == 2

    def test_schema_column_data_samples(self):
        """SchemaColumn should store sample data."""
        samples = ["john@example.com", "jane@example.com", "bob@example.com"]
        col = SchemaColumn(
            name="email",
            data_type="VARCHAR",
            data_samples=samples
        )
        assert col.data_samples == samples

    def test_schema_column_statistics(self):
        """SchemaColumn should store statistics."""
        col = SchemaColumn(
            name="age",
            data_type="INTEGER",
            distinct_count=150,
            null_count=5,
            min_value="18",
            max_value="85",
            avg_value="42.5"
        )
        assert col.distinct_count == 150
        assert col.null_count == 5
        assert col.min_value == "18"
        assert col.max_value == "85"
        assert col.avg_value == "42.5"

    def test_schema_column_index_and_unique(self):
        """SchemaColumn should track index and unique constraints."""
        col = SchemaColumn(
            name="email",
            data_type="VARCHAR",
            is_indexed=True,
            is_unique=True
        )
        assert col.is_indexed is True
        assert col.is_unique is True

    def test_schema_column_ordinal_position(self):
        """SchemaColumn should store ordinal position."""
        col = SchemaColumn(
            name="id",
            data_type="INTEGER",
            ordinal_position=1
        )
        assert col.ordinal_position == 1


class TestSchemaTableEnhancements:
    """Test enhanced SchemaTable with statistics and samples."""

    def test_schema_table_row_count(self):
        """SchemaTable should store row count."""
        table = SchemaTable(
            name="users",
            row_count=10000
        )
        assert table.row_count == 10000

    def test_schema_table_size_bytes(self):
        """SchemaTable should store size in bytes."""
        table = SchemaTable(
            name="users",
            size_bytes=1024000  # 1MB
        )
        assert table.size_bytes == 1024000

    def test_schema_table_sample_rows(self):
        """SchemaTable should store sample rows."""
        samples = [
            {"id": 1, "name": "John", "age": 30},
            {"id": 2, "name": "Jane", "age": 25},
            {"id": 3, "name": "Bob", "age": 35},
        ]
        table = SchemaTable(
            name="users",
            sample_rows=samples
        )
        assert len(table.sample_rows) == 3
        assert table.sample_rows[0]["name"] == "John"

    def test_schema_table_last_modified(self):
        """SchemaTable should track last modification time."""
        now = datetime.now()
        table = SchemaTable(
            name="users",
            last_modified=now
        )
        assert table.last_modified == now

    def test_schema_table_complete_info(self):
        """SchemaTable with complete statistics."""
        col1 = SchemaColumn(
            name="id",
            data_type="INTEGER",
            is_primary_key=True,
            ordinal_position=1
        )
        col2 = SchemaColumn(
            name="email",
            data_type="VARCHAR",
            column_size=255,
            is_indexed=True,
            is_unique=True,
            distinct_count=5000,
            data_samples=["user1@example.com", "user2@example.com"]
        )

        table = SchemaTable(
            name="users",
            description="User accounts",
            columns=[col1, col2],
            row_count=5000,
            size_bytes=5120000,
            sample_rows=[
                {"id": 1, "email": "user1@example.com"},
                {"id": 2, "email": "user2@example.com"},
            ]
        )

        assert len(table.columns) == 2
        assert table.row_count == 5000
        assert len(table.sample_rows) == 2


class TestSchemaCatalogLLMFormat:
    """Test SchemaCatalog.to_llm_format() method."""

    def test_llm_format_basic_structure(self):
        """LLM format should have expected structure."""
        col = SchemaColumn(
            name="id",
            data_type="INTEGER",
            description="User ID"
        )
        table = SchemaTable(
            name="users",
            description="User data",
            columns=[col]
        )
        catalog = SchemaCatalog(
            name="test_catalog",
            source_ref="test_db",
            tables=[table]
        )

        llm_format = catalog.to_llm_format()

        assert "source_ref" in llm_format
        assert "tables" in llm_format
        assert llm_format["source_ref"] == "test_db"
        assert len(llm_format["tables"]) == 1

    def test_llm_format_table_structure(self):
        """LLM format tables should include essential info."""
        col = SchemaColumn(
            name="email",
            data_type="VARCHAR",
            column_size=255,
            description="User email"
        )
        table = SchemaTable(
            name="users",
            schema_name="public",
            description="User accounts",
            columns=[col],
            row_count=1000
        )
        catalog = SchemaCatalog(
            name="test",
            source_ref="test_db",
            tables=[table]
        )

        llm_format = catalog.to_llm_format()
        table_info = llm_format["tables"][0]

        assert table_info["name"] == "users"
        assert table_info["schema"] == "public"
        assert table_info["description"] == "User accounts"
        assert "columns" in table_info
        assert table_info["row_count"] == 1000

    def test_llm_format_column_structure(self):
        """LLM format columns should include type, size, and stats."""
        col = SchemaColumn(
            name="price",
            data_type="NUMERIC",
            description="Item price",
            numeric_precision=10,
            numeric_scale=2,
            min_value="0.01",
            max_value="9999.99",
            null_count=5,
            distinct_count=200,
            data_samples=[10.50, 25.99, 100.00]
        )
        table = SchemaTable(
            name="items",
            columns=[col]
        )
        catalog = SchemaCatalog(
            name="test",
            source_ref="test_db",
            tables=[table]
        )

        llm_format = catalog.to_llm_format()
        col_info = llm_format["tables"][0]["columns"][0]

        assert col_info["name"] == "price"
        assert col_info["type"] == "NUMERIC"
        assert col_info["description"] == "Item price"
        assert col_info["precision"] == 10
        assert col_info["scale"] == 2
        assert col_info["min"] == "0.01"
        assert col_info["max"] == "9999.99"
        assert col_info["null_count"] == 5
        assert col_info["distinct_count"] == 200
        assert col_info["samples"] == [10.50, 25.99, 100.00]

    def test_llm_format_column_with_size(self):
        """LLM format should include column size for VARCHAR."""
        col = SchemaColumn(
            name="name",
            data_type="VARCHAR",
            column_size=100
        )
        table = SchemaTable(
            name="users",
            columns=[col]
        )
        catalog = SchemaCatalog(
            name="test",
            source_ref="test_db",
            tables=[table]
        )

        llm_format = catalog.to_llm_format()
        col_info = llm_format["tables"][0]["columns"][0]

        assert col_info["size"] == 100

    def test_llm_format_foreign_key(self):
        """LLM format should include foreign key info."""
        col = SchemaColumn(
            name="user_id",
            data_type="INTEGER",
            is_foreign_key=True,
            foreign_key_table="users",
            foreign_key_column="id"
        )
        table = SchemaTable(
            name="orders",
            columns=[col]
        )
        catalog = SchemaCatalog(
            name="test",
            source_ref="test_db",
            tables=[table]
        )

        llm_format = catalog.to_llm_format()
        col_info = llm_format["tables"][0]["columns"][0]

        assert col_info["foreign_key"] == "users.id"

    def test_llm_format_max_tables_limit(self):
        """LLM format should respect max_tables limit."""
        tables = [
            SchemaTable(name=f"table_{i}")
            for i in range(20)
        ]
        catalog = SchemaCatalog(
            name="test",
            source_ref="test_db",
            tables=tables
        )

        llm_format = catalog.to_llm_format(max_tables=5)

        assert len(llm_format["tables"]) == 5

    def test_llm_format_max_columns_limit(self):
        """LLM format should respect max_columns_per_table limit."""
        cols = [
            SchemaColumn(name=f"col_{i}", data_type="VARCHAR")
            for i in range(20)
        ]
        table = SchemaTable(
            name="large_table",
            columns=cols
        )
        catalog = SchemaCatalog(
            name="test",
            source_ref="test_db",
            tables=[table]
        )

        llm_format = catalog.to_llm_format(max_columns_per_table=10)

        assert len(llm_format["tables"][0]["columns"]) == 10

    def test_llm_format_sample_rows(self):
        """LLM format should include sample rows."""
        samples = [
            {"id": 1, "name": "John"},
            {"id": 2, "name": "Jane"},
            {"id": 3, "name": "Bob"},
            {"id": 4, "name": "Alice"},
        ]
        table = SchemaTable(
            name="users",
            sample_rows=samples
        )
        catalog = SchemaCatalog(
            name="test",
            source_ref="test_db",
            tables=[table]
        )

        llm_format = catalog.to_llm_format(max_sample_rows=2)

        assert "sample_rows" in llm_format["tables"][0]
        assert len(llm_format["tables"][0]["sample_rows"]) == 2

    def test_llm_format_primary_key(self):
        """LLM format should mark primary keys."""
        col = SchemaColumn(
            name="id",
            data_type="INTEGER",
            is_primary_key=True
        )
        table = SchemaTable(
            name="users",
            columns=[col]
        )
        catalog = SchemaCatalog(
            name="test",
            source_ref="test_db",
            tables=[table]
        )

        llm_format = catalog.to_llm_format()
        col_info = llm_format["tables"][0]["columns"][0]

        assert col_info.get("primary_key") is True

    def test_llm_format_timestamp(self):
        """LLM format should include scan timestamp."""
        now = datetime.now()
        catalog = SchemaCatalog(
            name="test",
            source_ref="test_db",
            tables=[],
            last_scanned_at=now
        )

        llm_format = catalog.to_llm_format()

        assert llm_format["last_scanned"] is not None
        assert isinstance(llm_format["last_scanned"], str)

    def test_llm_format_complete_example(self):
        """LLM format with complete data should be suitable for LLM."""
        col1 = SchemaColumn(
            name="id",
            data_type="INTEGER",
            is_primary_key=True,
            description="Order ID"
        )
        col2 = SchemaColumn(
            name="customer_email",
            data_type="VARCHAR",
            column_size=255,
            is_indexed=True,
            description="Customer email",
            data_samples=["john@example.com", "jane@example.com"]
        )
        col3 = SchemaColumn(
            name="amount",
            data_type="NUMERIC",
            numeric_precision=12,
            numeric_scale=2,
            description="Order amount",
            min_value="0.01",
            max_value="99999.99"
        )

        table = SchemaTable(
            name="orders",
            description="Customer orders",
            columns=[col1, col2, col3],
            row_count=50000,
            size_bytes=10485760,
            sample_rows=[
                {"id": 1, "customer_email": "john@example.com", "amount": 150.00},
                {"id": 2, "customer_email": "jane@example.com", "amount": 250.50},
            ]
        )

        catalog = SchemaCatalog(
            name="ecommerce",
            source_ref="postgres_prod",
            description="E-commerce database",
            tables=[table],
            last_scanned_at=datetime.now()
        )

        llm_format = catalog.to_llm_format()

        # Verify structure is complete and suitable for LLM
        assert llm_format["source_ref"] == "postgres_prod"
        assert len(llm_format["tables"]) == 1
        assert len(llm_format["tables"][0]["columns"]) == 3

        # Verify useful information is present
        table_info = llm_format["tables"][0]
        assert table_info["row_count"] == 50000
        assert len(table_info["sample_rows"]) == 2

        email_col = next(c for c in table_info["columns"] if c["name"] == "customer_email")
        assert "samples" in email_col
        assert email_col["size"] == 255

        amount_col = next(c for c in table_info["columns"] if c["name"] == "amount")
        assert amount_col["precision"] == 12
        assert amount_col["scale"] == 2
        assert amount_col["min"] == "0.01"
