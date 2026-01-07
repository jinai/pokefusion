import logging
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from discord.ext import commands, tasks

from pokefusion.environment import Environment
from pokefusion.assetmanager import AssetManager
from pokefusion.bot import PokeFusion
from .cogutils import AttachmentType, EmbedAttachment, WeekDay, embed_factory

logger = logging.getLogger(__name__)

TZ = ZoneInfo("CET")
RERALL_DAY = WeekDay.THURSDAY
RERALL_TIME = time(hour=0, minute=5, second=0, tzinfo=TZ)
NOTIF_CHANNELS = [
    695415114203136031,  # BTA
    367074976827965450,  # Radio Eco
    357961752513871874,  # Weeaboo Lando
    1374426505387704370,  # Jinai
    1398068543253123326,  # Serong
]


class Scheduler(commands.Cog):
    def __init__(self, bot: PokeFusion) -> None:
        self.bot = bot

    def cog_load(self) -> None:
        logger.info("Scheduling initial tasks")
        if self.bot.config.env is Environment.PROD:
            self.rerall_task.start()

    def cog_unload(self) -> None:
        logger.info("Unscheduling initial tasks")
        self.rerall_task.cancel()

    @tasks.loop(time=RERALL_TIME)
    async def rerall_task(self) -> None:
        if WeekDay(date.today().isoweekday()) is RERALL_DAY:
            new_seed = self.bot.db.get_settings().global_seed + 1
            self.bot.db.update_settings(params={"global_seed": new_seed, "updated_at": datetime.now()})
            logger.info(f"New global seed: {new_seed}")
            avatar = EmbedAttachment(AssetManager.get_avatar_path(self.bot.config.env), "avatar.png",
                                     AttachmentType.THUMBNAIL)
            for channel_id in NOTIF_CHANNELS:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    embed, files = embed_factory(title="Rerall", description="All Totems have been reset!",
                                                 attachments=(avatar,), color=self.bot.main_color)
                    await channel.send(embed=embed, files=files)


async def setup(bot: PokeFusion) -> None:
    await bot.add_cog(Scheduler(bot))
