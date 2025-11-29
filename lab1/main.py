"""
Разработать приложение, обеспечивающее получение следующей системной
информации:
• Имя компьютера, имя пользователя;
• Версия операционной системы;
• Системные метрики (не менее 3х);
• Функции для работы со временем (не менее 2х);
• Дополнительные API-функции: 4 функции по выбору.
"""

import platform
import os
import socket
import time
from pathlib import Path

import psutil


if __name__ == "__main__":
    print(f"Hostname: {socket.gethostname()}, Username: {os.getlogin()}")
    print("###")
    print(f"OS version: {platform.uname().version}")
    print("###")
    mem = psutil.virtual_memory()
    print(
        f"CPU usage: {psutil.cpu_percent(interval=1.0)},"
        f" CPU count: {psutil.cpu_count()},"
        f" VRAM: total={mem.total/(10**9)}Gb, available={mem.available/(10**9)}Gb"
    )
    print("###")
    print(f"Current timestamp: {time.time()}, Proc time: {time.process_time()}")
    print("###")
    print(f"Current working dir: {os.getcwd()}")
    print("Create a file file.txt in the current dir:")
    fpath = Path("file.txt")
    fpath.touch()
    print("Change the file's permissions to 644")
    fpath.chmod(0o644)
    print("Remove the file")
    fpath.unlink()
