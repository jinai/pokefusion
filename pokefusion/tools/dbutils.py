import logging
import os

from peewee import SqliteDatabase
from peewee_migrate import Router

from pokefusion.configmanager import DatabaseConfig
from pokefusion.models.models import BaseModel

# from playhouse.kv import KeyValue

logger = logging.getLogger(__name__)


def create_migration(config: DatabaseConfig, migration_name) -> None:
    migrate_dir = os.path.join("pokefusion", "migrations")
    router = Router(SqliteDatabase(config.path, pragmas=config.pragmas), migrate_dir=migrate_dir,
                    ignore=[BaseModel._meta.name], logger=logger)

    # Create migration
    router.create(migration_name, auto="pokefusion.models")

    # Run all unapplied migrations
    router.run()


def run_migrations(config: DatabaseConfig) -> None:
    migrate_dir = os.path.join("pokefusion", "migrations")
    router = Router(SqliteDatabase(config.path, pragmas=config.pragmas), migrate_dir=migrate_dir,
                    ignore=[BaseModel._meta.name], logger=logger)
    router.run()


def rollback_migration(config: DatabaseConfig) -> None:
    migrate_dir = os.path.join("pokefusion", "migrations")
    router = Router(SqliteDatabase(config.path, pragmas=config.pragmas), migrate_dir=migrate_dir,
                    ignore=[BaseModel._meta.name], logger=logger)

    router.rollback()

# def keyval_store(config: DatabaseConfig) -> None:
#     db = SqliteDatabase(config.path, pragmas=config.pragmas)
#     kv = KeyValue(database=db, ordered=True, table_name="keyval", value_field=TextField())
#     kv["channels"] = json.dumps([1, 2, 3, 4])
#     kv["reminder_time"] = json.dumps("10:38")
#     channels = json.loads(kv["channels"])
#     print(channels)
#     print(type(channels))
