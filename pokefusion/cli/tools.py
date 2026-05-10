import logging
import os
import time

import typer

from pokefusion.cli.context import Context
from pokefusion.enums import Environment
from pokefusion.scripts.clean_assets import clean_assets_folder, clean_output_folder, restore_git_files
from pokefusion.scripts.import_assets import import_autogen_sprites, import_custom_sprites, import_egg_sprites, \
    move_to_assets, save_diff

logger = logging.getLogger(__name__)
tools_app = typer.Typer(no_args_is_help=True)
import_app = typer.Typer(no_args_is_help=True)
cleanup_app = typer.Typer(no_args_is_help=True)
tools_app.add_typer(import_app, name="import")
tools_app.add_typer(cleanup_app, name="cleanup")


@tools_app.callback()
def tools_callback() -> None:
    Context(Environment.PROD)


@import_app.command("all")
def import_all(pack_name: str) -> None:
    logger.info("Importing all assets")
    start_time = time.perf_counter()
    _cleanup_output()
    _import_autogen()
    _import_custom(pack_name)
    _import_eggs(pack_name)
    _save_diff()
    _cleanup_assets()
    _import_to_assets()
    logger.info("Restoring git files")
    restore_git_files()
    elapsed_time = time.perf_counter() - start_time
    logger.info(f"Total runtime is {elapsed_time:.2f} seconds")
    logger.info("Don't forget to update fusionapi.PREVIOUS_MAX_ID if necessary")


@import_app.command("autogen")
def import_autogen() -> None:
    _import_autogen()


@import_app.command("custom")
def import_custom(pack_name: str) -> None:
    _import_custom(pack_name)


@import_app.command("eggs")
def import_eggs(pack_name: str) -> None:
    _import_eggs(pack_name)


@import_app.command("to_assets")
def import_to_assets() -> None:
    _import_to_assets()


@tools_app.command("save_diff")
def save_diff_cmd() -> None:
    _save_diff()


@cleanup_app.command("output")
def cleanup_output_cmd() -> None:
    _cleanup_output()


@cleanup_app.command("assets")
def cleanup_assets_cmd() -> None:
    _cleanup_assets()


def _import_autogen() -> None:
    logger.info("Importing autogen sprites from GitHub")
    import_autogen_sprites()


def _import_custom(pack_name: str) -> None:
    logger.info(f"Importing custom sprites from '{pack_name}'")
    import_custom_sprites(pack_name)


def _import_eggs(pack_name: str) -> None:
    logger.info(os.path.abspath("scripts"))
    logger.info(f"Importing eggs from '{pack_name}'")
    import_egg_sprites(pack_name)


def _import_to_assets() -> None:
    logger.info("Moving files to assets folder")
    move_to_assets()


def _save_diff() -> None:
    logger.info("Saving diff")
    save_diff()


def _cleanup_output() -> None:
    logger.info("Cleaning up output folder")
    clean_output_folder()


def _cleanup_assets() -> None:
    logger.info("Cleaning up assets folder")
    clean_assets_folder()
