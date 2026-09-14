from discord.ext.commands import BadArgument, Converter

from pokefusion.bot.context import Context
from pokefusion.enums import Language
from pokefusion.utils import special_join


class PrefixConverter(Converter):
    _MIN_SIZE = 1
    _MAX_SIZE = 3

    async def convert(self, ctx: Context, argument: str) -> str:  # noqa: ARG002
        if not self._MIN_SIZE <= len(argument) <= self._MAX_SIZE:
            raise BadArgument(f"The prefix must be between {self._MIN_SIZE} and {self._MAX_SIZE} characters long.")

        return argument


class LanguageConverter(Converter):
    _AVAILABLE_LANGUAGES = special_join([f"`{lang}`" for lang in Language], ", ", " or ")

    async def convert(self, ctx: Context, argument: str) -> Language:  # noqa: ARG002
        if argument not in Language:
            raise BadArgument(f"The language must be one of {self._AVAILABLE_LANGUAGES}.")

        return Language(argument)


class ModuleConverter(Converter):
    async def convert(self, ctx: Context, argument: str) -> str:
        if argument.startswith(f"{ctx.bot.COGS_PACKAGE}."):
            return argument

        return f"{ctx.bot.COGS_PACKAGE}.{argument}"
