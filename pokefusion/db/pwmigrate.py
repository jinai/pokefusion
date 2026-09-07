from peewee import SqliteDatabase

from pokefusion.configmanager import ConfigManager

config = ConfigManager.get_bot_config().database
database = SqliteDatabase(config.path, pragmas=config.pragmas)
