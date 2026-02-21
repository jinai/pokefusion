import logging
from pathlib import Path

from peewee import SqliteDatabase
from peewee_migrate import Router

from pokefusion.configmanager import ConfigManager
from pokefusion.db import models
from pokefusion.db.models import BaseModel
from pokefusion.environment import Environment

logger = logging.getLogger(__name__)


class MigrationError(Exception):
    pass


class ForceRequiredError(MigrationError):
    def __init__(self, name: str):
        self.name = name


def _resolve_auto_module() -> str:
    return models.__name__


def _resolve_migrations_dir() -> str:
    base_dir = Path(__file__).resolve().parent
    migrations_dir = base_dir / "migrations"
    return str(migrations_dir)


class MigrationService:
    def __init__(self, env: Environment):
        self._dbconf = ConfigManager.get_bot_config(env).dbconf
        self._database = SqliteDatabase(self._dbconf.path, pragmas=self._dbconf.pragmas)
        self._auto_module = _resolve_auto_module()
        self._migrations_dir = _resolve_migrations_dir()
        self._router = Router(self._database, migrate_dir=self._migrations_dir, ignore=BaseModel._meta.name,
                              logger=logger)

    def create(self, name: str) -> str | None:
        try:
            return self._router.create(name, auto=self._auto_module)
        except Exception as e:
            raise MigrationError(str(e)) from e

    def apply(self, name: str | None = None) -> list[str]:
        try:
            return self._router.run(name)
        except Exception as e:
            raise MigrationError(str(e)) from e

    def rollback(self, count: int = 1) -> None:
        done = len(self._router.done)
        if count > done:
            raise MigrationError(f"Cannot rollback {count} migration{'s' if count > 1 else ''}, only {done} applied.")

        try:
            for _ in range(count):
                self._router.rollback()
        except Exception as e:
            raise MigrationError(str(e)) from e

    def list(self) -> tuple[list[str], list[str]]:
        return self._router.done, self._router.diff

    def remove(self, name: str, force: bool = False) -> None:
        if name not in self._router.todo:
            raise MigrationError(f"Migration '{name}' does not exist on disk.")

        if name in self._router.done:
            if self._router.done[-1] != name:
                raise MigrationError(f"Cannot remove '{name}' because it is applied and not the latest migration.")

            if not force:
                raise ForceRequiredError(name)

            self.rollback(count=1)

        file_path = Path(self._router.migrate_dir) / f"{name}.py"
        if not file_path.exists():
            raise MigrationError(f"Migration file '{file_path}' is missing from disk.")

        file_path.unlink()
