import logging
import os
import platform
import time
from logging.handlers import TimedRotatingFileHandler

import discord

from pokefusion.environment import Environment


def setup_logging(env: Environment):
    if platform.system() == "Linux":
        os.environ["TZ"] = "CET"
        time.tzset()

    os.makedirs("logs", exist_ok=True)
    discord.utils.setup_logging()
    root = logging.getLogger()
    file_handler = TimedRotatingFileHandler(filename=os.path.join("logs", f"pokefusion.{env}.log"), when="midnight",
                                            encoding="utf-8")
    dt_fmt = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)
