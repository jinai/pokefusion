import logging
import os
import re
import time
import zipfile
from functools import cache, partial
from multiprocessing import Pool
from pathlib import Path

from tqdm import tqdm

from pokefusion.assetpaths import AssetPaths
from pokefusion.fusionapi import FusionClient
from pokefusion.imagelib import save_resized_image
from pokefusion.scripts.assets.paths import (
    PACKS_DIR,
    STAGING_CUSTOM_DIR,
    STAGING_DEFAULT_EGG_PATH,
    STAGING_EGGS_DIR,
)
from pokefusion.scripts.assets.workspace import prepare_staging_directory
from pokefusion.scripts.utils import regex_filter

logger = logging.getLogger(__name__)

ZIP_FUSION_PATTERN = re.compile(r"^CustomBattlers/\d+\.\d+\.png$")
ZIP_EGG_PATTERN = re.compile(r"^Other/Eggs/\d*[1-9]\d*\.png$")

DEFAULT_CUSTOM_SPRITE_WORKERS = 8
CUSTOM_SPRITE_CHUNKSIZE = 64
CUSTOM_SPRITE_SCALE = 2 / 3
CUSTOM_SPRITE_COMPRESSION_LEVEL = 3


class InvalidPackError(ValueError):
    pass


def resolve_pack(pack: Path) -> Path:
    if pack.suffix.casefold() != ".zip":
        pack = pack.with_name(pack.name + ".zip")

    if not pack.is_absolute():
        pack = PACKS_DIR / pack

    pack = pack.resolve()

    if zipfile.is_zipfile(pack):
        with zipfile.ZipFile(pack) as archive:
            if any(ZIP_FUSION_PATTERN.fullmatch(filename) for filename in archive.namelist()):
                return pack

    raise InvalidPackError(f"Invalid pack: {pack!r}")


def stage_custom_sprites(pack_path: Path, *, workers: int | None = None) -> None:
    logger.info("Staging custom sprites from '%s'", pack_path)
    staging_start_time = time.perf_counter()

    prepare_staging_directory(STAGING_CUSTOM_DIR)

    processing_start_time = time.perf_counter()

    with zipfile.ZipFile(pack_path, "r") as archive:
        filenames = list(regex_filter(archive.namelist(), ZIP_FUSION_PATTERN))

    tasks = []
    heads = set()

    for filename in filenames:
        head, body = map(int, Path(filename).stem.split(".", 1))

        if head > FusionClient.MAX_ID or body > FusionClient.MAX_ID:
            continue

        tasks.append((filename, head, body))
        heads.add(head)

    for head in heads:
        (STAGING_CUSTOM_DIR / str(head)).mkdir(parents=True)

    staged_count = len(tasks)
    discarded_count = len(filenames) - staged_count

    if staged_count:
        worker_count = min(
            workers if workers is not None else DEFAULT_CUSTOM_SPRITE_WORKERS,
            os.process_cpu_count() or 1,
            staged_count,
        )

        if worker_count > DEFAULT_CUSTOM_SPRITE_WORKERS:
            logger.warning(
                "Using %d custom sprite workers (default: up to %d); higher counts may exhaust available memory",
                worker_count,
                DEFAULT_CUSTOM_SPRITE_WORKERS,
            )

        worker_label = "worker" if worker_count == 1 else "workers"
        desc = f"Processing custom sprites from pack ({worker_count} {worker_label})"

        with Pool(worker_count) as pool:
            results = pool.imap_unordered(
                partial(_stage_custom_sprite, pack_path=pack_path),
                tasks,
                chunksize=CUSTOM_SPRITE_CHUNKSIZE,
            )

            for _ in tqdm(results, total=staged_count, desc=desc):
                pass

    processing_elapsed_time = time.perf_counter() - processing_start_time
    logger.info("Processed custom sprites from pack in %.2f seconds", processing_elapsed_time)

    if discarded_count:
        logger.warning(
            "Discarded %d custom sprites whose head or body ID exceeds MAX_ID (%d)",
            discarded_count,
            FusionClient.MAX_ID,
        )

    staging_elapsed_time = time.perf_counter() - staging_start_time
    logger.info("Staged %d custom sprites in %.2f seconds", staged_count, staging_elapsed_time)


def stage_egg_sprites(pack_path: Path) -> None:
    logger.info("Staging egg sprites from '%s'", pack_path)
    start_time = time.perf_counter()

    prepare_staging_directory(STAGING_EGGS_DIR)

    if not AssetPaths.DEFAULT_EGG_PATH.is_file():
        raise FileNotFoundError(f"Default egg sprite not found: '{AssetPaths.DEFAULT_EGG_PATH}'")

    AssetPaths.DEFAULT_EGG_PATH.copy(STAGING_DEFAULT_EGG_PATH)

    egg_count = 0

    with zipfile.ZipFile(pack_path, "r") as archive:
        filenames = list(regex_filter(archive.namelist(), ZIP_EGG_PATTERN))

        for filename in tqdm(filenames, desc="Extracting egg sprites from pack"):
            dex_id = int(Path(filename).stem)

            if dex_id > FusionClient.MAX_ID:
                continue

            egg_count += 1
            (STAGING_EGGS_DIR / f"{dex_id}.png").write_bytes(archive.read(filename))

    if discarded_count := len(filenames) - egg_count:
        logger.warning(
            "Discarded %d egg sprites whose ID exceeds MAX_ID (%d)",
            discarded_count,
            FusionClient.MAX_ID,
        )

    elapsed_time = time.perf_counter() - start_time
    logger.info("Staged %d egg sprites in %.2f seconds", egg_count, elapsed_time)


@cache
def _open_custom_archive(pack_path: Path) -> zipfile.ZipFile:
    return zipfile.ZipFile(pack_path, "r")


def _stage_custom_sprite(task: tuple[str, int, int], *, pack_path: Path) -> None:
    filename, head, body = task
    output_path = STAGING_CUSTOM_DIR / str(head) / f"{head}.{body}.png"

    with _open_custom_archive(pack_path).open(filename) as sprite_file:
        save_resized_image(
            sprite_file,
            output_path,
            scale=CUSTOM_SPRITE_SCALE,
            compress_level=CUSTOM_SPRITE_COMPRESSION_LEVEL,
        )
