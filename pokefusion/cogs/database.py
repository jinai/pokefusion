from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, TYPE_CHECKING

from discord import Guild, Member
from discord.ext import commands

from pokefusion.models import models
from pokefusion.models.models import Server, Settings, User

if TYPE_CHECKING:
    from pokefusion.bot import PokeFusion

logger = logging.getLogger(__name__)


class Database(commands.Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: PokeFusion):
        self.bot = bot

    def cog_load(self) -> None:
        models.database.init(self.bot.config.database.path, pragmas=self.bot.config.database.pragmas)
        logger.info(f"Opened connection to {models.database.database}")
        global_seed = Settings.get_or_create(id=1)[0].global_seed
        logger.info(f"Global seed: {global_seed}")

    def cog_unload(self) -> None:
        models.database.close()
        logger.info(f"Closed connection to {models.database.database}")

    @staticmethod
    def get_settings() -> Settings:
        return Settings.get(Settings.id == 1)

    @staticmethod
    def update_settings(params: Dict[str, Any]) -> int:
        q = (Settings
             .update(**params)
             .where(Settings.id == 1))
        return q.execute()

    @staticmethod
    def add_server(guild: Guild, prefix: str) -> int:
        now = datetime.now()
        q = (Server
             .insert(discord_id=guild.id, name=guild.name, prefix=prefix, joined_at=now)
             .on_conflict(conflict_target=[Server.discord_id],
                          preserve=[Server.name],  # Update the name just in case
                          update={Server.active: True}))  # Mark server as active again
        return q.execute()

    @staticmethod
    def remove_server(guild: Guild) -> int:
        now = datetime.now()
        q = (Server
             .update({Server.active: False, Server.updated_at: now})  # Mark server as inactive and set leave date
             .where(Server.discord_id == guild.id))
        return q.execute()

    @staticmethod
    def get_server(guild: Guild) -> Server:
        return Server.get(Server.discord_id == guild.id)

    @staticmethod
    def update_server(guild: Guild, params: Dict[str, Any]) -> int:
        q = (Server
             .update(**params)
             .where(Server.discord_id == guild.id))
        return q.execute()

    @staticmethod
    def get_or_create_user(user: Member) -> User:
        return User.get_or_create(discord_id=user.id, defaults={"name": str(user)})[0]

    @staticmethod
    def update_user(user: Member, params: Dict[str, Any]) -> int:
        q = (User
             .update(**params)
             .where(User.discord_id == user.id))
        return q.execute()

    @staticmethod
    def update_freererolls(user: Member = None, amount: int = 1) -> int:
        if user is None:
            query = User.update(free_rerolls=User.free_rerolls + amount)
        else:
            query = User.update(free_rerolls=User.free_rerolls + amount).where(User.discord_id == user.id)
        return query.execute()


async def setup(bot: PokeFusion) -> None:
    await bot.add_cog(Database(bot))
