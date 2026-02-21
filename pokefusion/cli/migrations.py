import logging
from functools import wraps
from typing import Annotated

import typer

from pokefusion.cli import env_option
from pokefusion.cli.context import Context
from pokefusion.db.migrations import ForceRequiredError, MigrationError
from pokefusion.environment import Environment

logger = logging.getLogger(__name__)
migrations_app = typer.Typer(no_args_is_help=True)


def count_callback(value: int) -> int:
    if value <= 0:
        raise typer.BadParameter("Must be a positive integer.")
    return value


def handle_migration_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ForceRequiredError as e:
            logger.error(f"Migration '{e.name}' is applied, use --force to rollback and remove.")
            raise typer.Abort()
        except MigrationError as e:
            logger.error(e)
            raise typer.Abort()

    return wrapper


@migrations_app.command(name="new")
@handle_migration_errors
def create_migration(name: str, env: Environment = env_option) -> None:
    ctx = Context(env)
    ctx.migration_service.create(name)


@migrations_app.command(name="apply")
@handle_migration_errors
def apply_migrations(name: Annotated[str, typer.Option()] = None, env: Environment = env_option) -> None:
    ctx = Context(env, require_confirmation=True, action="Apply pending migrations")
    ctx.migration_service.apply(name)


@migrations_app.command(name="rollback")
@handle_migration_errors
def rollback_migration(count: Annotated[int, typer.Argument(callback=count_callback)] = 1,
                       env: Environment = env_option) -> None:
    ctx = Context(env, require_confirmation=True, action=f"Rollback {count} migration{'s' if count > 1 else ''}")
    ctx.migration_service.rollback(count)


@migrations_app.command(name="list")
def list_migrations(env: Environment = env_option) -> None:
    ctx = Context(env)
    done, diff = ctx.migration_service.list()

    logger.info("List of migrations:")
    for migration in done:
        logger.info(f"- [x] {migration}")

    for migration in diff:
        logger.info(f"- [ ] {migration}")


@migrations_app.command(name="remove")
@handle_migration_errors
def remove_migration(name: str,
                     force: Annotated[
                         bool, typer.Option("--force", "-f", help="Rollback and remove even if applied.")] = False,
                     env: Environment = env_option) -> None:
    ctx = Context(env, require_confirmation=True, action=f"Remove '{name}'")
    ctx.migration_service.remove(name, force)
    logger.info(f"Removed migration '{name}' from disk")
