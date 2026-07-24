from discord import Intents

from pokefusion.bot.pokefusion import PokeFusion
from pokefusion.cli.context import Context
from pokefusion.db.database import database, init_db


def run_bot() -> None:
    ctx = Context()
    init_db(ctx.config.dbconf)
    intents = Intents.default()
    intents.members = False
    intents.presences = False
    intents.message_content = True
    bot = PokeFusion(case_insensitive=True, intents=intents, config=ctx.config)

    try:
        bot.run(ctx.config.token, log_handler=None)
    finally:
        database.close()
