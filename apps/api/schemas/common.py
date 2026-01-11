from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ResponseEnvelope(BaseModel):
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
        return cls(time=datetime.utcnow(), code=code, message=message, data=data)

    @classmethod
    def error(
        cls,
        message: str,
        *,
        code: int = 1,
        data: dict[str, Any] | None = None,
    ) -> "ResponseEnvelope":
        return cls(time=datetime.utcnow(), code=code, message=message, data=data)
