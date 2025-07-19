import discord
from discord.ext import commands

from pokefusion import imagelib
from pokefusion.bot import PokeFusion
from pokefusion.context import Context, Reply
from .cogutils import guess_prompt


class Misc(commands.Cog):
    def __init__(self, bot: PokeFusion):
        self.bot = bot
        self.client = bot.sprite_client

    @commands.command(aliases=["sh"])
    async def shiny(self, ctx: Context, species: str):
        sprite = self.client.get_sprite(species)
        if sprite.found:
            filename = f"sprites_{sprite.lookup.dex_id:03}_{sprite.lookup.species}.png"
            sprites = imagelib.merge_images(sprite.path, sprite.path_shiny, pixel_gap=5)
            f = discord.File(fp=sprites, filename=filename)
            await ctx.send(file=f)
        else:
            desc = f"Did you mean: `{ctx.prefix}{ctx.invoked_with} {sprite.lookup.guess}`"
            reply = await guess_prompt(ctx, desc, delete=False)

            if reply == Reply.Yes:
                # noinspection PyTypeChecker
                await ctx.invoke(self.shiny, species=sprite.lookup.guess)


async def setup(bot: PokeFusion) -> None:
    await bot.add_cog(Misc(bot))
