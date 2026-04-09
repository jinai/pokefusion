from typing import Annotated

from discord.ext import commands
from discord.ext.commands import BadArgument, CommandError

from pokefusion.bot.context import Context
from pokefusion.bot.converters import LanguageConverter, PrefixConverter
from pokefusion.bot.pokefusion import PokeFusion
from pokefusion.db.models import Server
from pokefusion.enums import Language


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
            prefix = Server.get(Server.discord_id == ctx.guild.id).prefix
            await ctx.send(f"Current prefix: `{prefix}`")
        else:
            q = Server.update(prefix=new_prefix).where(Server.discord_id == ctx.guild.id)
            await ctx.tick(q.execute())

    @commands.command()
    async def lang(self, ctx: Context, *, new_lang: Annotated[Language, LanguageConverter] = None) -> None:
        if new_lang is None:
            await ctx.send(f"Current language: `{ctx.lang}`")
        else:
            q = Server.update(lang=new_lang).where(Server.discord_id == ctx.guild.id)
            await ctx.tick(q.execute())


async def setup(bot: PokeFusion) -> None:
    await bot.add_cog(Admin(bot))
