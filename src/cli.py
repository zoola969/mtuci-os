import json
import signal
import sys
import threading
from pathlib import Path
from types import FrameType
from typing import Any

import typer
from client import WhatType, build_request, connect as client_connect, resolve_sockets, send as client_send

app = typer.Typer(help="Client for monitoring/proc servers")
_shutdown_event = threading.Event()


def _setup_signal_handlers() -> None:
    def shutdown(signum: int, _frame: FrameType | None) -> None:
        print(f"Received shutdown signal {signum}, exiting...")
        _shutdown_event.set()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)


@app.callback()
def _main_callback() -> None:  # noqa: D401
    """CLI client for connecting to one or more servers and requesting data."""
    _setup_signal_handlers()


@app.command("connect")
def connect_cmd(
    servers: list[Path] | None = typer.Option(None, "--server", help="UNIX socket path; repeat to target multiple"),
) -> None:
    sockets = resolve_sockets(servers)

    # Connect to all specified servers concurrently
    from concurrent.futures import ThreadPoolExecutor

    def worker(sock_path: Path) -> None:
        try:
            with client_connect(sock_path):
                print(f"Connected to {sock_path.as_posix()}")
        except Exception as e:
            print(f"Failed to connect to {sock_path}: {e}")

    with ThreadPoolExecutor(max_workers=len(sockets) or None) as ex:
        for sock_path in sockets:
            ex.submit(worker, sock_path)


@app.command("disconnect")
def disconnect_cmd(
    servers: list[Path] | None = typer.Option(None, "--server", help="UNIX socket path; repeat to target multiple"),
) -> None:
    sockets = resolve_sockets(servers)
    for sock_path in sockets:
        print(f"Disconnected from {sock_path}")


@app.command("get")
def get_cmd(
    what: WhatType = typer.Option(..., "--what", help="What data to request"),
    x: int | None = typer.Option(None, "--x", help="X coordinate for pixel (required for 'pixel')"),
    y: int | None = typer.Option(None, "--y", help="Y coordinate for pixel (required for 'pixel')"),
    servers: list[Path] | None = typer.Option(None, "--server", help="UNIX socket path; repeat to target multiple"),
) -> None:
    request = build_request(what, x, y)
    sockets = resolve_sockets(servers)

    from concurrent.futures import ThreadPoolExecutor

    def worker(sock_path: Path) -> None:
        try:
            with client_connect(sock_path) as client:
                response: dict[str, Any] = client_send(client, request, _shutdown_event)
                print(f"[{sock_path}] -> {json.dumps(response, ensure_ascii=False)}")
        except Exception as e:
            print(f"[{sock_path}] -> error: {e}")

    with ThreadPoolExecutor(max_workers=len(sockets) or None) as ex:
        for sock_path in sockets:
            ex.submit(worker, sock_path)


if __name__ == "__main__":
    app()
