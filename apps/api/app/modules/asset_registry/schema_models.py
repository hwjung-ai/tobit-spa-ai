from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlmodel import Field, SQLModel


class SchemaColumn(SQLModel):
    """Represents a column in a database table"""

    name: str = Field(min_length=1)
    data_type: str = Field(min_length=1)
    is_nullable: bool = Field(default=True)
    is_primary_key: bool = Field(default=False)
    is_foreign_key: bool = Field(default=False)
    foreign_key_table: Optional[str] = None
    foreign_key_column: Optional[str] = None
    default_value: Optional[str] = None
    description: Optional[str] = None
    constraints: Dict[str, Any] | None = Field(default_factory=dict)
    # Column size/length information
    column_size: Optional[int] = None  # VARCHAR(255) -> 255
    numeric_precision: Optional[int] = None  # NUMERIC(10,2) -> 10
    numeric_scale: Optional[int] = None  # NUMERIC(10,2) -> 2
    # Column statistics and samples
    data_samples: List[Any] | None = Field(default=None, description="Sample values from the column")
    distinct_count: Optional[int] = None  # Number of distinct values
    null_count: Optional[int] = None  # Number of NULL values
    min_value: Optional[str] = None  # Min value (for numeric/date types)
    max_value: Optional[str] = None  # Max value (for numeric/date types)
    avg_value: Optional[str] = None  # Average value (for numeric types)
    # Additional column properties
    is_indexed: bool = Field(default=False)
    is_unique: bool = Field(default=False)
    character_maximum_length: Optional[int] = None  # Alternative length specification
    ordinal_position: Optional[int] = None  # Column position in table


class SchemaTable(SQLModel):
    """Represents a database table"""

    name: str = Field(min_length=1)
    schema_name: str = Field(min_length=1, default="public")
    description: Optional[str] = None
    columns: List[SchemaColumn] = Field(default_factory=list)
    indexes: Dict[str, Any] | None = Field(default_factory=dict)
    constraints: Dict[str, Any] | None = Field(default_factory=dict)
    tags: Dict[str, Any] | None = Field(default_factory=dict)
    # Table statistics
    row_count: Optional[int] = None  # Number of rows in table
    size_bytes: Optional[int] = None  # Table size in bytes
    last_modified: Optional[datetime] = None  # When table was last modified
    # Sample data from table
    sample_rows: List[Dict[str, Any]] | None = Field(
        default=None,
        description="Sample rows from the table for LLM context"
    )


class SchemaCatalog(SQLModel):
    """Represents a schema catalog for a database source"""

    name: str = Field(min_length=1)
    description: Optional[str] = None
    source_ref: str = Field(min_length=1)  # Reference to the source asset ID
    tables: List[SchemaTable] = Field(default_factory=list)
    last_scanned_at: Optional[datetime] = None
    scan_status: str = Field(
        default="pending"
    )  # "pending", "scanning", "completed", "failed"
    scan_metadata: Dict[str, Any] | None = Field(default_factory=dict)

    @property
    def table_count(self) -> int:
        return len(self.tables)

    @property
    def column_count(self) -> int:
        return sum(len(table.columns) for table in self.tables)

    def get_table(self, table_name: str) -> Optional[SchemaTable]:
        """Get a table by name"""
        return next((t for t in self.tables if t.name == table_name), None)

    def get_column(self, table_name: str, column_name: str) -> Optional[SchemaColumn]:
        """Get a column by table and column name"""
        table = self.get_table(table_name)
        if table:
            return next((c for c in table.columns if c.name == column_name), None)
        return None

    def to_llm_format(self, max_tables: int = 10, max_columns_per_table: int = 15, max_sample_rows: int = 3) -> Dict[str, Any]:
        """
        Convert catalog to simplified format suitable for LLM prompts.

        Includes:
        - Table names and descriptions
        - Column names, types, sizes, and descriptions
        - Sample data from tables
        - Column statistics (distinct count, null count, min/max values)

        Args:
            max_tables: Maximum number of tables to include
            max_columns_per_table: Maximum columns per table
            max_sample_rows: Maximum sample rows per table

        Returns:
            Simplified catalog dictionary for LLM
        """
        simplified_tables = []

        for table in self.tables[:max_tables]:
            simplified_columns = []

            for col in table.columns[:max_columns_per_table]:
                col_info = {
                    "name": col.name,
                    "type": col.data_type,
                    "nullable": col.is_nullable,
                    "description": col.description or "",
                }

                # Add size information
                if col.column_size:
                    col_info["size"] = col.column_size
                elif col.character_maximum_length:
                    col_info["size"] = col.character_maximum_length
                elif col.numeric_precision:
                    col_info["precision"] = col.numeric_precision
                    if col.numeric_scale:
                        col_info["scale"] = col.numeric_scale

                # Add key constraints
                if col.is_primary_key:
                    col_info["primary_key"] = True
                if col.is_foreign_key:
                    col_info["foreign_key"] = f"{col.foreign_key_table}.{col.foreign_key_column}"
                if col.is_indexed:
                    col_info["indexed"] = True
                if col.is_unique:
                    col_info["unique"] = True

                # Add statistics if available
                if col.distinct_count is not None:
                    col_info["distinct_count"] = col.distinct_count
                if col.null_count is not None:
                    col_info["null_count"] = col.null_count
                if col.min_value is not None:
                    col_info["min"] = col.min_value
                if col.max_value is not None:
                    col_info["max"] = col.max_value
                if col.avg_value is not None:
                    col_info["avg"] = col.avg_value

                # Add sample values
                if col.data_samples and len(col.data_samples) > 0:
                    col_info["samples"] = col.data_samples[:3]  # Limit to 3 samples

                simplified_columns.append(col_info)

            table_info = {
                "name": table.name,
                "schema": table.schema_name,
                "description": table.description or "",
                "columns": simplified_columns,
            }

            # Add table statistics
            if table.row_count is not None:
                table_info["row_count"] = table.row_count
            if table.size_bytes is not None:
                table_info["size_bytes"] = table.size_bytes

            # Add sample rows
            if table.sample_rows and len(table.sample_rows) > 0:
                table_info["sample_rows"] = table.sample_rows[:max_sample_rows]

            simplified_tables.append(table_info)

        return {
            "source_ref": self.source_ref,
            "name": self.name,
            "description": self.description or "",
            "tables": simplified_tables,
            "last_scanned": self.last_scanned_at.isoformat() if self.last_scanned_at else None,
        }


class SchemaAsset(SQLModel):
    """Asset for storing schema information"""

    # Asset metadata
    asset_type: str = Field(default="catalog")
    name: str = Field(min_length=1)
    description: Optional[str] = None
    version: int = Field(default=1)
    status: str = Field(default="draft")

    # Schema-specific fields
    catalog: SchemaCatalog

    # Asset management
    scope: Optional[str] = None
    tags: Dict[str, Any] | None = Field(default_factory=dict)

    # Metadata
    created_by: Optional[str] = None
    published_by: Optional[str] = None
    published_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # For spec_json pattern consistency (P0-7)
    spec_json: Dict[str, Any] | None = Field(
        default=None, description="JSON spec for the schema catalog"
    )

    @property
    def spec(self) -> Dict[str, Any]:
        """Get the spec for this schema asset"""
        if self.spec_json:
            return self.spec_json

        # Build spec from catalog
        spec = {
            "name": self.name,
            "source_ref": self.catalog.source_ref,
            "table_count": self.catalog.table_count,
            "column_count": self.catalog.column_count,
            "last_scanned_at": self.catalog.last_scanned_at,
            "scan_status": self.catalog.scan_status,
        }

        if self.catalog.scan_metadata:
            spec["scan_metadata"] = self.catalog.scan_metadata

        return spec

    @spec.setter
    def spec(self, value: Dict[str, Any]) -> None:
        """Set the spec and update catalog"""
        self.spec_json = value


class SchemaAssetCreate(SQLModel):
    name: str = Field(min_length=1)
    description: Optional[str] = None
    source_ref: str = Field(min_length=1)
    scope: Optional[str] = None
    tags: Dict[str, Any] | None = Field(default_factory=dict)


class SchemaAssetUpdate(SQLModel):
    name: Optional[str] = Field(min_length=1)
    description: Optional[str] = None
    catalog: Optional[SchemaCatalog] = None
    scope: Optional[str] = None
    tags: Optional[Dict[str, Any]] = None


class SchemaAssetResponse(SQLModel):
    asset_id: str
    asset_type: str
    name: str
    description: Optional[str]
    version: int
    status: str
    catalog: SchemaCatalog
    scope: Optional[str]
    tags: Dict[str, Any] | None
    created_by: Optional[str]
    published_by: Optional[str]
    published_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScanRequest(SQLModel):
    """Request to scan a schema"""

    source_ref: str
    include_tables: Optional[List[str]] = None
    exclude_tables: Optional[List[str]] = None
    scan_options: Dict[str, Any] | None = Field(default_factory=dict)


class CatalogScanRequest(SQLModel):
    """Request payload for catalog schema discovery scan."""

    schema_names: List[str] | None = Field(
        default=None,
        description="Schema names to scan. Null means source-specific default schema.",
    )
    include_row_counts: bool = Field(
        default=False,
        description="Whether to include per-table row counts during scanning.",
    )


class ScanResult(SQLModel):
    """Result of a schema scan"""

    scan_id: str
    source_ref: str
    status: str
    tables_scanned: int
    columns_discovered: int
    error_message: Optional[str] = None
    scan_metadata: Dict[str, Any] | None = Field(default_factory=dict)
    execution_time_ms: Optional[int] = None


class SchemaListResponse(SQLModel):
    assets: List[SchemaAssetResponse]
    total: int
    page: int
    page_size: int
