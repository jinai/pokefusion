from discord.ext.commands import BadArgument, Converter

from pokefusion.context import Context
from pokefusion.fusionapi import Language
from pokefusion.utils import special_join

# languages = " / ".join([str(lang).upper() for lang in Language])
languages = special_join([f"`{lang}`" for lang in Language], ", ", " or ")


class PrefixConverter(Converter):
    async def convert(self, ctx: Context, argument: str) -> str:
        size = len(argument)
        if size < 1 or size > 2:
            raise BadArgument("The prefix must be 1 or 2 characters long.")
        return argument


class LangConverter(Converter):
    async def convert(self, ctx: Context, argument: str) -> Language:
        if argument not in Language:
            raise BadArgument(f"The language must be one of {languages}")
        return Language(argument)


class ModuleConverter(Converter):
    async def convert(self, ctx: Context, argument: str) -> str:
        if not argument.startswith(ctx.bot.COGS_MODULE_PREFIX):
            return ctx.bot.COGS_MODULE_PREFIX + "." + argument
        return argument
