from datetime import datetime
from typing import Annotated

from discord.ext import commands
from discord.ext.commands import BadArgument, CommandError

from pokefusion.bot import PokeFusion
from pokefusion.context import Context
from pokefusion.converters import LanguageConverter, PrefixConverter
from pokefusion.fusionapi import Language


class Admin(commands.Cog):
    def __init__(self, bot: PokeFusion) -> None:
        self.bot = bot

    async def cog_check(self, ctx: Context) -> bool:
        return (await commands.check_any(commands.is_owner(),
                                         commands.has_guild_permissions(manage_guild=True)).predicate(ctx) and
                await commands.guild_only().predicate(ctx))

    async def cog_command_error(self, ctx: Context, error: CommandError) -> None:
        if isinstance(error, BadArgument):
            await ctx.send(str(error))

    @commands.command()
    async def prefix(self, ctx: Context, *, new_prefix: Annotated[str, PrefixConverter] = None) -> None:
        if new_prefix is None:
            prefix = ctx.db.get_server(ctx.guild).prefix
            await ctx.send(f"Current prefix: `{prefix}`")
        else:
            ctx.db.update_server(ctx.guild, {"prefix": new_prefix, "updated_at": datetime.now()})
            await ctx.tick(True)

    @commands.command()
    async def lang(self, ctx: Context, *, new_lang: Annotated[Language, LanguageConverter] = None) -> None:
        if new_lang is None:
            await ctx.send(f"Current language: `{ctx.lang}`")
        else:
            ctx.db.update_server(ctx.guild, {"lang": new_lang, "updated_at": datetime.now()})
            await ctx.tick(True)


async def setup(bot: PokeFusion) -> None:
    await bot.add_cog(Admin(bot))
