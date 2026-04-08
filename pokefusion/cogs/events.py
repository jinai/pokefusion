import logging

from discord import Guild
from discord.ext import commands
from discord.ext.commands import CommandError

from pokefusion.bot import PokeFusion
from pokefusion.context import Context
from pokefusion.db.models import Server

logger = logging.getLogger(__name__)


class Events(commands.Cog):
    def __init__(self, bot: PokeFusion) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        logger.info(f"Bot is ready, authenticated as {self.bot.user} (ID: {self.bot.user.id})")

    @commands.Cog.listener()
    async def on_guild_join(self, guild: Guild) -> None:
        rowid = Server.add(guild.id, guild.name, self.bot.default_prefix)
        logger.info(f"Joined {guild.name} (Guild ID: {guild.id}, Row ID: {rowid})")

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: Guild) -> None:
        rowid = Server.remove(guild.id)
        logger.info(f"Left {guild.name} (Guild ID: {guild.id}, Row ID: {rowid})")

    @commands.Cog.listener()
    async def on_command_error(self, ctx: Context, error: CommandError):
        logger.error(f"{error.__class__.__name__} [{ctx.command.name}] {error}")
        logger.error(f"Message: {ctx.message.content}")


async def setup(bot: PokeFusion) -> None:
    await bot.add_cog(Events(bot))
