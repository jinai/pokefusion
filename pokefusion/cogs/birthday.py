import asyncio
import logging
from datetime import date

from discord import Color, Member, User
from discord.ext import commands
from discord.ext.commands import CheckFailure, CommandError, NoPrivateMessage

from pokefusion.bot.context import Context
from pokefusion.bot.pokefusion import PokeFusion
from pokefusion.configmanager import ConfigManager
from pokefusion.db.models import User as DatabaseUser
from .cogutils import birthday_embed

logger = logging.getLogger(__name__)


class Birthday(commands.Cog):
    def __init__(self, bot: PokeFusion) -> None:
        self.bot = bot
        self.bot.after_invoke(self.bday_event)
        self.birthdays = {}

    def cog_load(self) -> None:
        self.birthdays = ConfigManager.read_json("birthdays.json")
        logger.info(f"Loaded {len(self.birthdays)} birthdays")

    async def cog_check(self, ctx: Context) -> bool:
        return await commands.guild_only().predicate(ctx) and self.is_birthday(ctx.author)

    async def cog_command_error(self, ctx: Context, error: CommandError) -> None:
        if isinstance(error, NoPrivateMessage):
            await ctx.send(str(error))
        elif isinstance(error, CheckFailure):
            await ctx.send("It's not your birthday!")

    def is_birthday(self, user: User | Member) -> bool:
        key = str(user.id)
        if key not in self.birthdays:
            return False

        bday = self.birthdays[key]
        today = date.today()
        day, month = bday.split("/")
        bday = date(today.year, int(month), int(day))

        return bday == today

    @commands.command(aliases=["bday"])
    async def kdo2(self, ctx: Context):
        self.bot.totem_service.reroll_totem(ctx.author.id)
        # noinspection PyTypeChecker
        await ctx.invoke(self.bot.get_command("totem"))

    async def bday_event(self, ctx: Context) -> None:
        if ctx.guild is None or not self.is_birthday(ctx.author):
            return

        user_db, _ = DatabaseUser.get_or_create(
            discord_id=ctx.author.id,
            defaults={"name": ctx.author.name}
        )

        if user_db.bday_prompt:
            return

        colors = (
            Color.yellow(),
            Color.from_str("#4DE30F"),
            Color.from_str("#62D4F3"),
            Color.from_str("#FC47AB"),
        )

        embed, files = birthday_embed(ctx, color=colors[-1])

        message = await ctx.send(embed=embed, files=files)

        user_db.bday_prompt = True
        user_db.save(only=[DatabaseUser.bday_prompt])

        for index in range(8):
            await asyncio.sleep(0.5)

            embed.colour = colors[index % len(colors)]
            message = await message.edit(embed=embed)


async def setup(bot: PokeFusion) -> None:
    await bot.add_cog(Birthday(bot))
