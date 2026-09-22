import logging
import os
import time
from functools import partial
from multiprocessing import Pool
from pathlib import Path

from PIL import Image
from PIL.Image import Resampling
from tqdm import tqdm

from pokefusion.fusionapi import FusionClient
from pokefusion.scripts.assets.paths import (
    AUTOGEN_REPOSITORY_DIR,
    AUTOGEN_SPRITESHEETS_DIR,
    AUTOGEN_SPRITESHEETS_RELATIVE_DIR,
    CACHE_DIR,
    STAGING_AUTOGEN_DIR,
)
from pokefusion.scripts.assets.workspace import prepare_staging_directory
from pokefusion.scripts.git import run_git
from pokefusion.scripts.utils import fast_delete
from pokefusion.types import StrPath

logger = logging.getLogger(__name__)

AUTOGEN_REPOSITORY_URL = "https://github.com/infinitefusion/infinitefusion-e18.git"
AUTOGEN_REPOSITORY_BRANCH = "develop-6.6"

SPRITESHEET_ROWS = 58
SPRITESHEET_COLUMNS = 10
SPRITE_WIDTH = 96
SPRITE_HEIGHT = 96
SPRITE_SCALE = 2


def stage_autogen_sprites() -> None:
    logger.info("Staging autogen sprites from the Infinite Fusion repository")
    stage_start_time = time.perf_counter()

    prepare_staging_directory(STAGING_AUTOGEN_DIR)
    _prepare_autogen_repository()

    sheet_count = sum(1 for _ in AUTOGEN_SPRITESHEETS_DIR.glob("*.png"))

    if sheet_count == 0:
        raise RuntimeError(f"No autogen spritesheets found in '{AUTOGEN_SPRITESHEETS_DIR.resolve()}'")

    if sheet_count > FusionClient.MAX_ID:
        logger.warning(
            "Found more than %d autogen spritesheets! "
            "Check if new autogen sprites were released, and update FusionClient.MAX_ID accordingly",
            FusionClient.MAX_ID,
        )

    logger.info("Splitting %d autogen spritesheets", sheet_count)
    split_start_time = time.perf_counter()

    _split_spritesheets(AUTOGEN_SPRITESHEETS_DIR, STAGING_AUTOGEN_DIR)

    split_elapsed_time = time.perf_counter() - split_start_time
    logger.info("Split %d autogen spritesheets in %.2f seconds", sheet_count, split_elapsed_time)

    sprite_count = sum(len(filenames) for _, _, filenames in os.walk(STAGING_AUTOGEN_DIR))

    stage_elapsed_time = time.perf_counter() - stage_start_time
    logger.info(
        "Staged %d autogen sprites from %d spritesheets in %.2f seconds",
        sprite_count,
        sheet_count,
        stage_elapsed_time,
    )


def clean_asset_cache() -> None:
    if not CACHE_DIR.exists():
        logger.info("Asset cache is already clean")
        return

    logger.info("Cleaning asset cache directory: '%s'", CACHE_DIR.resolve())
    start_time = time.perf_counter()

    fast_delete(CACHE_DIR)

    elapsed_time = time.perf_counter() - start_time
    logger.info("Cleaned asset cache in %.2f seconds", elapsed_time)


def _prepare_autogen_repository() -> None:
    repository_dir = AUTOGEN_REPOSITORY_DIR.resolve()
    git_dir = repository_dir / ".git"

    if repository_dir.exists() and not git_dir.is_dir():
        raise RuntimeError(f"Invalid autogen repository cache: '{repository_dir}'")

    start_time = time.perf_counter()

    if git_dir.is_dir():
        logger.info("Updating cached Infinite Fusion repository")

        commands = [
            ["-C", str(repository_dir), "fetch", "--depth=1", "--no-tags", "origin", AUTOGEN_REPOSITORY_BRANCH],
            ["-C", str(repository_dir), "reset", "--hard", "FETCH_HEAD"],
        ]
        operation = "Updated"
    else:
        logger.info("Cloning Infinite Fusion repository into cache")
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        commands = [
            [
                "clone",
                "-n",
                "--depth=1",
                "--filter=tree:0",
                "--no-tags",
                "-b",
                AUTOGEN_REPOSITORY_BRANCH,
                "--single-branch",
                AUTOGEN_REPOSITORY_URL,
                str(repository_dir),
            ],
            [
                "-C",
                str(repository_dir),
                "sparse-checkout",
                "set",
                "--no-cone",
                f"/{AUTOGEN_SPRITESHEETS_RELATIVE_DIR.as_posix()}",
            ],
            ["-C", str(repository_dir), "checkout"],
        ]
        operation = "Initialized"

    for arguments in commands:
        run_git(arguments)

    if not AUTOGEN_SPRITESHEETS_DIR.is_dir():
        raise RuntimeError(f"Autogen spritesheets directory not found: '{AUTOGEN_SPRITESHEETS_DIR.resolve()}'")

    elapsed_time = time.perf_counter() - start_time
    logger.info("%s Infinite Fusion repository cache in %.2f seconds", operation, elapsed_time)


def _split_spritesheets(input_dir: StrPath, output_dir: StrPath) -> None:
    spritesheet_paths = sorted(Path(input_dir).glob("*.png"))
    worker_count = min(os.process_cpu_count() or 1, len(spritesheet_paths))

    worker_label = "worker" if worker_count == 1 else "workers"
    desc = f"Splitting spritesheets ({worker_count} {worker_label})"
    split = partial(_split_spritesheet, output_dir=output_dir)

    with Pool(worker_count) as pool:
        results = pool.imap_unordered(split, spritesheet_paths)

        for _ in tqdm(results, total=len(spritesheet_paths), desc=desc):
            pass


def _split_spritesheet(spritesheet_path: StrPath, output_dir: StrPath) -> None:
    with Image.open(spritesheet_path) as sheet:
        if SPRITE_SCALE > 1:
            sheet = sheet.resize(
                size=(
                    sheet.width * SPRITE_SCALE,
                    sheet.height * SPRITE_SCALE,
                ),
                resample=Resampling.NEAREST,
            )

        sheet_name = Path(spritesheet_path).stem
        sheet_output_dir = Path(output_dir) / sheet_name
        sheet_output_dir.mkdir(parents=True, exist_ok=True)

        sprite_width = SPRITE_WIDTH * SPRITE_SCALE
        sprite_height = SPRITE_HEIGHT * SPRITE_SCALE
        sheet_capacity = SPRITESHEET_ROWS * SPRITESHEET_COLUMNS - 1
        max_sprite_id = min(FusionClient.MAX_ID, sheet_capacity)

        for sprite_id in range(1, max_sprite_id + 1):
            row, column = divmod(sprite_id, SPRITESHEET_COLUMNS)
            box = (
                column * sprite_width,
                row * sprite_height,
                (column + 1) * sprite_width,
                (row + 1) * sprite_height,
            )

            output_path = sheet_output_dir / f"{sheet_name}.{sprite_id}.png"
            sprite = sheet.crop(box)
            sprite.save(output_path)
