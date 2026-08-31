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
        logger.info("Syncing database with Discord guilds")

        current_discord_ids = tuple(guild.id for guild in self.bot.guilds)

        available_servers = [
            (guild.id, guild.name)
            for guild in self.bot.guilds
            if not guild.unavailable
        ]

        upserted, deactivated = Server.sync_all(
            available_servers,
            current_discord_ids,
            self.bot.default_prefix,
            self.bot.default_language
        )

        logger.info(
            f"Synced server records (upserted: {upserted}, deactivated: {deactivated})"
        )
        logger.info(f"Bot is ready, authenticated as {self.bot.user} (ID: {self.bot.user.id})")

    @commands.Cog.listener()
    async def on_guild_available(self, guild: Guild) -> None:
        if not self.bot.is_ready():
            return

        upserted = Server.upsert(guild.id, guild.name, self.bot.default_prefix, self.bot.default_language)

        if upserted:
            logger.info(f"Upserted available server {guild.name} (Guild ID: {guild.id})")

    @commands.Cog.listener()
    async def on_guild_join(self, guild: Guild) -> None:
        Server.upsert(guild.id, guild.name, self.bot.default_prefix, self.bot.default_language)
        logger.info(f"Joined '{guild.name}' (Guild ID: {guild.id})")

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: Guild) -> None:
        Server.deactivate(guild.id)
        logger.info(f"Left '{guild.name}' (Guild ID: {guild.id})")

    @commands.Cog.listener()
    async def on_command_error(self, ctx: Context, error: CommandError):
        log = f"{error.__class__.__name__}: {error} (message: {ctx.message.content})"

        if ctx.command is not None:
            log = f"[{ctx.canonical_command}] {log}"

        original = getattr(error, "original", error)
        logger.error(log, exc_info=original)

        if self.bot.config.environment is not Environment.PROD:
            formatted = "".join(traceback.format_exception(error)).rstrip()
            await ctx.safe_send(f"```py\n{formatted}\n```")


async def setup(bot: PokeFusion) -> None:
    await bot.add_cog(Events(bot))
