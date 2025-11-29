import os
from datetime import datetime
from threading import Thread, get_ident


def print_info() -> None:
    print(f"Thread id: {get_ident()}, Parent pid: {os.getppid()}, current time: {datetime.now().strftime("%H:%M:%S")}")


if __name__ == "__main__":
    pid1 = os.fork()
    parent = False
    first_child = False
    second_child = False
    if pid1 == 0:  # we are inside the first child
        first_child = True
    else:  # we are still in the parent
        pid2 = os.fork()
        if pid2 == 0:  # we are inside the second child
            second_child = True
        else:  # we are still in the parent
            parent = True
    print(f"Pid: {os.getpid()}, Parent pid: {os.getppid()}, current time: {datetime.now().strftime("%H:%M:%S")}")

    if parent:
        os.system("ps -x")
    if first_child:
        os.system("netstat -rn")
    if second_child:
        t1 = Thread(target=print_info)
        t2 = Thread(target=print_info)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

    exit()
