import asyncio
from calendar import Day
from datetime import date, timedelta

from discord import Color
from discord.ext import commands
from discord.ext.commands import CheckFailure, CommandError

from pokefusion.bot.context import Context
from pokefusion.bot.pokefusion import PokeFusion
from pokefusion.db.models import User
from .cogutils import christmas_embed


def is_christmas_period() -> bool:
    # Check if today is between the Thursday before
    # Christmas week and January 1st
    today = date.today()

    christmas = date(today.year, 12, 25)
    days_back = christmas.weekday() + 7 - Day.THURSDAY

    start = christmas - timedelta(days=days_back)
    end = date(today.year + 1, 1, 1)

    return start <= today < end


class Christmas(commands.Cog):
    def __init__(self, bot: PokeFusion) -> None:
        self.bot = bot
        self.bot.after_invoke(self.christmas_event)

    async def cog_check(self, ctx: Context) -> bool:
        return is_christmas_period()

    async def cog_command_error(self, ctx: Context, error: CommandError) -> None:
        if isinstance(error, CheckFailure):
            await ctx.send("Christmas event is over.")

    @commands.command(aliases=["xmas"])
    async def kdo(self, ctx: Context):
        self.bot.totem_service.reroll_totem(ctx.author.id)
        # noinspection PyTypeChecker
        await ctx.invoke(self.bot.get_command("totem"))

    @staticmethod
    async def christmas_event(ctx: Context) -> None:
        if not is_christmas_period():
            return

        user_db, _ = User.get_or_create(
            discord_id=ctx.author.id,
            defaults={"name": ctx.author.name}
        )

        if user_db.xmas_prompt:
            return

        colors = (
            Color.green(),
            Color.red(),
        )

        embed, files = christmas_embed(ctx, color=colors[-1])

        message = await ctx.send(embed=embed, files=files)

        user_db.xmas_prompt = True
        user_db.save(only=[User.xmas_prompt])

        for index in range(8):
            await asyncio.sleep(0.5)

            embed.colour = colors[index % len(colors)]
            message = await message.edit(embed=embed)


async def setup(bot: PokeFusion) -> None:
    await bot.add_cog(Christmas(bot))
