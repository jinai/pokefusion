from datetime import datetime

from discord import Color, Embed, Member
from discord.ext import commands

from pokefusion.bot import PokeFusion
from pokefusion.context import Context, Reply
from pokefusion.fusionapi import FusionResult
from .cogutils import fusion_embed, guess_prompt


class Fusion(commands.Cog):
    def __init__(self, bot: PokeFusion):
        self.bot = bot
        self.client = bot.fusion_client
        self.last_queries = {}

    async def _send_embed(self, ctx: Context, result: FusionResult, title: str) -> None:
        self.last_queries[ctx.channel] = result
        embed, files = fusion_embed(ctx, result, title=title)
        await ctx.send(embed=embed, files=files)

    @commands.command(aliases=["f"])
    async def fusion(self, ctx: Context, head="?", body="?"):
        result = self.client.fusion(head, body, ctx.lang)
        if result.succeeded:
            await self._send_embed(ctx, result, title="Fusion")
        else:
            head_guess = result.head.guess if result.head.failed else head
            body_guess = result.body.guess if result.body.failed else body

            cmd = f"{ctx.prefix}{ctx.invoked_with} {head_guess} {body_guess}"
            desc = f"Did you mean: `{cmd}`\n\n[List of available Pokémon](https://infinitefusion.fandom.com/wiki/Pokédex) (up to #{self.client.MAX_ID})"
            reply = await guess_prompt(ctx, desc)

            if reply == Reply.Yes:
                # noinspection PyTypeChecker
                await ctx.invoke(self.fusion, head=head_guess, body=body_guess)

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
    async def totem(self, ctx: Context, user: Member = None):
        user = user or ctx.author
        user_db = self.bot.db.get_or_create_user(user)
        settings = self.bot.db.get_settings()
        seed = settings.global_seed + user_db.seed + user.id
        result = self.client.totem(seed, ctx.lang)
        await self._send_embed(ctx, result, title=f"Totem - {user.display_name}")

    @commands.command(aliases=["fr", "cadeau"])
    async def freereroll(self, ctx: Context):
        user = ctx.author
        user_db = self.bot.db.get_or_create_user(user)

        if user_db.free_rerolls < 1:
            await ctx.send("You don't have enough free rerolls.")
        else:
            desc = f"Reroll {user.display_name}'s totem?"
            embed = Embed(description=desc, color=Color.light_grey())
            embed.set_footer(text="Type yes or no.")
            prompt = await ctx.send(embed=embed)
            reply = await ctx.prompt(timeout=10, delete_reply=True)

            if reply == Reply.NoReply:
                embed.set_footer(text=f"{ctx.author} didn't reply.")
            elif reply == Reply.No:
                embed.set_footer(text=f"{ctx.author} replied no.")
            else:
                embed.set_footer(text=f"{ctx.author} replied yes.")
                user_db = self.bot.db.get_or_create_user(user)
                self.bot.db.update_user(user,
                                        params={"seed": user_db.seed + 1, "free_rerolls": user_db.free_rerolls - 1,
                                                "updated_at": datetime.now()})
                # noinspection PyTypeChecker
                await ctx.invoke(self.totem)

            await prompt.edit(embed=embed, delete_after=10)

    @commands.command()
    async def fru(self, ctx: Context, user: Member = None):
        user = user or ctx.author
        user_db = self.bot.db.get_or_create_user(user)
        msg = f"You have {user_db.free_rerolls} free reroll(s)." if ctx.author.id == user.id else f"{user.display_name} has {user_db.free_rerolls} free rerolls."
        await ctx.send(msg)


async def setup(bot: PokeFusion) -> None:
    await bot.add_cog(Fusion(bot))
