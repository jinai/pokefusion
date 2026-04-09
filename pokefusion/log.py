import logging
import os
import platform
import time
from logging.handlers import TimedRotatingFileHandler

from pokefusion.enums import Environment


class ColorFormatter(logging.Formatter):
    LEVEL_COLOURS = {
        logging.DEBUG: "\x1b[40;1m",
        logging.INFO: "\x1b[34;1m",
        logging.WARNING: "\x1b[33;1m",
        logging.ERROR: "\x1b[31m",
        logging.CRITICAL: "\x1b[41m",
    }
    RESET = "\x1b[0m"
    TIME_COLOR = "\x1b[30;1m"
    NAME_COLOR = "\x1b[35m"
    FMT = f"{TIME_COLOR}%(asctime)s.%(msecs)03d{RESET} %(levelname_color)s%(levelname)-8s{RESET} {NAME_COLOR}%(name)s{RESET} %(message)s"

    def __init__(self):
        super().__init__()
        self._formatter = logging.Formatter(fmt=self.FMT, datefmt="%Y-%m-%d %H:%M:%S")

    def format(self, record):
        record.levelname_color = self.LEVEL_COLOURS.get(record.levelno, self.RESET)
        return self._formatter.format(record)


def setup_logging(env: Environment):
    if platform.system() == "Linux":
        os.environ["TZ"] = "CET"
        time.tzset()

    os.makedirs("logs", exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    file_handler = TimedRotatingFileHandler(filename=os.path.join("logs", f"pokefusion.{env}.log"), when="midnight",
                                            encoding="utf-8")
    fmt = "[%(asctime)s.%(msecs)03d] [%(levelname)-8s] %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    formatter = ColorFormatter()
    stream_handler.setFormatter(formatter)

    root.addHandler(file_handler)
    root.addHandler(stream_handler)
