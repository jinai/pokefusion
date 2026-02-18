from peewee import SqliteDatabase

from pokefusion.configmanager import DatabaseConfig

database = SqliteDatabase(None)


def init_db(config: DatabaseConfig):
    database.init(config.path, pragmas=config.pragmas)
