import logging

import typer

from pokefusion.cli import env_option
from pokefusion.cli.context import Context
from pokefusion.db import database, schema
from pokefusion.environment import Environment

logger = logging.getLogger(__name__)
db_app = typer.Typer(no_args_is_help=True)


@db_app.command("init")
def init_db(env: Environment = env_option) -> None:
    ctx = Context(env, require_confirmation=True, action="Initialize database (drop tables)")
    logger.info(f"Initializing database")
    database.init_db(ctx.config.dbconf)
    schema.create_schema(drop_tables=True)
