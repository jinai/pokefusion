from discord import Intents

from pokefusion.bot import PokeFusion
from pokefusion.cli import env_option
from pokefusion.cli.context import Context
from pokefusion.environment import Environment


def run_bot(env: Environment = env_option) -> None:
    ctx = Context(env)
    intents = Intents.default()
    intents.members = False
    intents.presences = False
    intents.message_content = True
    bot = PokeFusion(case_insensitive=True, intents=intents, config=ctx.config)
    bot.run(ctx.config.token, log_handler=None)
