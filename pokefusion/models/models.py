import datetime
import logging

from peewee import BooleanField, CharField, DatabaseProxy, DateTimeField, IntegerField, Model, SqliteDatabase

from pokefusion.configmanager import DatabaseConfig
from pokefusion.fusionapi import Language

logger = logging.getLogger(__name__)
database = DatabaseProxy()


def init_db(config: DatabaseConfig, drop_tables: bool = False):
    open_db(config)
    with database:
        if drop_tables:
            database.drop_tables(MODELS)
        database.create_tables(MODELS)


def open_db(config: DatabaseConfig):
    global database
    runtime_db = SqliteDatabase(config.path, pragmas=config.pragmas)
    database.initialize(runtime_db)
    logger.info(f"Opened connection to {database.database}")


def close_db():
    global database
    database.close()
    logger.info(f"Closed connection to {database.database}")


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
    global_seed = IntegerField(default=0)
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
    seed = IntegerField(default=0)
    updated_at = DateTimeField(default=datetime.datetime.now)
    xmas_prompt = BooleanField(default=False)
    xmas_rerolls = IntegerField(default=0)
    xmas_delta = IntegerField(default=0)
    bday_prompt = BooleanField(default=False)
    bday_rerolls = IntegerField(default=0)
    bday_delta = IntegerField(default=0)
    free_rerolls = IntegerField(default=3)


class Blacklist(BaseModel):
    discord_id = IntegerField(unique=True)
    reason = CharField(null=True)


MODELS = [Settings, Server, User, Blacklist]
