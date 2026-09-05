from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Sequence
from datetime import datetime
from io import BytesIO
from typing import Any

from discord import Color, HTTPException, Intents, Interaction, Message, User
from discord.ext import commands
from discord.ext.commands import CommandError
from peewee import DatabaseError

from pokefusion.bot.context import Context
from pokefusion.configmanager import BotConfig
from pokefusion.db.models import Server, Settings, User as DatabaseUser
from pokefusion.fusionapi import FusionClient, SpriteClient
from pokefusion.imagelib import get_dominant_color
from pokefusion.pokeapi import PokeApiClient
from pokefusion.services.totem import TotemService

logger = logging.getLogger(__name__)


def get_prefix(bot: PokeFusion, message: Message) -> Sequence[str]:
    if not message.guild:
        return bot.default_prefix

    try:
        prefix = Server.get(Server.discord_id == message.guild.id).prefix
    except AttributeError:
        prefix = bot.default_prefix

    return commands.when_mentioned_or(prefix)(bot, message)


class PokeFusion(commands.Bot):
    CORE_EXTENSIONS: tuple[str, ...] = (
        "pokefusion.cogs.events",
    )

    def __init__(self, config: BotConfig, *, intents: Intents):
        super().__init__(
            command_prefix=get_prefix,
            intents=intents,
            case_insensitive=True,
            owner_id=config.owner_id,
        )

        # Configuration
        self.config = config
        self.default_prefix = config.default_prefix
        self.default_language = config.default_language
        self.block_dms = config.block_dms

        # Runtime state
        self.main_color: Color = Color.light_grey()
        self.boot_time: datetime = datetime.now()

        # Clients and services
        self.fusion_client = FusionClient(self.default_language)
        self.sprite_client = SpriteClient(self.default_language)
        self.pokeapi_client = PokeApiClient(self.config.pokeapi_url)
        self.totem_service = TotemService(self.fusion_client)

        # Invoke hooks
        self._before_invokes: list[Callable[[Context], Awaitable[Any]]] = []
        self._after_invokes: list[Callable[[Context], Awaitable[Any]]] = []

        self.before_invoke: Callable[Callable[[Context], Awaitable[Any]], None] = lambda _: None
        self.after_invoke: Callable[Callable[[Context], Awaitable[Any]], None] = lambda _: None

        self.patch_invoke_hooks()

        self.before_invoke(self.log_command)
        self.before_invoke(self.create_user)

        # Checks
        self.add_check(self.check_maintenance, call_once=True)
        self.add_check(self.check_block_dms)

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

    @staticmethod
    async def check_maintenance(ctx: Context) -> bool:
        if await ctx.bot.is_owner(ctx.author):
            return True

        maintenance = Settings.is_maintenance()
        if maintenance:
            await ctx.send("Please wait, the bot is in maintenance mode.")
        return not maintenance

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

    async def _resolve_main_color(self) -> Color:
        fallback_color = self.main_color

        if configured_color := self.config.main_color:
            try:
                return Color.from_str(configured_color)
            except ValueError:
                logger.warning(f"Invalid main color {self.config.main_color!r}, deriving it from the bot avatar")

        if self.user is None:
            logger.error(f"Couldn't derive the main color: bot user is unavailable")
            return fallback_color

        try:
            avatar = self.user.display_avatar.with_format("png")
            avatar_data = await avatar.read()
            rgb = get_dominant_color(BytesIO(avatar_data), normalize=True)
            return Color.from_rgb(*rgb)
        except (HTTPException, OSError) as e:
            logger.error(f"Couldn't derive the main color from the bot avatar: {e}")
            return fallback_color

    async def get_context(self, origin: Message | Interaction, /, *, cls=Context) -> Context:
        return await super().get_context(origin, cls=cls)

    async def setup_hook(self) -> None:
        await self.pokeapi_client.start()

        self.main_color = await self._resolve_main_color()
        logger.info(f"Set main color to: {self.main_color}")

        for extension in self.CORE_EXTENSIONS:
            logger.info(f"Loading core extension '{extension}'")
            await self.load_extension(extension)

        for extension in self.config.extensions:
            if extension in self.CORE_EXTENSIONS:
                continue

            logger.info(f"Loading extension '{extension}'")
            await self.load_extension(extension)

    @staticmethod
    async def log_command(ctx: Context) -> None:
        logger.info(f"{ctx.message.content} in #{ctx.channel} ({ctx.guild}) by {ctx.author}")

    @staticmethod
    async def create_user(ctx: Context) -> None:
        try:
            DatabaseUser.get_or_create(discord_id=ctx.author.id, defaults={"name": ctx.author.name})
        except DatabaseError as e:
            raise CommandError(f"Failed to create user: {ctx.author.name} ({ctx.author.id})") from e

    async def close(self) -> None:
        await self.pokeapi_client.close()
        await super().close()
