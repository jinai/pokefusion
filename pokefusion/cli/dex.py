import logging

import typer

from pokefusion.cli.context import Context
from pokefusion.scripts.generate_infinitedex import generate_infinitedex
from pokefusion.scripts.generate_pokedex import generate_pokedex

logger = logging.getLogger(__name__)
dex_app = typer.Typer(no_args_is_help=True)


@dex_app.command()
def build() -> None:
    Context()
    logger.info(f"Building dex files")
    generate_pokedex()
    generate_infinitedex()
