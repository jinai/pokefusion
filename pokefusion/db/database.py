from pathlib import Path

from peewee import Database, SqliteDatabase
from playhouse.migrations import Runner

from pokefusion.configmanager import DatabaseConfig

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
MIGRATIONS_TABLE = "schema_migrations"

database = SqliteDatabase(None)


def connect_database(config: DatabaseConfig) -> SqliteDatabase:
    database.init(config.path, pragmas=config.pragmas)
    database.connect()
    return database


def get_pending_migrations(database: Database) -> list[str]:
    runner = Runner(database, directory=str(MIGRATIONS_DIR), table_name=MIGRATIONS_TABLE)

    return [
        migration.name
        for migration in runner.status()
        if migration.path is not None and migration.applied is None
    ]
