from discord.ext.commands import BadArgument, Converter

from pokefusion.context import Context
from pokefusion.fusionapi import Language
from pokefusion.utils import special_join


class PrefixConverter(Converter):
    async def convert(self, ctx: Context, argument: str) -> str:
        size = len(argument)
        if size < 1 or size > 2:
            raise BadArgument("The prefix must be 1 or 2 characters long.")
        return argument


class LanguageConverter(Converter):
    LANGUAGES = special_join([f"`{lang}`" for lang in Language], ", ", " or ")

    async def convert(self, ctx: Context, argument: str) -> Language:
        if argument not in Language:
            raise BadArgument(f"The language must be one of {LanguageConverter.LANGUAGES}")
        return Language(argument)


class ModuleConverter(Converter):
    async def convert(self, ctx: Context, argument: str) -> str:
        if not argument.startswith(ctx.bot.COGS_MODULE_PREFIX):
            return ctx.bot.COGS_MODULE_PREFIX + "." + argument
        return argument


class ShuffleCooldownConverter(Converter):
    COOLDOWN_MIN = 10
    COOLDOWN_MAX = 4 * 60
    COOLDOWN_DEFAULT = 10

    async def convert(self, ctx: Context, argument: str) -> int:
        if not argument.isdigit():
            raise BadArgument("The shuffle cooldown must be an integer (specified in minutes).")
        cooldown = int(argument)
        if cooldown < ShuffleCooldownConverter.COOLDOWN_MIN or cooldown > ShuffleCooldownConverter.COOLDOWN_MAX:
            raise BadArgument(
                f"The shuffle cooldown must be between {ShuffleCooldownConverter.COOLDOWN_MIN} and {ShuffleCooldownConverter.COOLDOWN_MAX} minutes.")
        return cooldown


class ShuffleVarianceConverter(Converter):
    VARIANCE_MIN = 0
    VARIANCE_MAX = 4 * 60
    VARIANCE_DEFAULT = 0

    async def convert(self, ctx: Context, argument: str) -> int:
        if not argument.isdigit():
            raise BadArgument("The shuffle variance must be an integer (specified in minutes).")
        variance = int(argument)
        if variance < ShuffleVarianceConverter.VARIANCE_MIN or variance > ShuffleVarianceConverter.VARIANCE_MAX:
            raise BadArgument(
                f"The shuffle variance must be between {ShuffleVarianceConverter.VARIANCE_MIN} and {ShuffleVarianceConverter.VARIANCE_MAX} minutes.")
        return variance
