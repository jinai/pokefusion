from discord import Member
from discord.ext import commands

from pokefusion.bot.context import Context, Reply
from pokefusion.bot.pokefusion import PokeFusion
from pokefusion.db.database import database
from pokefusion.db.models import User
from pokefusion.fusionapi import FusionClient, FusionResult
from .cogutils import confirm_prompt, fusion_embed, unknown_prompt

POKEDEX_DETAILS = (
    "[List of available Pokémon]"
    "(https://infinitefusion.fandom.com/wiki/Pokédex) "
    f"(up to #{FusionClient.MAX_ID})"
)


class Fusion(commands.Cog):
    def __init__(self, bot: PokeFusion) -> None:
        self.bot = bot
        self.client = bot.fusion_client
        self.last_queries = {}

    async def _send_embed(self, ctx: Context, result: FusionResult, title: str) -> None:
        self.last_queries[ctx.channel] = result
        embed, files = fusion_embed(ctx, result, title=title)
        await ctx.send(embed=embed, files=files)

    @commands.command(aliases=["f"])
    async def fusion(self, ctx: Context, head: str = "?", body: str = "?"):
        result = self.client.fusion(head, body, ctx.lang)

        if result.succeeded:
            await self._send_embed(ctx, result, title="Fusion")
            return

        head_guess = result.head.guess if result.head.failed else head
        body_guess = result.body.guess if result.body.failed else body

        reply = await unknown_prompt(ctx, head_guess, body_guess, details=POKEDEX_DETAILS)

        if reply is Reply.Yes:
            # noinspection PyTypeChecker
            await ctx.invoke(self.fusion, head=head_guess, body=body_guess)

    @commands.command(aliases=["fc"])
    async def fusion_custom(self, ctx: Context, head: str = "?"):
        result = self.client.fusion(head, "?", ctx.lang, custom_only=True)

        if result.succeeded:
            await self._send_embed(ctx, result, title="Fusion")
            return

        head_guess = result.head.guess if result.head.failed else head

        reply = await unknown_prompt(ctx, head_guess, details=POKEDEX_DETAILS)

        if reply is Reply.Yes:
            # noinspection PyTypeChecker
            await ctx.invoke(self.fusion_custom, head=head_guess)

    @commands.command(aliases=["s"])
    async def swap(self, ctx: Context):
        if ctx.channel in self.last_queries:
            result: FusionResult = self.last_queries[ctx.channel]
            # noinspection PyTypeChecker
            await ctx.invoke(self.fusion, head=result.body.species, body=result.head.species)

    @commands.command(aliases=["r"])
    async def repeat(self, ctx: Context):
        if ctx.channel in self.last_queries:
            result: FusionResult = self.last_queries[ctx.channel]
            # noinspection PyTypeChecker
            await ctx.invoke(self.fusion, head=result.head_query, body=result.body_query)

    @commands.command(aliases=["t"])
    async def totem(self, ctx: Context, user: Member | None = None):
        user = user or ctx.author
        result = self.bot.totem_service.get_or_create(user.id)
        await self._send_embed(ctx, result, title=f"Totem - {user.display_name}")

    @commands.command(aliases=["fr"])
    async def freereroll(self, ctx: Context):
        user = ctx.author
        user_db = User.get_or_create(discord_id=ctx.author.id, defaults={"name": ctx.author.name})[0]

        if user_db.free_rerolls < 1:
            await ctx.send("You don't have enough free rerolls.")
            return

        desc = f"Reroll your totem?"

        reply = await confirm_prompt(ctx, desc)

        if reply is Reply.Yes:
            with database.atomic():
                self.bot.totem_service.reroll_totem(user.id)
                User.add_free_rerolls(user.id, -1)

            # noinspection PyTypeChecker
            await ctx.invoke(self.totem)

    @commands.command()
    async def fru(self, ctx: Context, user: Member | None = None):
        user = user or ctx.author
        user_db = User.get_or_create(discord_id=ctx.author.id, defaults={"name": ctx.author.name})[0]

        if ctx.author.id == user.id:
            msg = f"You have {user_db.free_rerolls} free reroll(s). Type `{ctx.clean_prefix}fr` to use it."
        else:
            msg = f"{user.display_name} has {user_db.free_rerolls} free rerolls."

        await ctx.send(msg)


async def setup(bot: PokeFusion) -> None:
    await bot.add_cog(Fusion(bot))
