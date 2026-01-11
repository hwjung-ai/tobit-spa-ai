from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List


class Direction(Enum):
    OUT = "out"
    IN = "in"
    BOTH = "both"


@dataclass(frozen=True)
class ViewPolicy:
    name: str
    description: str
    default_depth: int
    max_depth: int
    direction_default: Direction
    output_defaults: List[str]
    notes: str | None = None
    max_hops: int | None = None


VIEW_REGISTRY: Dict[str, ViewPolicy] = {
    "SUMMARY": ViewPolicy(
        name="SUMMARY",
        description="Top-level overview of a CI with immediate key statistics.",
        default_depth=1,
        max_depth=1,
        direction_default=Direction.BOTH,
        output_defaults=["overviews", "counts"],
    ),
    "COMPOSITION": ViewPolicy(
        name="COMPOSITION",
        description="System/component composition that highlights parent/child links.",
        default_depth=2,
        max_depth=3,
        direction_default=Direction.OUT,
        output_defaults=["hierarchy", "children"],
    ),
    "DEPENDENCY": ViewPolicy(
        name="DEPENDENCY",
        description="Bidirectional dependency relationships for the selected CI.",
        default_depth=2,
        max_depth=3,
        direction_default=Direction.BOTH,
        output_defaults=["dependency_graph", "counts"],
    ),
    "IMPACT": ViewPolicy(
        name="IMPACT",
        description="Propagated impact along dependencies (assumption-based).",
        default_depth=2,
        max_depth=2,
        direction_default=Direction.OUT,
        output_defaults=["impact_summary"],
        notes="IMPACT는 의존 기반 영향(가정)으로 정의합니다.",
    ),
    "PATH": ViewPolicy(
        name="PATH",
        description="Path discovery capped by a maximum hop limit.",
        default_depth=3,
        max_depth=6,
        direction_default=Direction.BOTH,
        output_defaults=["path_segments"],
        max_hops=6,
    ),
    "NEIGHBORS": ViewPolicy(
        name="NEIGHBORS",
        description="Immediate neighbors for the selected CI.",
        default_depth=1,
        max_depth=2,
        direction_default=Direction.BOTH,
        output_defaults=["neighbors"],
    ),
}

VIEW_NAMES: List[str] = list(VIEW_REGISTRY.keys())
