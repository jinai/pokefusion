import logging
import os
import random
from collections import defaultdict

from discord import Message, TextChannel
from discord.ext import commands

from pokefusion import utils
from pokefusion.bot import PokeFusion
from pokefusion.configmanager import ConfigManager
from pokefusion.context import Context
from pokefusion.fusionapi import FusionResult, Language, Sprite
from pokefusion.imagelib import FilterType
from pokefusion.pokeapi import PokeApiClient, PokeApiResult
from .cogutils import description_embed, guess_filter_embed, guess_fusion_embed

logger = logging.getLogger(__name__)


def normalize(string: str) -> str:
    return utils.normalize(string, wrap=lambda s: s.lower(), remove_extra_spaces=True)


def shuffle(word: str) -> str:
    characters = list(word)
    random.shuffle(characters)
    return ''.join(characters)


def remove_forms(name: str) -> str:
    if (index := name.find("-")) != -1:
        return name[:index]
    return name


def load_pokemon_names() -> dict[Language, list[str]]:
    data = {}
    for path in ConfigManager.get_pokedex():
        lang = Language(os.path.splitext(filename := os.path.basename(path))[0].split("_")[-1])  # pokedex_{lang}.json
        raw = ConfigManager.read_json(filename)
        data[lang] = [normalize(value) for key, value in raw.items() if int(key) < 899]
    return data


class Games(commands.Cog):
    def __init__(self, bot: PokeFusion):
        self.bot = bot
        self.fusion_client = bot.fusion_client
        self.sprite_client = bot.sprite_client
        self.last_answers: dict[TextChannel, Sprite | FusionResult | PokeApiResult] = {}
        self.hints_counter: defaultdict[TextChannel, int] = defaultdict(int)
        self.last_shuffles: defaultdict[TextChannel, list[tuple[str, str]]] = defaultdict(list)
        self._pokemon_names: dict[Language, list[str]] = {}

    def cog_load(self) -> None:
        self._pokemon_names = load_pokemon_names()
        logger.info(f"Loaded {len(self._pokemon_names[Language.DEFAULT])} Pokémon names")

    def cog_unload(self) -> None:
        self._pokemon_names = {}

    @commands.Cog.listener()
    async def on_message(self, message: Message) -> None:
        channel = message.channel
        if message.author.bot or not (channel in self.last_answers or channel in self.last_shuffles):
            return

        ctx = await self.bot.get_context(message)
        message_content = normalize(ctx.message.content)

        if channel in self.last_shuffles:
            for index in range(len(self.last_shuffles[channel]) - 1, -1, -1):
                word = self.last_shuffles[channel][index]
                if normalize(word[1]) in message_content:
                    del self.last_shuffles[channel][index]
                    await ctx.score(rank=1)
                    await ctx.send(f"Pokémon name found: **{word[0]}** -> **{word[1]}**")

        if channel in self.last_answers:
            answer = self.last_answers[channel]
            if isinstance(answer, Sprite):
                compare = lambda x, y: normalize(y.lookup.species) in x
            elif isinstance(answer, FusionResult):
                compare = lambda x, y: set([remove_forms(p) for p in x.split(" ")]).issuperset(set([p for p in
                                                                                                    f"{remove_forms(normalize(y.head.species))} {remove_forms(normalize(y.body.species))}".split(
                                                                                                        " ")]))
            else:  # PokeApiResult
                compare = lambda x, y: normalize(y.name_fr) in x

            if compare(message_content, answer):
                del self.last_answers[channel]
                self.hints_counter.pop(channel, None)
                await ctx.score(1)

    @commands.group(invoke_without_command=True)
    async def guess(self, ctx: Context):
        await ctx.send(
            "Available guessing games: Silhouette, Blur, Pixel, Grayscale, Edge, Box, Swirl, PixelBlur, Fusion, PixelFusion, FusionBox and Description")

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

    @guess.command(name="swirl", aliases=["sw"])
    async def guess_swirl(self, ctx: Context) -> None:
        sprite = self.sprite_client.get_sprite("?")
        self.last_answers[ctx.channel] = sprite

        embed, files = guess_filter_embed(ctx, [FilterType.SWIRL], sprite)
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

    @guess.command(name="fb")
    async def guess_fusionbox(self, ctx: Context):
        result = self.fusion_client.fusion()
        self.last_answers[ctx.channel] = result
        embed, files = guess_fusion_embed(ctx, result, filters=[FilterType.BOX])
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

    @commands.command(aliases=["h"])
    async def hint(self, ctx: Context):
        if ctx.channel in self.last_answers:
            hint_num = self.hints_counter[ctx.channel]
            answer = self.last_answers[ctx.channel]
            if isinstance(answer, Sprite):
                message = f"Hint: `{answer.lookup.species[:hint_num + 1]}`"
            elif isinstance(answer, FusionResult):
                head, body = answer.head, answer.body
                message = f"Hint: `{head.species[:hint_num + 1]}    {body.species[:hint_num + 1]}`"
            else:  # PokeApiResult
                if hint_num == 0:
                    message = f"Hint: `{answer.generation}G`"
                elif hint_num == 1:
                    if not answer.type_2:
                        message = f"Hint: `{answer.type_1}`"
                    else:
                        message = f"Hint: `{answer.type_1} {PokeApiClient.REDACTED_STRING}`"
                else:
                    types = f"{answer.type_1} {answer.type_2}".strip()
                    message = f"Hint: `{types}`"

            self.hints_counter[ctx.channel] += 1
            await ctx.send(message)

    @guess_silhouette.before_invoke
    @guess_pixel.before_invoke
    @guess_blur.before_invoke
    @guess_grayscale.before_invoke
    @guess_edge.before_invoke
    @guess_box.before_invoke
    @guess_swirl.before_invoke
    @guess_pixelblur.before_invoke
    @guess_fusion.before_invoke
    @guess_pixelfusion.before_invoke
    @guess_fusionbox.before_invoke
    @guess_description.before_invoke
    @guess_giveup.before_invoke
    async def reveal_answer(self, ctx: Context) -> None:
        if ctx.channel in self.last_answers:
            answer = self.last_answers[ctx.channel]
            if isinstance(answer, Sprite):
                message = f"The answer was: **{answer.lookup.species}**"
            elif isinstance(answer, FusionResult):
                head, body = answer.head, answer.body
                message = f"The answer was: **{head.species} {body.species}**"
            else:  # PokeApiResult
                message = f"The answer was: **{answer.name_fr}**"

            del self.last_answers[ctx.channel]
            self.hints_counter.pop(ctx.channel, None)

            await ctx.send(message)

    @commands.group(invoke_without_command=True)
    async def shuffle(self, ctx: Context):
        if self.last_shuffles[ctx.channel]:
            words = utils.special_join([f"**{word[0]}**" for word in self.last_shuffles[ctx.channel]], ", ", " et ")
            await ctx.send(f"Pokémon names to find: {words}")
        else:
            await ctx.send(
                f"No Pokémon name to find, use `{ctx.prefix}shuffle new` to get one")

    @shuffle.command(name="new")
    async def shuffle_new(self, ctx: Context):
        word = random.choice(self._pokemon_names[ctx.lang])
        shuffled = shuffle(word).lower()
        self.last_shuffles[ctx.channel].append((shuffled, word))
        await ctx.send(f"Find the Pokémon name: **{shuffled}**")

    @shuffle.command(name="giveup", aliases=["ff"])
    async def shuffle_giveup(self, ctx: Context):
        if ctx.channel in self.last_shuffles:
            solution = self.last_shuffles[ctx.channel][-1]  # last solution
            message = f"The last Pokémon name was: **{solution}**"

            self.last_shuffles[ctx.channel].remove(solution)
            await ctx.send(message)

    @commands.is_owner()
    @shuffle.command(name="debug")
    async def shuffle_debug(self, ctx: Context):
        output = f"```\n#{ctx.channel.name}:\n"
        for solution in self.last_shuffles[ctx.channel]:
            output += f"\t{solution}\n"
        output += "```"
        await ctx.send(output)


async def setup(bot: PokeFusion) -> None:
    await bot.add_cog(Games(bot))
