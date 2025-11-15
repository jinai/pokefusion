from __future__ import annotations

import logging
import traceback
from collections.abc import Awaitable, Callable, Sequence
from datetime import datetime
from typing import Any

import discord
from discord import Interaction, Message, User
from discord.ext import commands
from discord.ext.commands import CommandError

from . import cogs
from .assetmanager import AssetManager
from .cogs.database import Database
from .configmanager import BotConfig
from .context import Context
from .environment import Environment
from .fusionapi import FusionClient, SpriteClient

logger = logging.getLogger(__name__)


def get_prefix(bot: PokeFusion, message: Message) -> Sequence[str]:
    if not message.guild:
        return bot.default_prefix

    try:
        prefix = bot.db.get_server(message.guild).prefix
    except AttributeError:
        prefix = bot.default_prefix

    return commands.when_mentioned_or(prefix)(bot, message)


class PokeFusion(commands.Bot):
    COGS_MODULE_PREFIX = cogs.__name__

    def __init__(self, config: BotConfig, **kwargs):
        super().__init__(command_prefix=get_prefix, **kwargs)
        self.config = config
        self.boot_time: datetime = datetime.now()
        self.owner_id: int = config.owner_id
        self.default_prefix = config.default_prefix
        self.init_cogs = config.init_cogs
        self.block_dms = config.block_dms
        self.fusion_client: FusionClient = FusionClient()
        self.sprite_client: SpriteClient = SpriteClient()
        self._main_color: discord.Color | None = None
        self._before_invokes: list[Callable[[Context], Awaitable[Any]]] = []
        self._after_invokes: list[Callable[[Context], Awaitable[Any]]] = []
        self.after_invoke: Callable[Callable[[Context], Awaitable[Any]], None] = lambda _: None
        self.before_invoke: Callable[Callable[[Context], Awaitable[Any]], None] = lambda _: None
        self.patch_invoke_hooks()
        self.before_invoke(self.log_command)
        self.add_check(self.check_maintenance, call_once=True)
        self.add_check(self.check_block_dms)
        if self.config.env is not Environment.PROD:
            self.on_command_error = self.debug_error

    def patch_invoke_hooks(self) -> None:
        async def pre_invoke_caller(ctx: Context) -> None:
            for hook in self._before_invokes:
                await hook(ctx)

        async def post_invoke_caller(ctx: Context) -> None:
            for hook in self._after_invokes:
                await hook(ctx)

        def before_invoke(coro: Callable[[Context], Awaitable[Any]]):
            self._before_invokes.append(coro)

        def after_invoke(coro: Callable[[Context], Awaitable[Any]]):
            self._after_invokes.append(coro)

        self._before_invoke = pre_invoke_caller
        self._after_invoke = post_invoke_caller

        self.before_invoke = before_invoke
        self.after_invoke = after_invoke

    async def check_maintenance(self, ctx: Context) -> bool:
        if await ctx.bot.is_owner(ctx.author):
            return True

        is_maintenance = self.db.get_settings().maintenance_mode
        if is_maintenance:
            await ctx.send("Please wait, the bot is in maintenance mode.")
        return not is_maintenance

    async def check_block_dms(self, ctx: Context) -> bool:
        if self.block_dms and ctx.guild is None:
            await ctx.send("DMs not allowed.")
            return False
        return True

    async def get_owner(self) -> User:
        owner = self.get_user(self.owner_id)
        if owner:
            return owner

        return await self.fetch_user(self.owner_id)

    @property
    def uptime(self) -> float:
        delta = datetime.now() - self.boot_time
        return delta.total_seconds()

    @property
    def db(self) -> Database | None:
        return self.get_cog("Database")

    @property
    def main_color(self) -> discord.Color:
        if self._main_color is None:
            try:
                self._main_color = AssetManager.get_asset_color(AssetManager.get_avatar_path(self.config.env))
            except OSError:
                self._main_color = discord.Color.light_grey()
        return self._main_color

    async def get_context(self, origin: Message | Interaction, /, *, cls=Context) -> Context:
        return await super().get_context(origin, cls=cls)

    async def setup_hook(self) -> None:
        for cog in self.init_cogs:
            logger.info(f"Loading cog: {cog}")
            await self.load_extension(f"{PokeFusion.COGS_MODULE_PREFIX}.{cog}")

    # noinspection PyMethodMayBeStatic
    async def debug_error(self, ctx: Context, exception: CommandError, /) -> None:
        if exc := traceback.format_exc():
            await ctx.safe_send(f"```py\n{exc}\n```")

    @staticmethod
    async def log_command(ctx: Context) -> None:
        msg = ctx.message.content.replace(ctx.prefix, "", 1)
        logger.info(f"{msg} in #{ctx.channel} ({ctx.guild}) by {ctx.author}")

    async def close(self) -> None:
        logger.info(f"Initiating graceful exit")
        await super().close()
