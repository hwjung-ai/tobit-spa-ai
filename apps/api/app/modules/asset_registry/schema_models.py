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


class SchemaTable(SQLModel):
    """Represents a database table"""

    name: str = Field(min_length=1)
    schema_name: str = Field(min_length=1, default="public")
    description: Optional[str] = None
    columns: List[SchemaColumn] = Field(default_factory=list)
    indexes: Dict[str, Any] | None = Field(default_factory=dict)
    constraints: Dict[str, Any] | None = Field(default_factory=dict)
    tags: Dict[str, Any] | None = Field(default_factory=dict)


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
