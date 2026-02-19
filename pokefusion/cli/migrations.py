import logging
from typing import Annotated

import typer
from peewee import SqliteDatabase
from peewee_migrate import Router

from pokefusion.cli import env_option
from pokefusion.cli.context import Context
from pokefusion.db.models import BaseModel
from pokefusion.db.paths import MIGRATIONS_DIR
from pokefusion.environment import Environment

logger = logging.getLogger(__name__)
migrations_app = typer.Typer(no_args_is_help=True)


def count_callback(value: int) -> int:
    if value <= 0:
        raise typer.BadParameter("Must be a positive integer.")
    return value


@migrations_app.command(name="new")
def create_migration(name: str, env: Environment = env_option) -> None:
    ctx = Context(env)
    router = Router(SqliteDatabase(ctx.config.dbconf.path, pragmas=ctx.config.dbconf.pragmas),
                    migrate_dir=MIGRATIONS_DIR, ignore=[BaseModel._meta.name], logger=logger)
    router.create(name, auto="pokefusion.db")


@migrations_app.command(name="run")
def run_migrations(name: Annotated[str, typer.Option()] = None, env: Environment = env_option) -> None:
    ctx = Context(env, require_confirmation=True, action="Run pending migrations")
    router = Router(SqliteDatabase(ctx.config.dbconf.path, pragmas=ctx.config.dbconf.pragmas),
                    migrate_dir=MIGRATIONS_DIR, ignore=[BaseModel._meta.name], logger=logger)
    router.run(name)


@migrations_app.command(name="rollback")
def rollback_migration(count: Annotated[int, typer.Argument(callback=count_callback)] = 1,
                       env: Environment = env_option) -> None:
    ctx = Context(env, require_confirmation=True, action=f"Rollback {count} migration{'s' if count > 1 else ''}")
    router = Router(SqliteDatabase(ctx.config.dbconf.path, pragmas=ctx.config.dbconf.pragmas),
                    migrate_dir=MIGRATIONS_DIR, ignore=[BaseModel._meta.name], logger=logger)

    if len(router.done) < count:
        logger.error(
            f"Unable to rollback {count} migration{'s' if count > 1 else ''} because there are only {len(router.done)}")
        raise typer.Abort()

    for _ in range(count):
        router.rollback()


@migrations_app.command(name="list")
def list_migrations(env: Environment = env_option) -> None:
    ctx = Context(env)
    router = Router(SqliteDatabase(ctx.config.dbconf.path, pragmas=ctx.config.dbconf.pragmas),
                    migrate_dir=MIGRATIONS_DIR, ignore=[BaseModel._meta.name], logger=logger)

    logger.info("List of migrations:")
    for migration in router.done:
        logger.info(f"- [x] {migration}")

    for migration in router.diff:
        logger.info(f"- [ ] {migration}")
