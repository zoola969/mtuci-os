import os
import socket
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Literal

from pydantic import TypeAdapter

from consts import DEFAULT_SERVER_SOCKET
from models.request import (
    CallABC,
    ECallType,
    GetMainMonitorParamsCall,
    GetMainMonitorPixelColor,
    GetMainMonitorPixelColorCall,
    GetProcessIdCall,
    GetThreadCountCall,
)
from models.response import ErrorResponse, Response
from utils.messagging import get_one_message, send_message


def resolve_sockets(servers: list[Path] | None) -> list[Path]:
    # If no servers passed explicitly, check env for one or more sockets.
    if not servers:
        # New style: two explicit env vars
        env1 = os.getenv("SERVER_SOCKET_PATH_1")
        env2 = os.getenv("SERVER_SOCKET_PATH_2")
        paths: list[Path] = []
        for p in (env1, env2):
            if p and p.strip():
                paths.append(Path(p.strip()))
        if paths:
            return paths
        # Legacy plural env var allowing multiple sockets (comma/space separated)
        sockets_env = os.getenv("SERVER_SOCKET_PATHS")
        if sockets_env:
            raw_parts = [part.strip() for chunk in sockets_env.split(",") for part in chunk.split()]
            paths = [Path(p) for p in raw_parts if p]
            if paths:
                return paths
        # Fallback to single-socket env var or default
        path = Path(os.getenv("SERVER_SOCKET_PATH", DEFAULT_SERVER_SOCKET))
        return [path]
    return [Path(p) for p in servers]


@contextmanager
def connect(socket_path: Path) -> Iterator[socket.socket]:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.connect(socket_path.as_posix())
        yield client


WhatType = Literal["monitor_params", "pixel", "pid", "threads"]


def build_request(what: WhatType, x: int | None, y: int | None) -> CallABC[Any]:
    if what == "monitor_params":
        return GetMainMonitorParamsCall(type=ECallType.GET_MAIN_MONITOR_PARAMS, params=None)
    if what == "pixel":
        if x is None or y is None:
            raise ValueError("--x and --y are required for 'pixel' request")
        return GetMainMonitorPixelColorCall(
            type=ECallType.GET_MAIN_MONITOR_PIXEL_COLOR,
            params=GetMainMonitorPixelColor(x=x, y=y),
        )
    if what == "pid":
        return GetProcessIdCall(type=ECallType.GET_PROCESS_ID, params=None)
    if what == "threads":
        return GetThreadCountCall(type=ECallType.GET_THREAD_COUNT, params=None)
    raise NotImplementedError(what)


def send[T: Response](
    client: socket.socket, message: CallABC[Any], shutdown_event: threading.Event, expected_response: type[T]
) -> T | ErrorResponse:
    send_message(client, message)
    raw = get_one_message(client, shutdown_event)
    return TypeAdapter(expected_response | ErrorResponse).validate_json(raw)
