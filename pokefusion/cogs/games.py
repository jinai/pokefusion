import logging
import os
import random
from collections import defaultdict
from enum import IntEnum, auto
from typing import Annotated

from discord import Message, TextChannel
from discord.ext import commands, tasks
from discord.ext.commands import BadArgument, CommandError

from pokefusion import utils
from pokefusion.assetmanager import AssetManager
from pokefusion.bot import PokeFusion
from pokefusion.cogs.cogutils import description_embed, guess_filter_embed, guess_fusion_embed
from pokefusion.context import Context
from pokefusion.converters import ShuffleCooldownConverter, ShuffleVarianceConverter
from pokefusion.fusionapi import FusionResult, Sprite
from pokefusion.imagelib import FilterType
from pokefusion.pokeapi import PokeApiClient, PokeApiResult

logger = logging.getLogger(__name__)


def normalize(string: str) -> str:
    return utils.remove_extra_spaces(utils.normalize(string.lower()))


def shuffle(word: str) -> str:
    chars = list(word)
    random.shuffle(chars)
    return ''.join(chars)


def remove_forms(name: str) -> str:
    if (index := name.find("-")) != -1:
        return name[:index]
    return name


def get_next_cooldown(cooldown: int, variance: int, seed: int = None) -> int:
    rand = random.Random(seed)
    return cooldown + rand.randint(-variance, variance)


class Difficilty(IntEnum):
    EASY = auto()
    MEDIUM = auto()
    HARD = auto()
    EXPERT = auto()


class SolutionContext:
    def __init__(self, channel: TextChannel, answer: Sprite | FusionResult | PokeApiResult):
        self.channel = channel
        self.answer = answer

    def verify(self, user_answer):
        pass


class Games(commands.Cog):
    def __init__(self, bot: PokeFusion):
        self.bot = bot
        self.fusion_client = bot.fusion_client
        self.sprite_client = bot.sprite_client
        self.last_answers: dict[TextChannel, Sprite | FusionResult | PokeApiResult] = {}
        self.hints_counter: defaultdict[TextChannel, int] = defaultdict(int)
        self._load_words()
        self.solutions_shuffle: defaultdict[TextChannel, list[tuple[str, str]]] = defaultdict(list)
        self._shuffle_task_channels: set[TextChannel] = set()

    def _load_words(self):
        path = os.path.join(AssetManager.MISC_DIR, "wordlist_fr.txt")
        with open(path, "r", encoding="utf-8") as f:
            self.words = f.read().splitlines()

    async def cog_command_error(self, ctx: Context, error: CommandError) -> None:
        if isinstance(error, BadArgument):
            await ctx.send(str(error))

    @commands.Cog.listener()
    async def on_message(self, message: Message) -> None:
        if message.author.id != self.bot.user.id:
            if (chan := message.channel) in self.last_answers or chan in self.solutions_shuffle:
                ctx = await self.bot.get_context(message)
                message_content = normalize(ctx.message.content)

            if message.channel in self.solutions_shuffle:
                for index in range(len(self.solutions_shuffle[ctx.channel]) - 1, -1, -1):
                    word = self.solutions_shuffle[ctx.channel][index]
                    if normalize(word[1]) in message_content:
                        await ctx.score(rank=1)
                        await ctx.send(f"Mot trouvé : **{word[0]}** -> **{word[1]}**")
                        del self.solutions_shuffle[ctx.channel][index]

            if message.channel in self.last_answers:
                correct_answer = self.last_answers[ctx.channel]
                if isinstance(correct_answer, Sprite):
                    compare = lambda x, y: x == normalize(y.lookup.species)
                elif isinstance(correct_answer, FusionResult):
                    compare = lambda x, y: set([remove_forms(p) for p in x.split(" ")]) == {
                        remove_forms(normalize(y.head.species)), remove_forms(normalize(y.body.species))}
                else:  # PokeApiResult
                    compare = lambda x, y: x == normalize(y.name_fr)

                if compare(message_content, correct_answer):
                    del self.last_answers[ctx.channel]
                    self.hints_counter.pop(ctx.channel, None)
                    await ctx.score(rank=1)

    @commands.group(invoke_without_command=True)
    async def guess(self, ctx: Context, *, message: str = ""):
        if ctx.channel in self.last_answers:
            user_answer = normalize(message)
            correct_answer = self.last_answers[ctx.channel]
            if isinstance(correct_answer, Sprite):
                compare = lambda x, y: x == normalize(y.lookup.species)
            elif isinstance(correct_answer, FusionResult):
                compare = lambda x, y: set([remove_forms(p) for p in x.split(" ")]) == {
                    remove_forms(normalize(y.head.species)), remove_forms(normalize(y.body.species))}
            else:  # PokeApiResult
                compare = lambda x, y: x == normalize(y.name_fr)

            if compare(user_answer, correct_answer):
                del self.last_answers[ctx.channel]
                self.hints_counter.pop(ctx.channel, None)
                await ctx.score(rank=1)
            else:
                await ctx.tick(False)

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
    #     result = self.fusion_client.fusion("Plumeline-Flamenco", "?", lang=ctx.lang)
    #     self.last_answers[ctx.channel] = result
    #     embed, files = guess_fusion_embed(ctx, result)
    #     await ctx.send(embed=embed, files=files)

    @guess.command(name="description", aliases=["desc"])
    async def guess_description(self, ctx: Context) -> None:
        result = await PokeApiClient.get_random_pokemon()
        # print(result.name_fr)  # TODO: remove
        self.last_answers[ctx.channel] = result
        embed, files = description_embed(ctx, result.get_random_desc())
        await ctx.send(embed=embed, files=files)

    @commands.group(invoke_without_command=True, pass_context=True)
    async def hint(self, ctx: Context):
        if ctx.channel in self.last_answers:
            hint = self.hints_counter[ctx.channel]
            answer = self.last_answers[ctx.channel]
            if isinstance(answer, Sprite):
                message = f"Indice : `{answer.lookup.species[:hint + 1]}`"
            elif isinstance(answer, FusionResult):
                head, body = answer.head, answer.body
                message = f"Indice : `{head.species[:hint + 1]}    {body.species[:hint + 1]}`"
            else:  # PokeApiResult
                if hint < 1:
                    if not answer.type_2:
                        message = f"Indice : `{answer.type_1}`"
                    else:
                        message = f"Indice : `{answer.type_1} {PokeApiClient.REDACTED_STRING}`"
                else:
                    message = f"Indice : `{answer.type_1} {answer.type_2}`"

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
    @guess_description.before_invoke
    @guess_giveup.before_invoke
    async def guess_reveal_answer(self, ctx: Context) -> None:
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

    @commands.group(invoke_without_command=True)
    async def shuffle(self, ctx: Context, *, message: str = ""):
        if self.solutions_shuffle[ctx.channel]:
            words = utils.special_join([f"**{word[0]}**" for word in self.solutions_shuffle[ctx.channel]], ", ", " et ")
            await ctx.send(f"Les mots à trouver sont : {words}")
        else:
            await ctx.send(
                f"Aucun mot à trouver. Faites `{ctx.prefix}shuffle start` ou `{ctx.prefix}shuffle new` pour démarrer")

    @commands.is_owner()
    @shuffle.command(name="debug")
    async def shuffle_debug(self, ctx: Context):
        output = f"```\n#{ctx.channel.name}:\n"
        for solution in self.solutions_shuffle[ctx.channel]:
            output += f"\t{solution}\n"
        output += "```"
        await ctx.send(output)

    @shuffle.command(name="new")
    async def shuffle_new(self, ctx: Context):
        word = random.choice(self.words)
        shuffled = shuffle(word)
        self.solutions_shuffle[ctx.channel].append((shuffled, word))
        await ctx.send(f"Trouvez le mot caché : **{shuffled}**")

    @tasks.loop(minutes=ShuffleCooldownConverter.COOLDOWN_DEFAULT)
    async def shuffle_task(self) -> None:
        for channel in self._shuffle_task_channels:
            word = random.choice(self.words)
            shuffled = shuffle(word)
            self.solutions_shuffle[channel].append((shuffled, word))
            await channel.send(f"Trouvez le mot caché : **{shuffled}**")

    @shuffle.command(name="start")
    async def shuffle_start(
            self,
            ctx: Context,
            cooldown: Annotated[int, ShuffleCooldownConverter] = ShuffleCooldownConverter.COOLDOWN_DEFAULT,
            variance: Annotated[int, ShuffleVarianceConverter] = ShuffleVarianceConverter.VARIANCE_DEFAULT
    ) -> None:
        await ctx.invoke(self.shuffle_stop)
        self.shuffle_task.change_interval(minutes=get_next_cooldown(cooldown, variance))
        logger.debug(f"Next shuffle: {self.shuffle_task.minutes} minutes")
        self.shuffle_task.start()
        self._shuffle_task_channels.add(ctx.channel)
        await ctx.send(f"Un mot caché (anagramme) sera dévoilé toutes les {cooldown} (± {variance}) minutes.")

    @shuffle.command(name="stop", aliases=["cancel"])
    async def shuffle_stop(self, ctx: Context):
        if ctx.channel in self._shuffle_task_channels:
            self.shuffle_task.cancel()
            self._shuffle_task_channels.remove(ctx.channel)
            await ctx.send("Le jeu des mots est arrêté.")

    @shuffle.command(name="giveup", aliases=["ff"])
    async def shuffle_giveup(self, ctx: Context):
        pass

    @shuffle_giveup.before_invoke
    async def shuffle_reveal_answer(self, ctx: Context) -> None:
        if ctx.channel in self.solutions_shuffle:
            solution = self.solutions_shuffle[ctx.channel][-1]  # last solution
            message = f"Le dernier mot caché était : **{solution}**"

            self.solutions_shuffle[ctx.channel].remove(solution)
            await ctx.send(message)


async def setup(bot: PokeFusion) -> None:
    await bot.add_cog(Games(bot))
