from peewee import SqliteDatabase

from pokefusion.configmanager import DatabaseConfig

database = SqliteDatabase(None)


def connect_database(config: DatabaseConfig):
    database.init(config.path, pragmas=config.pragmas)
    database.connect()
