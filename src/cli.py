import argparse
import shlex
import signal
import sys
import threading
import socket
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import FrameType
import os

from client import (
    WhatType,
    build_request,
    resolve_sockets,
    send as client_send,
)
from models.response import (
    GetMainMonitorParamsResponse,
    GetMainMonitorPixelColorResponse,
    GetProcessIdResponse,
    GetThreadCountResponse,
    Response,
)

# Global shutdown flag and persistent connections registry
_shutdown_event = threading.Event()
_connections: dict[Path, socket.socket] = {}


def _setup_signal_handlers() -> None:
    def shutdown(signum: int, _frame: FrameType | None) -> None:
        print(f"Received shutdown signal {signum}, exiting...")
        _shutdown_event.set()
        # Close all persistent connections gracefully
        for p, s in list(_connections.items()):
            try:
                s.close()
            except Exception:
                pass
            finally:
                _connections.pop(p, None)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)


def _response_type_for(what: WhatType) -> type[Response]:
    if what == "monitor_params":
        return GetMainMonitorParamsResponse
    if what == "pixel":
        return GetMainMonitorPixelColorResponse
    if what == "pid":
        return GetProcessIdResponse
    if what == "threads":
        return GetThreadCountResponse
    raise NotImplementedError(what)


def _what_role(what: WhatType) -> str:
    return "monitor" if what in ("monitor_params", "pixel") else "proc"


def _infer_role_for_socket(sock_path: Path) -> str | None:
    s1 = os.getenv("SERVER_SOCKET_PATH_1")
    s2 = os.getenv("SERVER_SOCKET_PATH_2")
    sp = sock_path.as_posix()
    if s1 and sp == s1:
        return "monitor"
    if s2 and sp == s2:
        return "proc"
    name = sock_path.name.lower()
    if "server_1" in name:
        return "monitor"
    if "server_2" in name:
        return "proc"
    return None


def _resolve_known_servers() -> dict[str, Path]:
    mapping: dict[str, Path] = {}
    s1 = os.getenv("SERVER_SOCKET_PATH_1")
    s2 = os.getenv("SERVER_SOCKET_PATH_2")
    if s1:
        mapping["1"] = Path(s1)
    if s2:
        mapping["2"] = Path(s2)
    if mapping and len(mapping) == 2:
        return mapping
    for p in resolve_sockets(None):
        role = _infer_role_for_socket(p)
        if role == "monitor" and "1" not in mapping:
            mapping["1"] = p
        elif role == "proc" and "2" not in mapping:
            mapping["2"] = p
    return mapping


def cmd_servers(argv: list[str]) -> None:
    """Show known server socket paths resolved from environment or defaults."""
    mapping = _resolve_known_servers()
    if not mapping:
        print("No sockets resolved")
        return
    for sid in ("1", "2"):
        p = mapping.get(sid)
        if p:
            role = "monitor" if sid == "1" else "proc"
            print(f"server_{sid} [{role}] -> {p.as_posix()}")
        else:
            print(f"server_{sid} -> <unresolved>")


def cmd_connect(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="connect")
    parser.add_argument("target", nargs="?", choices=["1", "2", "both"], default="both")
    ns = parser.parse_args(argv)

    mapping = _resolve_known_servers()
    targets: list[Path] = []
    if ns.target == "1":
        p = mapping.get("1")
        if not p:
            print("server_1 socket path is not resolved")
            return
        targets = [p]
    elif ns.target == "2":
        p = mapping.get("2")
        if not p:
            print("server_2 socket path is not resolved")
            return
        targets = [p]
    else:  # both
        for sid in ("1", "2"):
            p = mapping.get(sid)
            if p:
                targets.append(p)
        if not targets:
            print("No sockets resolved")
            return

    def worker(sock_path: Path) -> None:
        try:
            if sock_path in _connections:
                print(f"Already connected: {sock_path.as_posix()}")
                return
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.connect(sock_path.as_posix())
            _connections[sock_path] = s
            print(f"Connected to {sock_path.as_posix()}")
        except Exception as e:
            try:
                s.close()  # type: ignore[name-defined]
            except Exception:
                pass
            print(f"Failed to connect to {sock_path}: {e}")

    with ThreadPoolExecutor(max_workers=len(targets) or None) as ex:
        for sock in targets:
            ex.submit(worker, sock)


def cmd_disconnect(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="disconnect")
    parser.add_argument("target", nargs="?", choices=["1", "2", "both", "all"], default="both")
    ns = parser.parse_args(argv)

    mapping = _resolve_known_servers()
    targets: list[Path] = []
    if ns.target in ("both", "all"):
        targets = list(_connections.keys())
    elif ns.target == "1":
        p = mapping.get("1")
        if p in _connections:
            targets = [p]
        else:
            targets = [p_ for p_ in _connections.keys() if _infer_role_for_socket(p_) == "monitor"]
    elif ns.target == "2":
        p = mapping.get("2")
        if p in _connections:
            targets = [p]
        else:
            # Fallback: any connected socket with proc role
            targets = [p_ for p_ in _connections.keys() if _infer_role_for_socket(p_) == "proc"]

    if not targets:
        print("No matching active connections to disconnect")
        return

    def worker(sock_path: Path) -> None:
        s = _connections.get(sock_path)
        if not s:
            print(f"Not connected: {sock_path}")
            return
        try:
            s.close()
        except Exception:
            pass
        finally:
            _connections.pop(sock_path, None)
        print(f"Disconnected from {sock_path}")

    with ThreadPoolExecutor(max_workers=len(targets) or None) as ex:
        for sock in targets:
            ex.submit(worker, sock)


def cmd_status(argv: list[str]) -> None:
    if not _connections:
        print("No active connections")
        return
    for p, s in _connections.items():
        role = _infer_role_for_socket(p) or "unknown"
        print(f"{p.as_posix()} [role={role}] fd={s.fileno()}")


def cmd_get(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="get")
    parser.add_argument("--what", required=True, choices=["monitor_params", "pixel", "pid", "threads"], type=str)
    parser.add_argument("--x", type=int)
    parser.add_argument("--y", type=int)
    ns = parser.parse_args(argv)

    what: WhatType = ns.what  # type: ignore[assignment]
    x: int | None = ns.x
    y: int | None = ns.y

    try:
        request = build_request(what, x, y)
    except Exception as e:
        print(f"build_request error: {e}")
        return

    resp_type = _response_type_for(what)
    required_role = _what_role(what)

    # Auto-select from connected sockets with matching role
    targets: list[Path] = []
    for p in _connections.keys():
        role = _infer_role_for_socket(p)
        if role == required_role:
            targets.append(p)
    if not targets:
        hint = "connect 1" if required_role == "monitor" else "connect 2"
        print(f"No connected {required_role} servers available. Use '{hint}' first.")
        return

    def worker(sock_path: Path) -> None:
        s = _connections.get(sock_path)
        if not s:
            print(f"[{sock_path}] -> error: not connected")
            return
        try:
            response = client_send(s, request, _shutdown_event, resp_type)
            print(f"[{sock_path}] -> {response.model_dump_json(by_alias=True, exclude_none=True)}")
        except Exception as e:
            print(f"[{sock_path}] -> error: {e}")

    with ThreadPoolExecutor(max_workers=len(targets) or None) as ex:
        for sock in targets:
            ex.submit(worker, sock)


def run_shell() -> None:
    """Interactive shell loop."""
    _setup_signal_handlers()
    print("Type 'servers', 'connect', 'disconnect', 'status', 'get', or 'exit'.")
    while not _shutdown_event.is_set():
        try:
            line = input("> ").strip()
        except EOFError:
            print()
            break
        if not line:
            continue
        if line in {"exit", "quit"}:
            break
        parts = shlex.split(line)
        cmd, *args = parts
        try:
            if cmd == "servers":
                cmd_servers(args)
            elif cmd == "connect":
                cmd_connect(args)
            elif cmd == "disconnect":
                cmd_disconnect(args)
            elif cmd == "status":
                cmd_status(args)
            elif cmd == "get":
                cmd_get(args)
            else:
                print(f"Unknown command: {cmd}")
        except SystemExit:
            # argparse can call sys.exit; convert to message in shell
            continue
        except Exception as e:
            print(f"Command error: {e}")
    # Cleanup on normal exit
    for p, s in list(_connections.items()):
        try:
            s.close()
        except Exception:
            pass
        finally:
            _connections.pop(p, None)


if __name__ == "__main__":
    run_shell()
