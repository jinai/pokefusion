import discord
from discord.ext import commands

from pokefusion import imagelib
from pokefusion.bot.context import Context, Reply
from pokefusion.bot.pokefusion import PokeFusion
from .cogutils import unknown_prompt


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
            file = discord.File(fp=sprites, filename=filename)

            await ctx.send(file=file)
            return

        reply = await unknown_prompt(ctx, sprite.lookup.guess)

        if reply is Reply.Yes:
            # noinspection PyTypeChecker
            await ctx.invoke(self.shiny, species=sprite.lookup.guess)


async def setup(bot: PokeFusion) -> None:
    await bot.add_cog(Misc(bot))
