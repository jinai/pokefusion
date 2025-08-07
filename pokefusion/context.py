import asyncio
import contextlib
import io
import re
from enum import Enum, auto

import discord
from discord import Message
from discord.ext import commands

from . import utils
from .cogs.database import Database
from .fusionapi import Language


class Reply(Enum):
    NoReply = auto(),
    Yes = auto(),
    No = auto()


class Context(commands.Context):
    SENSITIVE_MASK = "******"
    SENSITIVE_PATTERNS = [
        r"mfa\.[\w-]{20,}",
        r"[\w-]{23,28}\.[\w-]{6,7}\.[\w-]{27,38}"
    ]
    MEDALS = {
        1: "\N{FIRST PLACE MEDAL}",
        2: "\N{SECOND PLACE MEDAL}",
        3: "\N{THIRD PLACE MEDAL}"
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def db(self) -> Database | None:
        return self.bot.db

    @property
    def lang(self) -> Language:
        if self.guild is None:
            return Language.DEFAULT
        return self.db.get_server(self.guild).lang

    async def tick(self, value: bool = True, /):
        emoji = "\N{BALLOT BOX WITH CHECK}" if value else "\N{CROSS MARK}"
        try:
            await self.message.add_reaction(emoji)
        except discord.HTTPException:
            pass

    async def score(self, rank: int = 1):
        try:
            if rank in Context.MEDALS:
                await self.message.add_reaction(Context.MEDALS[rank])
            else:
                await self.tick(True)
        except discord.HTTPException:
            pass

    async def prompt(self, text: str = None, *, options: list[str] = None, timeout: float = 15.0,
                     target_id: int = None, delete_prompt: bool = False, delete_reply: bool = False) -> Reply:
        target_id = target_id or self.author.id
        prompt_message = None
        if text is not None:
            if options is None:
                options = ["yes", "no"]
            text = f"{text} ({'/'.join(options)})"
            prompt_message = await self.send(text)

        reply = Reply.NoReply

        def check(message: Message) -> bool:
            nonlocal reply

            if message.author.id != target_id or message.channel != self.channel:
                return False

            if utils.yes(message.content):
                reply = Reply.Yes
                return True
            elif utils.no(message.content):
                reply = Reply.No
                return True

            return False

        try:
            reply_message = await self.bot.wait_for("message", check=check, timeout=timeout)
            if delete_reply:
                with contextlib.suppress():
                    await reply_message.delete()
        except asyncio.TimeoutError:
            pass

        if delete_prompt and prompt_message is not None:
            with contextlib.suppress():
                await prompt_message.delete()

        return reply

    async def safe_send(self, content: str, *, escape_mentions: bool = True, hide_sensitive_data: bool = True,
                        filename: str = "message_too_long.txt", **kwargs) -> Message:
        if escape_mentions:
            content = discord.utils.escape_mentions(content)
        if hide_sensitive_data:
            for pattern in Context.SENSITIVE_PATTERNS:
                content = re.sub(pattern, Context.SENSITIVE_MASK, content, flags=re.IGNORECASE)

        if len(content) > 2000:
            fp = io.BytesIO(content.encode())
            return await self.send(file=discord.File(fp, filename=filename), **kwargs)
        else:
            return await self.send(content)
