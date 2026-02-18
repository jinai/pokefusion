from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, TYPE_CHECKING

from discord import Guild, Member
from discord.ext import commands

from pokefusion.db.database import database
from pokefusion.db.models import Server, Settings, Totem, User
from pokefusion.fusionapi import FusionResult

if TYPE_CHECKING:
    from pokefusion.bot import PokeFusion

logger = logging.getLogger(__name__)


class Database(commands.Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: PokeFusion):
        self.bot = bot

    def cog_load(self) -> None:
        database.init(self.bot.config.dbconf.path, pragmas=self.bot.config.dbconf.pragmas)
        logger.info(f"Opened connection to {database.database}")

    def cog_unload(self) -> None:
        database.close()
        logger.info(f"Closed connection to {database.database}")

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
                          update={Server.active: True,
                                  Server.name: guild.name}))  # Mark server as active again and update name just in case
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

    def get_or_create_totem(self, user: Member) -> FusionResult:
        totem = Totem.get_or_create(discord_id=user.id)[0]
        if totem.head == 0:
            temp = self.bot.fusion_client.totem(None)
            totem.head = temp.head.dex_id
            totem.body = temp.body.dex_id
            totem.save()

        result = self.bot.fusion_client.fusion(str(totem.head), str(totem.body))
        return result

    def reroll_totem(self, user: Member) -> FusionResult:
        totem = self.bot.fusion_client.totem(None)
        Totem.replace(discord_id=user.id, head=totem.head.dex_id, body=totem.body.dex_id,
                      updated_at=Totem.updated_at.default()).execute()
        return totem

    def reroll_all_totems(self):
        with database.atomic():
            for (id_,) in Totem.select(Totem.id).tuples():
                totem = self.bot.fusion_client.totem(None)
                Totem.update(head=totem.head.dex_id, body=totem.body.dex_id,
                             updated_at=Totem.updated_at.default()).where(Totem.id == id_).execute()


async def setup(bot: PokeFusion) -> None:
    await bot.add_cog(Database(bot))
