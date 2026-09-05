import logging
import time
from pathlib import Path
from typing import Annotated

import typer

from pokefusion.cli.context import Context
from pokefusion.scripts.clean_assets import clean_assets_folder, clean_output_folder
from pokefusion.scripts.git import restore_deleted_files
from pokefusion.scripts.import_assets import InvalidPackError, import_autogen_sprites, import_custom_sprites, \
    import_egg_sprites, move_to_assets, resolve_pack, save_diff as _save_diff

logger = logging.getLogger(__name__)

tools_app = typer.Typer(no_args_is_help=True)
import_app = typer.Typer(no_args_is_help=True)
cleanup_app = typer.Typer(no_args_is_help=True)

tools_app.add_typer(import_app, name="import")
tools_app.add_typer(cleanup_app, name="cleanup")


def validate_pack(pack: Path) -> Path:
    try:
        return resolve_pack(pack)
    except InvalidPackError as error:
        raise typer.BadParameter(str(error)) from error


PackPath = Annotated[Path, typer.Argument(callback=validate_pack)]


@tools_app.callback()
def tools_callback() -> None:
    Context()


@tools_app.command("save_diff")
def save_diff() -> None:
    logger.info("Saving diff")
    _save_diff()


@import_app.command("all")
def import_all(pack: PackPath) -> None:
    logger.info("Importing all assets")
    start_time = time.perf_counter()

    cleanup_output()
    import_autogen()
    import_custom(pack)
    import_eggs(pack)
    save_diff()
    cleanup_assets()
    import_to_assets()

    logger.info("Restoring tracked files deleted during cleanup")
    restore_deleted_files()

    elapsed_time = time.perf_counter() - start_time
    logger.info(f"Total runtime is {elapsed_time:.2f} seconds")
    logger.info("Don't forget to update fusionapi.PREVIOUS_MAX_ID if necessary")


@import_app.command("autogen")
def import_autogen() -> None:
    logger.info("Importing autogen sprites from GitHub")
    import_autogen_sprites()


@import_app.command("custom")
def import_custom(pack: PackPath) -> None:
    logger.info(f"Importing custom sprites from '{pack}'")
    import_custom_sprites(pack)


@import_app.command("eggs")
def import_eggs(pack: PackPath) -> None:
    logger.info(f"Importing eggs from '{pack}'")
    import_egg_sprites(pack)


@import_app.command("to_assets")
def import_to_assets() -> None:
    logger.info("Moving files to assets folder")
    move_to_assets()


@cleanup_app.command("output")
def cleanup_output() -> None:
    logger.info("Cleaning up output folder")
    start_time = time.perf_counter()

    clean_output_folder()

    elapsed_time = time.perf_counter() - start_time
    logger.info(f"Cleaned up output folder in {elapsed_time:.2f} seconds")


@cleanup_app.command("assets")
def cleanup_assets() -> None:
    logger.info("Cleaning up assets folder")
    start_time = time.perf_counter()

    clean_assets_folder()

    elapsed_time = time.perf_counter() - start_time
    logger.info(f"Cleaned up assets folder in {elapsed_time:.2f} seconds")
