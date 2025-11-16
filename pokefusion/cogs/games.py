from collections import defaultdict

from discord import Message, TextChannel
from discord.ext import commands

from pokefusion import utils
from pokefusion.bot import PokeFusion
from pokefusion.cogs.cogutils import description_embed, guess_filter_embed, guess_fusion_embed
from pokefusion.context import Context
from pokefusion.fusionapi import FusionResult, Sprite
from pokefusion.imagelib import FilterType
from pokefusion.pokeapi import PokeApiClient, PokeApiResult


def normalize(string: str) -> str:
    return utils.remove_extra_spaces(utils.normalize(string.lower()))


def remove_forms(name: str) -> str:
    if (index := name.find("-")) != -1:
        return name[:index]
    return name


class Games(commands.Cog):
    def __init__(self, bot: PokeFusion):
        self.bot = bot
        self.fusion_client = bot.fusion_client
        self.sprite_client = bot.sprite_client
        self.last_answers: dict[TextChannel, Sprite | FusionResult | PokeApiResult] = {}
        self.hints_counter: defaultdict[TextChannel, int] = defaultdict(int)

    @commands.Cog.listener()
    async def on_message(self, message: Message) -> None:
        if message.author.id == self.bot.user.id or message.channel not in self.last_answers:
            return

        ctx = await self.bot.get_context(message)
        correct_answer = self.last_answers[ctx.channel]
        if isinstance(correct_answer, Sprite):
            compare = lambda x, y: x == normalize(y.lookup.species)
        elif isinstance(correct_answer, FusionResult):
            compare = lambda x, y: set([remove_forms(p) for p in x.split(" ")]) == {
                remove_forms(normalize(y.head.species)), remove_forms(normalize(y.body.species))}
        else:  # PokeApiResult
            compare = lambda x, y: x == normalize(y.name_fr)

        message_content = normalize(ctx.message.content)
        if compare(message_content, correct_answer):
            del self.last_answers[ctx.channel]
            self.hints_counter.pop(ctx.channel, None)
            await ctx.score(1)

    @commands.group(invoke_without_command=True)
    async def guess(self, ctx: Context):
        await ctx.send(
            "Available guessing games: Silhouette, Blur, Pixel, Grayscale, Edge, Box, PixelBlur, Fusion, PixelFusion, Description")

    @guess.command(name="giveup", aliases=["ff"])
    async def guess_giveup(self, ctx: Context):
        pass

    @guess.command(name="silhouette", aliases=["sil"])
    async def guess_silhouette(self, ctx: Context):
        sprite = self.sprite_client.get_sprite("?")
        self.last_answers[ctx.channel] = sprite

        embed, files = guess_filter_embed(ctx, [FilterType.SILHOUETTE], sprite)
        await ctx.send(embed=embed, files=files)

    @guess.command(name="blur")
    async def guess_blur(self, ctx: Context) -> None:
        sprite = self.sprite_client.get_sprite("?")
        self.last_answers[ctx.channel] = sprite

        embed, files = guess_filter_embed(ctx, [FilterType.GAUSSIAN_BLUR], sprite)
        await ctx.send(embed=embed, files=files)

    @guess.command(name="pixel")
    async def guess_pixel(self, ctx: Context) -> None:
        sprite = self.sprite_client.get_sprite("?")
        self.last_answers[ctx.channel] = sprite

        embed, files = guess_filter_embed(ctx, [FilterType.PIXELATE], sprite)
        await ctx.send(embed=embed, files=files)

    @guess.command(name="grayscale", aliases=["gray", "grey", "greyscale"])
    async def guess_grayscale(self, ctx: Context) -> None:
        sprite = self.sprite_client.get_sprite("?")
        self.last_answers[ctx.channel] = sprite

        embed, files = guess_filter_embed(ctx, [FilterType.GRAYSCALE], sprite)
        await ctx.send(embed=embed, files=files)

    @guess.command(name="edge", aliases=["edges"])
    async def guess_edge(self, ctx: Context) -> None:
        sprite = self.sprite_client.get_sprite("?")
        self.last_answers[ctx.channel] = sprite

        embed, files = guess_filter_embed(ctx, [FilterType.EDGE], sprite)
        await ctx.send(embed=embed, files=files)

    @guess.command(name="box")
    async def guess_box(self, ctx: Context) -> None:
        sprite = self.sprite_client.get_sprite("?")
        self.last_answers[ctx.channel] = sprite

        embed, files = guess_filter_embed(ctx, [FilterType.BOX], sprite)
        await ctx.send(embed=embed, files=files)

    @guess.command(name="pixelblur", aliases=["pb"])
    async def guess_pixelblur(self, ctx: Context) -> None:
        sprite = self.sprite_client.get_sprite("?")
        self.last_answers[ctx.channel] = sprite

        embed, files = guess_filter_embed(ctx, [FilterType.GAUSSIAN_BLUR, FilterType.PIXELATE], sprite)
        await ctx.send(embed=embed, files=files)

    @guess.command(name="fusion")
    async def guess_fusion(self, ctx: Context):
        result = self.fusion_client.fusion()
        self.last_answers[ctx.channel] = result
        embed, files = guess_fusion_embed(ctx, result)
        await ctx.send(embed=embed, files=files)

    @guess.command(name="pf")
    async def guess_pixelfusion(self, ctx: Context):
        result = self.fusion_client.fusion()
        self.last_answers[ctx.channel] = result
        embed, files = guess_fusion_embed(ctx, result, filters=[FilterType.PIXELATE])
        await ctx.send(embed=embed, files=files)

    # @guess.command(name="test")
    # async def guess_test(self, ctx: Context):
    #     result = self.fusion_client.fusion("Plumeline-Flamenco", "Mime Jr.", lang=ctx.lang)
    #     self.last_answers[ctx.channel] = result
    #     embed, files = guess_fusion_embed(ctx, result)
    #     await ctx.send(embed=embed, files=files)

    @guess.command(name="description", aliases=["desc"])
    async def guess_description(self, ctx: Context) -> None:
        result = await PokeApiClient.get_random_pokemon()
        self.last_answers[ctx.channel] = result
        embed, files = description_embed(ctx, result.get_random_desc())
        await ctx.send(embed=embed, files=files)

    @commands.group(invoke_without_command=True, pass_context=True)
    async def hint(self, ctx: Context):
        if ctx.channel in self.last_answers:
            hint_num = self.hints_counter[ctx.channel]
            answer = self.last_answers[ctx.channel]
            if isinstance(answer, Sprite):
                message = f"Indice : `{answer.lookup.species[:hint_num + 1]}`"
            elif isinstance(answer, FusionResult):
                head, body = answer.head, answer.body
                message = f"Indice : `{head.species[:hint_num + 1]}    {body.species[:hint_num + 1]}`"
            else:  # PokeApiResult
                if hint_num == 0:
                    message = f"Indice : `{answer.generation}G`"
                elif hint_num == 1:
                    if not answer.type_2:
                        message = f"Indice : `{answer.type_1}`"
                    else:
                        message = f"Indice : `{answer.type_1} {PokeApiClient.REDACTED_STRING}`"
                else:
                    types = f"{answer.type_1} {answer.type_2}".strip()
                    message = f"Indice : `{types}`"

            self.hints_counter[ctx.channel] += 1
            await ctx.send(message)

    @guess_silhouette.before_invoke
    @guess_pixel.before_invoke
    @guess_blur.before_invoke
    @guess_grayscale.before_invoke
    @guess_edge.before_invoke
    @guess_box.before_invoke
    @guess_pixelblur.before_invoke
    @guess_fusion.before_invoke
    @guess_pixelfusion.before_invoke
    @guess_description.before_invoke
    @guess_giveup.before_invoke
    async def reveal_answer(self, ctx: Context) -> None:
        if ctx.channel in self.last_answers:
            answer = self.last_answers[ctx.channel]
            if isinstance(answer, Sprite):
                message = f"La réponse était : **{answer.lookup.species}**"
            elif isinstance(answer, FusionResult):
                head, body = answer.head, answer.body
                message = f"La réponse était : **{head.species} {body.species}**"
            else:  # PokeApiResult
                message = f"La réponse était : **{answer.name_fr}**"

            del self.last_answers[ctx.channel]
            self.hints_counter.pop(ctx.channel, None)

            await ctx.send(message)


async def setup(bot: PokeFusion) -> None:
    await bot.add_cog(Games(bot))
