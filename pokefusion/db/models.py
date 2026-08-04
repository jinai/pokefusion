from datetime import datetime
from typing import Iterable

from peewee import BooleanField, CharField, DateTimeField, EXCLUDED, IntegerField, Model

from pokefusion.db.database import database
from pokefusion.enums import Language


class EnumField(CharField):
    def __init__(self, choices, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.choices = choices

    def db_value(self, value):
        return value.value

    def python_value(self, value):
        value_type = type(list(self.choices)[0].value)
        return self.choices(value_type(value))


class BaseModel(Model):
    class Meta:
        database = database
        legacy_table_names = False


class Settings(BaseModel):
    maintenance = BooleanField(default=False)
    updated_at = DateTimeField(default=datetime.now)
    SETTINGS_ID = 1

    class Meta:
        table_name = "settings"

    @classmethod
    def is_maintenance(cls) -> bool:
        return cls.get_or_create(id=cls.SETTINGS_ID)[0].maintenance

    @classmethod
    def set_maintenance(cls, new_state: bool) -> int:
        query = (
            cls.update(
                maintenance=new_state,
                updated_at=datetime.now()
            )
            .where(cls.id == cls.SETTINGS_ID)
        )

        return query.execute()


class Server(BaseModel):
    discord_id = IntegerField(unique=True)
    name = CharField()
    prefix = CharField(max_length=2)
    lang = EnumField(choices=Language, default=Language.DEFAULT, max_length=2)
    joined_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)
    active = BooleanField(default=True)

    class Meta:
        table_name = "servers"

    @classmethod
    def upsert(cls, discord_id: int, name: str, prefix: str) -> int:
        now = datetime.now()
        incoming_name = EXCLUDED.name

        # Only update if the server was inactive or if the name changed
        needs_update = (~cls.active) | (cls.name != EXCLUDED.name)

        query = (
            cls.insert(
                discord_id=discord_id,
                name=name, prefix=prefix,
                joined_at=now,
                updated_at=now,
                active=True
            )
            .on_conflict(
                conflict_target=[cls.discord_id],
                update={
                    cls.active: True,
                    cls.name: incoming_name,
                    cls.updated_at: now
                },
                where=needs_update
            )
            .as_rowcount()
        )

        return query.execute()

    @classmethod
    def deactivate(cls, discord_id: int) -> int:
        query = (
            cls.update(
                active=False,
                updated_at=datetime.now()
            )
            .where(
                (cls.discord_id == discord_id)
                & cls.active
            )
        )

        return query.execute()

    @classmethod
    def deactivate_missing(cls, current_discord_ids: tuple[int, ...]) -> int:
        query = cls.update(
            active=False,
            updated_at=datetime.now()
        )

        if current_discord_ids:
            # noinspection argument-list
            condition = cls.active & cls.discord_id.not_in(current_discord_ids)
        else:
            condition = cls.active

        return query.where(condition).execute()

    @classmethod
    def sync_all(
            cls,
            available_servers: Iterable[tuple[int, str]],
            current_discord_ids: tuple[int, ...],
            default_prefix: str
    ) -> tuple[int, int]:
        db = cls._meta.database

        with db.atomic():
            upserted = sum(
                cls.upsert(discord_id, name, default_prefix)
                for discord_id, name in available_servers
            )

            deactivated = cls.deactivate_missing(current_discord_ids)

        return upserted, deactivated


class User(BaseModel):
    discord_id = IntegerField(unique=True)
    name = CharField()
    updated_at = DateTimeField(default=datetime.now)
    xmas_prompt = BooleanField(default=False)
    bday_prompt = BooleanField(default=False)
    free_rerolls = IntegerField(default=3)

    class Meta:
        table_name = "users"

    @classmethod
    def add_free_rerolls(cls, discord_id: int, amount: int) -> int:
        query = (
            cls.update(
                free_rerolls=cls.free_rerolls + amount,
                updated_at=datetime.now()
            )
            .where(cls.discord_id == discord_id)
        )

        return query.execute()

    @classmethod
    def add_free_rerolls_to_all(cls, amount: int) -> int:
        query = cls.update(
            free_rerolls=cls.free_rerolls + amount,
            updated_at=datetime.now()
        )

        return query.execute()


class Blacklist(BaseModel):
    discord_id = IntegerField(unique=True)
    reason = CharField(null=True)

    class Meta:
        table_name = "blacklist"


class Totem(BaseModel):
    discord_id = IntegerField(unique=True)
    head = IntegerField(default=0)
    body = IntegerField(default=0)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = "totems"

    @classmethod
    def get_all_ids(cls) -> Iterable[int]:
        return cls.select(cls.discord_id).tuples()
