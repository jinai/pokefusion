import logging

import discord
from discord import Intents

from pokefusion.bot.pokefusion import PokeFusion
from pokefusion.cli.context import Context
from pokefusion.db.database import connect_database, database

logger = logging.getLogger(__name__)


def run_bot() -> None:
    ctx = Context()
    connect_database(ctx.config.database)
    intents = Intents.default()
    intents.members = False
    intents.presences = False
    intents.message_content = True

    # Voice support is not needed
    discord.VoiceClient.warn_nacl = False
    discord.VoiceClient.warn_dave = False

    logger.info(f"Starting bot (Environment: {ctx.config.environment.upper()})")
    bot = PokeFusion(case_insensitive=True, intents=intents, config=ctx.config)

    try:
        bot.run(ctx.config.token, log_handler=None)
    finally:
        database.close()
