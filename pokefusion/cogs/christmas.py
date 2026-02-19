import asyncio
from datetime import date

from discord import Color
from discord.ext import commands
from discord.ext.commands import CheckFailure, CommandError

from pokefusion.bot import PokeFusion
from pokefusion.context import Context
from .cogutils import christmas_embed


def is_christmas_period() -> bool:
    # 18 Dec <= Today < 1 Jan
    # Try to make it coincide with a Thursday reset
    today = date.today()
    start = date(today.year, 12, 18)
    end = date(today.year + 1, 1, 1)
    return start <= today < end


class Christmas(commands.Cog):
    def __init__(self, bot: PokeFusion):
        self.bot = bot
        self.client = bot.sprite_client
        self.bot.after_invoke(self.christmas_event)

    async def cog_check(self, ctx: Context) -> bool:
        return is_christmas_period()

    async def cog_command_error(self, ctx: Context, error: CommandError) -> None:
        if isinstance(error, CheckFailure):
            await ctx.send("Christmas event is over.")

    @commands.command(aliases=["xmas"])
    async def kdo(self, ctx: Context):
        self.bot.db.reroll_totem(ctx.author)
        # noinspection PyTypeChecker
        await ctx.invoke(self.bot.get_command("totem"))

    async def christmas_event(self, ctx: Context) -> None:
        if is_christmas_period():
            if not self.bot.db.get_or_create_user(ctx.author).xmas_prompt:
                embed, files = christmas_embed(ctx, color=Color.red())
                prompt = await ctx.send(embed=embed, files=files)
                thumbnail_url = prompt.embeds[0].thumbnail.url
                self.bot.db.update_user(ctx.author, {"xmas_prompt": True})
                for i in range(10):
                    await asyncio.sleep(0.6)
                    color = Color.green() if i % 2 == 0 else Color.red()
                    embed, _ = christmas_embed(ctx, color, upload_attachment=False)
                    embed.set_thumbnail(url=thumbnail_url)
                    await prompt.edit(embed=embed, attachments=())


async def setup(bot: PokeFusion) -> None:
    await bot.add_cog(Christmas(bot))
