import logging
import time

import typer

from pokefusion.cli.context import Context
from pokefusion.environment import Environment
from pokefusion.tools.import_assets import import_autogen_sprites, import_custom_sprites, import_eggs, save_diff

logger = logging.getLogger(__name__)
tools_app = typer.Typer(no_args_is_help=True)
import_app = typer.Typer(no_args_is_help=True)
tools_app.add_typer(import_app, name="import")


@tools_app.callback()
def tools_callback() -> None:
    Context(Environment.PROD)


@import_app.command("all")
def import_all(pack_name: str) -> None:
    logger.info("Importing all assets")
    start_time = time.perf_counter()
    import_autogen_impl()
    import_custom_impl(pack_name)
    import_eggs_impl(pack_name)
    save_diff_impl()
    elapsed_time = time.perf_counter() - start_time
    logger.info(f"Total runtime is {elapsed_time:.2f} seconds")
    logger.info("Don't forget to update fusionapi.PREVIOUS_MAX_ID if necessary")


@import_app.command("autogen")
def import_autogen() -> None:
    import_autogen_impl()


@import_app.command("custom")
def import_custom(pack_name: str) -> None:
    import_custom_impl(pack_name)


@import_app.command("eggs")
def import_eggs_cmd(pack_name: str) -> None:
    import_eggs_impl(pack_name)


@tools_app.command("save_diff")
def save_diff_cmd() -> None:
    save_diff_impl()


def import_autogen_impl() -> None:
    logger.info("Importing autogen sprites from GitHub")
    import_autogen_sprites()


def import_custom_impl(pack_name: str) -> None:
    logger.info(f"Importing custom sprites from '{pack_name}'")
    import_custom_sprites(pack_name)


def import_eggs_impl(pack_name: str) -> None:
    logger.info(f"Importing eggs from '{pack_name}'")
    import_eggs(pack_name)


def save_diff_impl() -> None:
    logger.info("Saving diff")
    save_diff()
