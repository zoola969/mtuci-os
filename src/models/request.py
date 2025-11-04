from enum import StrEnum

from pydantic import BaseModel

from models.base import MessageABC


class ECallType(StrEnum):
    GET_MAIN_MONITOR_PARAMS = "get_main_monitor_params"
    GET_MAIN_MONITOR_PIXEL_COLOR = "get_main_monitor_pixel_color"
    GET_PROCESS_ID = "get_process_id"
    GET_THREAD_COUNT = "get_thread_count"


class CallABC[T](MessageABC):
    type: ECallType
    params: T


class GetMainMonitorPixelColor(BaseModel):
    x: int
    y: int


class GetMainMonitorPixelColorCall(CallABC[GetMainMonitorPixelColor]): ...


class GetMainMonitorParamsCall(CallABC[None]): ...


class GetProcessIdCall(CallABC[None]): ...


class GetThreadCountCall(CallABC[None]): ...
