import logging
from pathlib import Path
from typing import Annotated

import typer

from pokefusion.cli.context import Context
from pokefusion.scripts.assets import (
    InvalidPackError,
    apply_staged_assets,
    clean_staging_assets,
    generate_asset_metadata,
    resolve_pack,
    stage_autogen_sprites,
    stage_custom_sprites,
    stage_egg_sprites,
    update_assets,
)

logger = logging.getLogger(__name__)

assets_app = typer.Typer(no_args_is_help=True)
stage_app = typer.Typer(no_args_is_help=True)
clean_app = typer.Typer(no_args_is_help=True)

assets_app.add_typer(stage_app, name="stage")
assets_app.add_typer(clean_app, name="clean")


def validate_pack(pack: Path) -> Path:
    try:
        return resolve_pack(pack)
    except InvalidPackError as error:
        raise typer.BadParameter(str(error)) from error


PackPath = Annotated[Path, typer.Argument(callback=validate_pack)]


@assets_app.callback()
def assets_callback() -> None:
    Context()


@assets_app.command()
def update(pack: PackPath) -> None:
    update_assets(pack)


@stage_app.command("autogen")
def stage_autogen() -> None:
    stage_autogen_sprites()


@stage_app.command("custom")
def stage_custom(pack: PackPath) -> None:
    stage_custom_sprites(pack)


@stage_app.command("eggs")
def stage_eggs(pack: PackPath) -> None:
    stage_egg_sprites(pack)


@assets_app.command()
def metadata() -> None:
    generate_asset_metadata()


@assets_app.command()
def apply() -> None:
    apply_staged_assets()


@clean_app.command("staging")
def cleanup_output() -> None:
    clean_staging_assets()
