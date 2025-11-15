import asyncio
import logging
from datetime import date, datetime

from discord import Color, User
from discord.ext import commands
from discord.ext.commands import CheckFailure, CommandError, NoPrivateMessage

from pokefusion.bot import PokeFusion
from pokefusion.context import Context
from .cogutils import birthday_embed
from ..configmanager import ConfigManager

logger = logging.getLogger(__name__)


class Birthday(commands.Cog):
    def __init__(self, bot: PokeFusion):
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

    def is_birthday(self, user: User) -> bool:
        key = str(user.id)
        if key not in self.birthdays:
            return False

        bday = self.birthdays[key]
        today = date.today()
        day, month = bday.split("/")
        bday = date(today.year, int(month), int(day))

        return bday == today

    @commands.command(aliases=["bday"])
    async def kdo2(self, ctx: Context, delta: int = 1):
        target = ctx.author
        user_db = self.bot.db.get_or_create_user(target)

        seed = user_db.seed + delta
        bday_rerolls = user_db.bday_rerolls + 1
        bday_delta = user_db.bday_delta + delta
        params = {"seed": seed, "bday_rerolls": bday_rerolls, "bday_delta": bday_delta, "updated_at": datetime.now()}
        self.bot.db.update_user(target, params=params)
        # noinspection PyTypeChecker
        await ctx.invoke(self.bot.get_command("totem"))

    async def bday_event(self, ctx: Context) -> None:
        if ctx.guild is not None and self.is_birthday(ctx.author):
            if not self.bot.db.get_or_create_user(ctx.author).bday_prompt:
                embed, files = birthday_embed(ctx, color=Color.from_str("#FC47AB"))
                prompt = await ctx.send(embed=embed, files=files)
                thumbnail_url = prompt.embeds[0].thumbnail.url
                self.bot.db.update_user(ctx.author, {"bday_prompt": True})
                for i in range(8):
                    await asyncio.sleep(0.5)
                    colors = [Color.yellow(), Color.from_str("#4DE30F"), Color.from_str("#62D4F3"),
                              Color.from_str("#FC47AB")]
                    embed, _ = birthday_embed(ctx, color=colors[i % len(colors)], upload_attachment=False)
                    embed.set_thumbnail(url=thumbnail_url)
                    await prompt.edit(embed=embed, attachments=())


async def setup(bot: PokeFusion) -> None:
    await bot.add_cog(Birthday(bot))
