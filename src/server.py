import fcntl
import json
import os
import signal
import socket
import sys
import threading
from collections.abc import Iterator
from concurrent.futures.thread import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from types import FrameType
from types_ import TLogger
from typing import Any, assert_never

from consts import (
    DEFAULT_LOG_PIPE,
    DEFAULT_SERVER_LOCK,
    DEFAULT_SERVER_SOCKET,
    LOG_PIPE_ENV_VAR,
    SERVER_LOCK_ENV_VAR,
    SERVER_SOCKER_ENV_VAR,
)
from models.request import (
    ECallType,
    GetMainMonitorPixelColor,
    GetProcessIdCall,
    GetThreadCountCall,
    GetMainMonitorParamsCall,
    GetMainMonitorPixelColorCall,
)
from utils.monitor import get_main_monitor_params, get_main_monitor_pixel_color
from utils.proc import get_process_id, get_thread_count
from models.response import (
    ErrorResponse,
    GetMainMonitorParamsResponse,
    GetMainMonitorPixelColorResponse,
    GetProcessIdResponse,
    GetThreadCountResponse,
    Response,
)
from utils.messagging import get_messages, send_message


def main(*, server_socket: Path, lock_file: Path, log_pipe_path: Path) -> None:
    shutdown_event = threading.Event()

    with (
        _open_log_pipe(log_pipe_path) as logger,
        _ensure_one_instance(lock_file, logger),
        _run_server(server_socket, logger) as server,
    ):

        def shutdown(signum: int, _frame: FrameType | None) -> None:
            logger(f"Received shutdown signal {signum}, exiting...")
            shutdown_event.set()

        signal.signal(signal.SIGINT, shutdown)
        signal.signal(signal.SIGTERM, shutdown)

        executor = ThreadPoolExecutor(max_workers=None)
        _handle_clients(server, logger, executor, shutdown_event)


@contextmanager
def _open_log_pipe(log_pipe_path: Path) -> Iterator[TLogger]:
    def log(msg: str) -> None:
        print(msg)
        log_pipe.write(f"timestamp='{datetime.now().isoformat()}' message='{msg}'\n")
        log_pipe.flush()

    with log_pipe_path.open("w") as log_pipe:
        yield log


@contextmanager
def _ensure_one_instance(lock_file_path: Path, logger: TLogger) -> Iterator[None]:
    lock_file_path.parent.mkdir(exist_ok=True, parents=True)
    with lock_file_path.open("w") as lock_file:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
        except BlockingIOError:
            logger("Cannot run server, another instance is already running")
            sys.exit(1)


@contextmanager
def _run_server(socket_path: Path, logger: TLogger) -> Iterator[socket.socket]:
    socket_path.parent.mkdir(exist_ok=True, parents=True)
    if socket_path.exists():
        socket_path.unlink()
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind(socket_path.as_posix())
        server.listen(5)
        logger(f"Starting listening on {socket_path.as_posix()}")
        yield server


def _handle_clients(
    server: socket.socket,
    logger: TLogger,
    executor: ThreadPoolExecutor,
    shutdown_event: threading.Event,
) -> None:
    server.settimeout(1.0)
    while not shutdown_event.is_set():
        try:
            client, _ = server.accept()
        except socket.timeout:
            logger("Server accept timed out, checking shutdown event...")
            continue
        logger("Client connected")
        executor.submit(_handle_client_messages, client, logger, shutdown_event)
    logger("Client handler has been shut down")
    executor.shutdown(wait=True)


def _handle_client_messages(conn: socket.socket, logger: TLogger, shutdown_event: threading.Event) -> None:
    with conn:
        for message in get_messages(conn, shutdown_event, logger):
            logger(f"Received message: {message}")
            response = _process_message(message)
            logger(f"Sending response: {response}")
            send_message(conn, response)
    logger("Client handler exited")


def _process_message(raw_message: bytes) -> Response:
    try:
        message = json.loads(raw_message)
        return _handle_message(message)
    except json.JSONDecodeError:
        return ErrorResponse(success=False, error="Invalid JSON")
    except Exception as e:
        return ErrorResponse(success=False, error=str(e))


def _handle_message(message: dict[str, Any]) -> Response:
    parsed_message = _parse_message(message)
    if isinstance(parsed_message, GetMainMonitorParamsCall):
        params = get_main_monitor_params()
        return GetMainMonitorParamsResponse(success=True, result=params)
    if isinstance(parsed_message, GetMainMonitorPixelColorCall):
        color = get_main_monitor_pixel_color(x=parsed_message.params.x, y=parsed_message.params.y)
        return GetMainMonitorPixelColorResponse(success=True, result=color)
    if isinstance(parsed_message, GetProcessIdCall):
        pid = get_process_id()
        return GetProcessIdResponse(success=True, result=pid)
    if isinstance(parsed_message, GetThreadCountCall):
        thread_count = get_thread_count()
        return GetThreadCountResponse(success=True, result=thread_count)
    assert_never(parsed_message)


def _parse_message(
    message: dict[str, Any],
) -> GetMainMonitorParamsCall | GetMainMonitorPixelColorCall | GetProcessIdCall | GetThreadCountCall:
    if message["type"] == ECallType.GET_MAIN_MONITOR_PARAMS:
        return GetMainMonitorParamsCall(type=ECallType.GET_MAIN_MONITOR_PARAMS, params=None)

    if message["type"] == ECallType.GET_MAIN_MONITOR_PIXEL_COLOR:
        return GetMainMonitorPixelColorCall(
            type=ECallType.GET_MAIN_MONITOR_PIXEL_COLOR,
            params=GetMainMonitorPixelColor(
                x=message["params"]["x"],
                y=message["params"]["y"],
            ),
        )
    if message["type"] == ECallType.GET_PROCESS_ID:
        return GetProcessIdCall(type=ECallType.GET_PROCESS_ID, params=None)
    if message["type"] == ECallType.GET_THREAD_COUNT:
        return GetThreadCountCall(type=ECallType.GET_THREAD_COUNT, params=None)
    raise NotImplementedError


if __name__ == "__main__":
    server_socket_path = Path(os.getenv(SERVER_SOCKER_ENV_VAR, DEFAULT_SERVER_SOCKET))
    lock_file_path = Path(os.getenv(SERVER_LOCK_ENV_VAR, DEFAULT_SERVER_LOCK))
    log_pipe_path = Path(os.getenv(LOG_PIPE_ENV_VAR, DEFAULT_LOG_PIPE))
    main(server_socket=server_socket_path, lock_file=lock_file_path, log_pipe_path=log_pipe_path)
