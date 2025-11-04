import os
import signal
import threading
import stat
from pathlib import Path
from time import sleep
from types import FrameType


def _ensure_fifo(path: Path) -> None:
    if path.exists():
        mode = os.stat(path).st_mode
        if not stat.S_ISFIFO(mode):
            path.unlink(missing_ok=True)
            os.mkfifo(path)
    else:
        os.mkfifo(path)


def main(*, pipe_path: Path, log_file_path: Path):
    shutdown_event = threading.Event()

    def shutdown(signum: int, _frame: FrameType | None) -> None:
        print(f"Received shutdown signal {signum}, exiting...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    pipe_path.touch(exist_ok=True)

    with log_file_path.open("a") as log:
        print("Starting log server.")
        # Continuously reopen the FIFO to keep waiting for new writers.
        with pipe_path.open("r") as pipe:
            while not shutdown_event.is_set():
                line = pipe.readline()
                if not line:
                    print("No data received, retrying in 100ms.")
                    sleep(0.1)
                    continue
                log.write(line)
                log.flush()
            print("Shutdown event set, exiting log server.")


if __name__ == "__main__":
    pipe_path = Path(os.getenv("PIPE_PATH", "/tmp/log_server_1.pipe"))
    log_file_path = Path(os.getenv("LOG_FILE_PATH", "/tmp/log_server_1.log"))
    main(pipe_path=pipe_path, log_file_path=log_file_path)
