import datetime
import logging

from peewee import BooleanField, CharField, DateTimeField, IntegerField, Model, SqliteDatabase

from pokefusion.configmanager import DatabaseConfig
from pokefusion.fusionapi import Language

logger = logging.getLogger(__name__)
database = SqliteDatabase(None)


def init_db(config: DatabaseConfig, drop_tables: bool = False):
    global database

    database.init(config.path, pragmas=config.pragmas)
    with database:
        if drop_tables:
            database.drop_tables(MODELS)
        database.create_tables(MODELS)


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
    updated_at = DateTimeField(default=datetime.datetime.now)
    maintenance_mode = BooleanField(default=False)


class Server(BaseModel):
    discord_id = IntegerField(unique=True)
    name = CharField()
    prefix = CharField(max_length=2)
    lang = EnumField(choices=Language, default=Language.DEFAULT, max_length=2)
    joined_at = DateTimeField(default=datetime.datetime.now)
    updated_at = DateTimeField(default=datetime.datetime.now)
    active = BooleanField(default=True)


class User(BaseModel):
    discord_id = IntegerField(unique=True)
    name = CharField()
    updated_at = DateTimeField(default=datetime.datetime.now)
    xmas_prompt = BooleanField(default=False)
    bday_prompt = BooleanField(default=False)
    free_rerolls = IntegerField(default=3)


class Blacklist(BaseModel):
    discord_id = IntegerField(unique=True)
    reason = CharField(null=True)


class Totem(BaseModel):
    discord_id = IntegerField(unique=True)
    head = IntegerField(default=0)
    body = IntegerField(default=0)
    updated_at = DateTimeField(default=datetime.datetime.now)


MODELS = [Settings, Server, User, Blacklist, Totem]
