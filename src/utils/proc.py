import os

import psutil


def get_process_id() -> int:
    return os.getpid()


def get_thread_count() -> int:
    pid = get_process_id()
    return psutil.Process(pid).num_threads()
