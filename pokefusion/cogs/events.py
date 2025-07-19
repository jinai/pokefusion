import logging

from discord import Guild
from discord.ext import commands
from discord.ext.commands import CommandError

from pokefusion.bot import PokeFusion
from pokefusion.context import Context

logger = logging.getLogger(__name__)


class Events(commands.Cog):
    def __init__(self, bot: PokeFusion) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        logger.info(f"Authenticated as {self.bot.user} (ID: {self.bot.user.id})")

    @commands.Cog.listener()
    async def on_guild_join(self, guild: Guild) -> None:
        rowid = self.bot.db.add_server(guild, self.bot.default_prefix)
        logger.info(f"Joined {guild.name} (ID: {guild.id})")
        logger.debug(f"Joined Server with rowid={rowid}")

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: Guild) -> None:
        rowid = self.bot.db.remove_server(guild)
        logger.info(f"Left {guild.name} (ID: {guild.id})")
        logger.debug(f"Left Server with rowid={rowid}")

    @commands.Cog.listener()
    async def on_command_error(self, ctx: Context, error: CommandError):
        logger.error(f"{error.__class__.__name__} {error}")
        logger.error(f"Message: {ctx.message.content}")


async def setup(bot: PokeFusion) -> None:
    await bot.add_cog(Events(bot))
