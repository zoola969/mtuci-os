from mss import mss
from mss.base import MSSBase
from mss.models import Monitor

from models.common import MonitorParams


def get_main_monitor_params() -> MonitorParams:
    with mss() as sct:
        main_monitor = _get_main_monitor(sct)
        return MonitorParams(width=main_monitor["width"], height=main_monitor["height"])


def get_main_monitor_pixel_color(*, x: int, y: int) -> str:
    with mss() as sct:
        main_monitor = _get_main_monitor(sct)
        r, g, b = sct.grab(main_monitor).pixel(x, y)

    return _rgb2hex(r=r, g=g, b=b)


def _get_main_monitor(sct: MSSBase) -> Monitor:
    try:
        return sct.monitors[1]  # 0 stands for all monitors, 1 for the main monitor
    except IndexError:
        raise  # TODO: log error


def _rgb2hex(*, r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"
