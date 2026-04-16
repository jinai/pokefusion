from datetime import datetime
from typing import Iterable

from peewee import BooleanField, CharField, DateTimeField, IntegerField, Model

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
        return cls.update(maintenance=new_state, updated_at=datetime.now).where(cls.id == cls.SETTINGS_ID).execute()


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
    def add(cls, discord_id: int, name: str, prefix: str) -> int:
        now = datetime.now()
        q = (cls
             .insert(discord_id=discord_id, name=name, prefix=prefix, joined_at=now)
             .on_conflict(conflict_target=[cls.discord_id],
                          update={cls.active: True,
                                  cls.name: name,
                                  cls.updated_at: datetime.now()}))
        return q.execute()

    @classmethod
    def remove(cls, discord_id: int) -> int:
        return cls.update(active=False, updated_at=datetime.now()).where(cls.discord_id == discord_id).execute()


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
        q = (cls
             .update(free_rerolls=cls.free_rerolls + amount, updated_at=datetime.now())
             .where(cls.discord_id == discord_id))
        return q.execute()

    @classmethod
    def add_free_rerolls_to_all(cls, amount: int) -> int:
        return cls.update(free_rerolls=cls.free_rerolls + amount, updated_at=datetime.now()).execute()


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
