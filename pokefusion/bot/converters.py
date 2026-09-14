from discord.ext.commands import BadArgument, Converter

from pokefusion.bot.context import Context
from pokefusion.enums import Language
from pokefusion.utils import special_join


class PrefixConverter(Converter):
    async def convert(self, ctx: Context, argument: str) -> str:  # noqa: ARG002
        size = len(argument)
        if size < 1 or size > 2:
            raise BadArgument("The prefix must be 1 or 2 characters long.")
        return argument


class LanguageConverter(Converter):
    LANGUAGES = special_join([f"`{lang}`" for lang in Language], ", ", " or ")

    async def convert(self, ctx: Context, argument: str) -> Language:  # noqa: ARG002
        if argument not in Language:
            raise BadArgument(f"The language must be one of {LanguageConverter.LANGUAGES}")
        return Language(argument)


class ModuleConverter(Converter):
    async def convert(self, ctx: Context, argument: str) -> str:
        if argument.startswith(f"{ctx.bot.COGS_PACKAGE}."):
            return argument

        return f"{ctx.bot.COGS_PACKAGE}.{argument}"
