import logging

import typer

from pokefusion.cli.context import Context
from pokefusion.db import database, schema

logger = logging.getLogger(__name__)
db_app = typer.Typer(no_args_is_help=True)


@db_app.command("init")
def init_db() -> None:
    ctx = Context(require_confirmation=True, action="Initialize database (drop tables)")
    logger.info(f"Initializing database")
    database.init_db(ctx.config.dbconf)
    schema.create_schema(drop_tables=True)
