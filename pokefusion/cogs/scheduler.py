import logging
from calendar import Day
from datetime import datetime, time
from zoneinfo import ZoneInfo

from discord.ext import commands, tasks

from pokefusion.bot.pokefusion import PokeFusion
from .cogutils import embed_factory

logger = logging.getLogger(__name__)

TZ = ZoneInfo("CET")
RERALL_DAY = Day.THURSDAY
RERALL_TIME = time(hour=0, minute=0, second=30, tzinfo=TZ)
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
        self.rerall_task.start()

    def cog_unload(self) -> None:
        logger.info("Unscheduling initial tasks")
        self.rerall_task.cancel()

    @tasks.loop(time=RERALL_TIME)
    async def rerall_task(self) -> None:
        logger.info(f"Running task '{self.rerall_task._name}'")

        if Day(datetime.now(TZ).weekday()) is not RERALL_DAY:
            return

        self.bot.totem_service.reroll_all_totems()

        for channel_id in NOTIF_CHANNELS:
            channel = self.bot.get_channel(channel_id)
            if channel:
                embed, files = embed_factory(
                    title="Rerall",
                    description="All Totems have been reset!",
                    color=self.bot.main_color,
                    thumbnail=self.bot.user.display_avatar.url,
                )
                await channel.send(embed=embed, files=files)


async def setup(bot: PokeFusion) -> None:
    await bot.add_cog(Scheduler(bot))
