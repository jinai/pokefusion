import logging
from pathlib import Path
from typing import Annotated

import typer

from pokefusion.cli.context import Context
from pokefusion.scripts.assets.autogen import clean_asset_cache, stage_autogen_sprites
from pokefusion.scripts.assets.pack import InvalidPackError, resolve_pack, stage_custom_sprites, stage_egg_sprites
from pokefusion.scripts.assets.staging import generate_asset_metadata
from pokefusion.scripts.assets.update import apply_staged_assets, update_assets
from pokefusion.scripts.assets.workspace import clean_staging_assets

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
CustomWorkers = Annotated[int | None, typer.Option(min=1, help="Number of custom sprite workers.")]


@assets_app.callback()
def assets_callback() -> None:
    Context()


@assets_app.command()
def update(pack: PackPath, custom_workers: CustomWorkers = None) -> None:
    update_assets(pack, custom_workers=custom_workers)


@stage_app.command("autogen")
def stage_autogen() -> None:
    stage_autogen_sprites()


@stage_app.command("custom")
def stage_custom(pack: PackPath, workers: CustomWorkers = None) -> None:
    stage_custom_sprites(pack, workers=workers)


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
def clean_output() -> None:
    clean_staging_assets()


@clean_app.command("cache")
def clean_cache() -> None:
    clean_asset_cache()
