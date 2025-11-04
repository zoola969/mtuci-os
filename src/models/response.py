from datetime import datetime, UTC
from typing import Literal

from pydantic import Field

from models.base import MessageABC
from models.common import MonitorParams


class Response(MessageABC):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class ErrorResponse(Response):
    error: str
    success: Literal[False] = False


class SuccessResponse[T](Response):
    result: T
    success: Literal[True] = True


class GetMainMonitorPixelColorResponse(SuccessResponse[str]): ...


class GetMainMonitorParamsResponse(SuccessResponse[MonitorParams]): ...


class GetProcessIdResponse(SuccessResponse[int]): ...


class GetThreadCountResponse(SuccessResponse[int]): ...
