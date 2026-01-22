from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar('T')

class ResponseEnvelope(BaseModel, Generic[T]):
    time: datetime
    code: int = 0
    message: str = "OK"
    data: dict[str, Any] | None = None

    @classmethod
    def success(
        cls,
        data: dict[str, Any] | None = None,
        *,
        message: str = "OK",
        code: int = 0,
    ) -> "ResponseEnvelope":
        return cls(time=datetime.now(timezone.utc), code=code, message=message, data=data)

    @classmethod
    def error(
        cls,
        message: str,
        *,
        code: int = 1,
        data: dict[str, Any] | None = None,
    ) -> "ResponseEnvelope":
        return cls(time=datetime.now(timezone.utc), code=code, message=message, data=data)
