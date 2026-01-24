from __future__ import annotations

import enum
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from sqlmodel import Field, SQLModel


class ResolverType(str, enum.Enum):
    """Types of resolver configurations"""

    ALIAS_MAPPING = "alias_mapping"
    PATTERN_RULE = "pattern_rule"
    TRANSFORMATION = "transformation"


class AliasMapping(SQLModel):
    """Represents an alias mapping for entity resolution"""

    source_entity: str = Field(min_length=1)  # Source entity name
    target_entity: str = Field(min_length=1)  # Target entity name
    namespace: Optional[str] = None  # Optional namespace
    description: Optional[str] = None
    is_active: bool = Field(default=True)
    priority: int = Field(default=0)
    extra_metadata: Dict[str, Any] | None = Field(default_factory=dict)


class PatternRule(SQLModel):
    """Represents a pattern matching rule"""

    name: str = Field(min_length=1)
    pattern: str = Field(min_length=1)  # Regex pattern
    replacement: str = Field(min_length=1)  # Replacement pattern
    description: Optional[str] = None
    is_active: bool = Field(default=True)
    priority: int = Field(default=0)
    extra_metadata: Dict[str, Any] | None = Field(default_factory=dict)


class TransformationRule(SQLModel):
    """Represents a transformation rule"""

    name: str = Field(min_length=1)
    transformation_type: str = Field(
        min_length=1
    )  # e.g., "uppercase", "lowercase", "format"
    field_name: str = Field(min_length=1)
    description: Optional[str] = None
    is_active: bool = Field(default=True)
    priority: int = Field(default=0)
    parameters: Dict[str, Any] | None = Field(default_factory=dict)
    extra_metadata: Dict[str, Any] | None = Field(default_factory=dict)


class ResolverRule(SQLModel):
    """Base class for resolver rules"""

    rule_type: ResolverType
    name: str = Field(min_length=1)
    description: Optional[str] = None
    is_active: bool = Field(default=True)
    priority: int = Field(default=0)
    extra_metadata: Dict[str, Any] | None = Field(default_factory=dict)

    # Union of specific rule types
    rule_data: Union[AliasMapping, PatternRule, TransformationRule]


class ResolverConfig(SQLModel):
    """Configuration for entity resolution"""

    name: str = Field(min_length=1)
    description: Optional[str] = None
    rules: List[ResolverRule] = Field(default_factory=list)
    default_namespace: Optional[str] = None
    tags: Dict[str, Any] | None = Field(default_factory=dict)
    version: int = Field(default=1)

    def get_rule_by_name(self, name: str) -> Optional[ResolverRule]:
        """Get a rule by name"""
        return next((r for r in self.rules if r.name == name), None)

    def get_rules_by_type(self, rule_type: ResolverType) -> List[ResolverRule]:
        """Get rules by type"""
        return [r for r in self.rules if r.rule_type == rule_type]

    def add_rule(self, rule: ResolverRule) -> None:
        """Add a rule"""
        # Remove existing rule with same name
        self.rules = [r for r in self.rules if r.name != rule.name]
        self.rules.append(rule)
        self.version += 1

    def remove_rule(self, name: str) -> bool:
        """Remove a rule by name"""
        original_length = len(self.rules)
        self.rules = [r for r in self.rules if r.name != name]
        if len(self.rules) < original_length:
            self.version += 1
            return True
        return False


class ResolverAsset(SQLModel):
    """Asset for storing resolver configuration"""

    # Asset metadata
    asset_type: str = Field(default="resolver")
    name: str = Field(min_length=1)
    description: Optional[str] = None
    version: int = Field(default=1)
    status: str = Field(default="draft")

    # Resolver-specific fields
    config: ResolverConfig

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
        default=None, description="JSON spec for the resolver configuration"
    )

    @property
    def spec(self) -> Dict[str, Any]:
        """Get the spec for this resolver asset"""
        if self.spec_json:
            return self.spec_json

        # Build spec from config
        spec = {
            "name": self.name,
            "rule_count": len(self.config.rules),
            "default_namespace": self.config.default_namespace,
            "version": self.version,
        }

        # Add rule type counts
        rule_type_counts = {}
        for rule in self.config.rules:
            rule_type_counts[rule.rule_type.value] = (
                rule_type_counts.get(rule.rule_type.value, 0) + 1
            )
        if rule_type_counts:
            spec["rule_types"] = rule_type_counts

        return spec

    @spec.setter
    def spec(self, value: Dict[str, Any]) -> None:
        """Set the spec and update config"""
        self.spec_json = value


class ResolverAssetCreate(SQLModel):
    name: str = Field(min_length=1)
    description: Optional[str] = None
    config: ResolverConfig
    scope: Optional[str] = None
    tags: Dict[str, Any] | None = Field(default_factory=dict)


class ResolverAssetUpdate(SQLModel):
    name: Optional[str] = Field(min_length=1)
    description: Optional[str] = None
    config: Optional[ResolverConfig] = None
    scope: Optional[str] = None
    tags: Optional[Dict[str, Any]] = None


class ResolverAssetResponse(SQLModel):
    asset_id: str
    asset_type: str
    name: str
    description: Optional[str]
    version: int
    status: str
    config: ResolverConfig
    scope: Optional[str]
    tags: Dict[str, Any] | None
    created_by: Optional[str]
    published_by: Optional[str]
    published_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ResolverListResponse(SQLModel):
    assets: List[ResolverAssetResponse]
    total: int
    page: int
    page_size: int


class ResolverSimulationRequest(SQLModel):
    """Request to simulate resolver configuration"""

    config: ResolverConfig
    test_entities: List[str] = Field(default_factory=list)
    simulation_options: Dict[str, Any] | None = Field(default_factory=dict)


class ResolverSimulationResult(SQLModel):
    """Result of resolver simulation"""

    original_entity: str
    resolved_entity: str
    transformations_applied: List[str] = Field(default_factory=list)
    confidence_score: float = Field(default=0.0)
    matched_rules: List[str] = Field(default_factory=list)
    extra_metadata: Dict[str, Any] | None = Field(default_factory=dict)
