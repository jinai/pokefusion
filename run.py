import logging
import os.path
from logging.handlers import TimedRotatingFileHandler
from typing import Annotated

import discord
import typer
from discord import Intents

from pokefusion.bot import PokeFusion
from pokefusion.configmanager import ConfigManager
from pokefusion.environment import Environment
from pokefusion.models import models


def setup_logging(env: Environment):
    os.makedirs("logs", exist_ok=True)
    discord.utils.setup_logging()
    root = logging.getLogger()
    file_handler = TimedRotatingFileHandler(filename=os.path.join("logs", f"pokefusion.{env}.log"), when="midnight",
                                            encoding="utf-8")
    dt_fmt = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)


def main(env: Annotated[Environment, typer.Option()]) -> None:
    setup_logging(env)
    config = ConfigManager.get_bot_config(env)
    models.open_db(config.database)
    intents = Intents.default()
    intents.members = False
    intents.presences = False
    intents.message_content = True
    bot = PokeFusion(case_insensitive=True, intents=intents, config=config)
    bot.run(config.token, log_handler=None)


if __name__ == "__main__":
    typer.run(main)
