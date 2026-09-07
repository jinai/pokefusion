import logging

import discord
from discord import Intents

from pokefusion.bot.pokefusion import PokeFusion
from pokefusion.cli.context import Context
from pokefusion.db.database import connect_database, get_pending_migrations

logger = logging.getLogger(__name__)


def run_bot() -> None:
    ctx = Context()
    database = connect_database(ctx.config.database)

    try:
        pending = get_pending_migrations(database)

        if pending:
            logger.warning("Cannot start the bot because database migrations are pending:")

            for migration in pending:
                logger.warning(f"- [ ] {migration}")

            logger.warning(f"Run 'uv run pwmigrate up' first.")
            return

        intents = Intents.default()
        intents.members = False
        intents.presences = False
        intents.message_content = True

        # Voice support is not needed
        discord.VoiceClient.warn_nacl = False
        discord.VoiceClient.warn_dave = False

        logger.info(f"Starting bot (Environment: {ctx.config.environment.upper()})")

        bot = PokeFusion(config=ctx.config, intents=intents)
        bot.run(ctx.config.token, log_handler=None)
    finally:
        database.close()
