import socket
import threading
from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path
from typing import Annotated, Any, AsyncIterator, Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from pydantic import BaseModel
from pydantic.v1 import BaseSettings
from starlette.responses import RedirectResponse

from client import send
from models.request import (
    CallABC,
    ECallType,
    GetProcessIdCall,
    GetThreadCountCall,
    GetMainMonitorParamsCall,
    GetMainMonitorPixelColorCall,
    GetMainMonitorPixelColor,
)
from models.response import (
    GetMainMonitorParamsResponse,
    Response,
    GetMainMonitorPixelColorResponse,
    GetProcessIdResponse,
    GetThreadCountResponse,
)


class Server:
    def __init__(self, name: str, socket_path: Path):
        self.name = name
        self._socket_path = socket_path
        self._sock: Optional[socket.socket] = None
        self._shutdown_event = threading.Event()

    @property
    def connected(self) -> bool:
        return self._sock is not None

    @property
    def socket_path(self) -> Path:
        return self._socket_path

    def request[T: Response](self, message: CallABC[Any], expected_response: type[T]) -> T:
        if self._sock is None:
            raise RuntimeError(f"{self.name} is not connected")
        return send(self._sock, message, self._shutdown_event, expected_response)

    def connect(self) -> None:
        if self._sock is not None:
            return
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(self._socket_path.as_posix())
        self._sock = s

    def disconnect(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None


@asynccontextmanager
async def lifespan(app_: FastAPI) -> AsyncIterator[None]:
    print("Starting up Client...")
    app_.state.server1 = Server("Server 1", client_settings.server_socket_path_1)
    app_.state.server2 = Server("Server 2", client_settings.server_socket_path_2)
    yield
    print("Shutting down Client...")


class ClientSettings(BaseSettings):
    server_socket_path_1: Path
    server_socket_path_2: Path


client_settings = ClientSettings()


app = FastAPI(title="OS Course Client API", lifespan=lifespan, version="1.0.0")


def get_server_1(request: Request) -> Server:
    return request.app.state.server1


def get_server_2(request: Request) -> Server:
    return request.app.state.server2


def get_connected_server(
    server_1: Annotated[Server, Depends(get_server_1)],
    server_2: Annotated[Server, Depends(get_server_2)],
    *,
    server_id: Annotated[Literal[1, 2], Path(description="1 or 2")],
) -> Server:
    server = server_1 if server_id == 1 else server_2
    if not server.connected:
        raise HTTPException(status_code=409, detail=f"Server {server_id} is not connected")
    return server


class Status(BaseModel):
    name: str
    socket_path: str
    connected: bool


@app.get("/servers", response_model=list[Status])
def servers_status(
    server_1: Annotated[Server, Depends(get_server_1)],
    server_2: Annotated[Server, Depends(get_server_2)],
) -> list[Status]:
    return [
        Status(name=server_1.name, socket_path=server_1.socket_path.as_posix(), connected=server_1.connected),
        Status(name=server_1.name, socket_path=server_2.socket_path.as_posix(), connected=server_2.connected),
    ]


@app.post("/connect/{server_id}")
def connect_server(
    server: Annotated[Server, Depends(get_connected_server)],
) -> Status:
    server.connect()
    return Status(name=server.name, socket_path=server.socket_path.as_posix(), connected=True)


@app.post("/disconnect/{server_id}")
def disconnect_server(
    server: Annotated[Server, Depends(get_connected_server)],
) -> Status:
    server.disconnect()
    return Status(name=server.name, socket_path=server.socket_path.as_posix(), connected=False)


# Server 1 monitor endpoints
@app.get("/server_1/monitor/params")
def server1_monitor_params(
    server: Annotated[Server, Depends(partial(get_connected_server, server_id=1))],
) -> GetMainMonitorParamsResponse:
    return server.request(
        GetMainMonitorParamsCall(type=ECallType.GET_MAIN_MONITOR_PARAMS, params=None),
        GetMainMonitorParamsResponse,
    )


@app.get("/server_1/monitor/pixel")
def server1_monitor_pixel(
    x: Annotated[int, Query(..., description="X for pixel")],
    y: Annotated[int, Query(..., description="Y for pixel")],
    server: Annotated[Server, Depends(partial(get_connected_server, server_id=1))],
) -> GetMainMonitorPixelColorResponse:
    return server.request(
        GetMainMonitorPixelColorCall(
            type=ECallType.GET_MAIN_MONITOR_PIXEL_COLOR,
            params=GetMainMonitorPixelColor(x=x, y=y),
        ),
        GetMainMonitorPixelColorResponse,
    )


# Server 2 pid/proc endpoints
@app.get("/server_2/pid")
def server2_pid(
    server: Annotated[Server, Depends(partial(get_connected_server, server_id=2))],
) -> GetProcessIdResponse:
    return server.request(
        GetProcessIdCall(type=ECallType.GET_PROCESS_ID, params=None),
        GetProcessIdResponse,
    )


@app.get("/server_2/threads")
def server2_threads(
    server: Annotated[Server, Depends(partial(get_connected_server, server_id=2))],
) -> GetThreadCountResponse:
    return server.request(
        GetThreadCountCall(type=ECallType.GET_THREAD_COUNT, params=None),
        GetThreadCountResponse,
    )


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse("/docs")
