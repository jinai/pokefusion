import asyncio
from datetime import date

from discord import Color
from discord.ext import commands
from discord.ext.commands import CheckFailure, CommandError

from pokefusion.bot.pokefusion import PokeFusion
from pokefusion.bot.context import Context
from pokefusion.db.models import User
from .cogutils import christmas_embed


def is_christmas_period() -> bool:
    # 18 Dec <= Today < 1 Jan
    # Try to make it coincide with a Thursday reset
    today = date.today()
    start = date(today.year, 12, 18)
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
        if is_christmas_period():
            user_db = User.get_or_create(discord_id=ctx.author.id, defaults={"name": ctx.author.name})[0]
            if not user_db.xmas_prompt:
                embed, files = christmas_embed(ctx, color=Color.red())
                prompt = await ctx.send(embed=embed, files=files)
                thumbnail_url = prompt.embeds[0].thumbnail.url
                User.update(xmas_prompt=True).where(User.discord_id == ctx.author.id).execute()
                for i in range(10):
                    await asyncio.sleep(0.6)
                    color = Color.green() if i % 2 == 0 else Color.red()
                    embed, _ = christmas_embed(ctx, color, upload_attachment=False)
                    embed.set_thumbnail(url=thumbnail_url)
                    await prompt.edit(embed=embed, attachments=())


async def setup(bot: PokeFusion) -> None:
    await bot.add_cog(Christmas(bot))
