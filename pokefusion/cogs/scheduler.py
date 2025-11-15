import logging
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from discord.ext import commands, tasks

from pokefusion.assetmanager import AssetManager
from pokefusion.bot import PokeFusion
from pokefusion.cogs.cogutils import AttachmentType, EmbedAttachment, WeekDay, embed_factory
from pokefusion.environment import Environment

logger = logging.getLogger(__name__)

tz = ZoneInfo("Europe/Brussels")
PULL_REMINDER_MINUTE = 38  # minute on the clock (e.g. 10:38)
PULL_REMINDER_TIMES = [time(hour=h % 24, minute=PULL_REMINDER_MINUTE, second=1, tzinfo=tz) for h in range(9, 27, 3)]

RERALL_DAY = WeekDay.THURSDAY
RERALL_TIME = time(hour=0, minute=0, second=5, tzinfo=tz)
RERALL_CHANNELS = [
    695415114203136031,  # BTA
    367074976827965450,  # Radio Eco
    357961752513871874,  # Weeaboo Lando
    1374426505387704370,  # Jinai
]


class Scheduler(commands.Cog):
    def __init__(self, bot: PokeFusion) -> None:
        self.bot = bot

    def cog_load(self) -> None:
        logger.info("Scheduling initial tasks")
        self.rerall_task.start()
        if self.bot.config.env is Environment.DEV:
            self.pull_reminder.start()

    def cog_unload(self) -> None:
        logger.info("Unscheduling initial tasks")
        self.rerall_task.cancel()
        self.pull_reminder.cancel()

    @tasks.loop(time=PULL_REMINDER_TIMES)
    async def pull_reminder(self) -> None:
        message = "NEXT RESET IN 5 MINUTES ⚠️"
        owner = await self.bot.get_owner()
        await owner.send(message)

    @tasks.loop(time=RERALL_TIME)
    async def rerall_task(self) -> None:
        if WeekDay(date.today().isoweekday()) is RERALL_DAY:
            new_seed = self.bot.db.get_settings().global_seed + 1
            self.bot.db.update_settings(params={"global_seed": new_seed, "updated_at": datetime.now()})
            avatar = EmbedAttachment(AssetManager.get_avatar_path(self.bot.config.env), "avatar.png",
                                     AttachmentType.THUMBNAIL)
            for channel_id in RERALL_CHANNELS:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    embed, files = embed_factory(title="Rerall", description="All Totems have been reset!",
                                                 attachments=(avatar,), color=self.bot.main_color)
                    await channel.send(embed=embed, files=files)
            logger.info(f"New global seed: {new_seed}")


async def setup(bot: PokeFusion) -> None:
    await bot.add_cog(Scheduler(bot))
