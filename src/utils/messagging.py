import threading
from socket import socket
from typing import Iterator

from consts import MESSAGE_DELIMITER
from utils.log import log
from models.base import MessageABC


def send_message(s: socket, message: MessageABC) -> None:
    msg = f"{message.model_dump_json()}{MESSAGE_DELIMITER}".encode()
    s.sendall(msg)


def get_messages(s: socket, shutdown_event: threading.Event, *, read_bytes: int = 1024) -> Iterator[bytes]:
    try:
        buffer = b""
        while not shutdown_event.is_set():
            data = s.recv(read_bytes)
            if not data:
                log("Client disconnected")
                return

            parts = data.split(MESSAGE_DELIMITER.encode())
            if len(parts) == 1:  # No newline, the message is incomplete
                buffer += data
                continue

            for part in parts[:-1]:
                buffer += part
                yield buffer
                buffer = b""
            buffer = parts[-1]
        log("Stopping message reception due to shutdown event")
    except Exception as e:
        log(f"Client error: {e}")


def get_one_message(s: socket, shutdown_event: threading.Event, *, read_bytes: int = 1024) -> bytes:
    return next(get_messages(s, shutdown_event, read_bytes=read_bytes))
