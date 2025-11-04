from models.base import MessageABC


class MonitorParams(MessageABC):
    width: int
    height: int
