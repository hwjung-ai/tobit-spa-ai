from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CIHit(BaseModel):
    ci_id: str
    ci_code: str
    ci_name: str
    ci_type: str
    ci_subtype: str
    ci_category: str | None
    score: float


class MetricHit(BaseModel):
    metric_id: str
    metric_name: str


class TimeRange(BaseModel):
    start: datetime
    end: datetime
    bucket: str
