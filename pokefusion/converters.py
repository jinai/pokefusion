from discord.ext.commands import BadArgument, Converter

from .context import Context
from .fusionapi import Language
from .utils import special_join


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
