import logging
import traceback

from discord import Guild
from discord.ext import commands
from discord.ext.commands import CommandError

from pokefusion.bot.context import Context
from pokefusion.bot.pokefusion import PokeFusion
from pokefusion.db.models import Server
from pokefusion.enums import Environment

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
        log = f"{error.__class__.__name__}: {error} (message: {ctx.message.content})"

        if ctx.command is not None:
            log = f"[{ctx.prefix}{ctx.command.qualified_name}] {log}"

        original = getattr(error, "original", error)
        logger.error(log, exc_info=original)

        if self.bot.config.environment is not Environment.PROD:
            formatted = "".join(traceback.format_exception(error)).rstrip()
            await ctx.safe_send(f"```py\n{formatted}\n```")


async def setup(bot: PokeFusion) -> None:
    await bot.add_cog(Events(bot))
