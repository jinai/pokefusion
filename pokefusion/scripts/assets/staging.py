import json
import logging
import os
import re
import time
from collections import defaultdict
from pathlib import Path

from pokefusion.assetpaths import AssetPaths
from pokefusion.scripts.assets.autogen import stage_autogen_sprites
from pokefusion.scripts.assets.pack import stage_custom_sprites, stage_egg_sprites
from pokefusion.scripts.assets.paths import (
    APPLIED_METADATA_PATHS,
    STAGING_AUTOGEN_DIFF_ADDED_PATH,
    STAGING_AUTOGEN_DIFF_REMOVED_PATH,
    STAGING_AUTOGEN_DIR,
    STAGING_CUSTOM_DIFF_ADDED_PATH,
    STAGING_CUSTOM_DIFF_REMOVED_PATH,
    STAGING_CUSTOM_DIR,
    STAGING_CUSTOM_FUSIONS_PATH,
    STAGING_EGGS_DIFF_ADDED_PATH,
    STAGING_EGGS_DIFF_REMOVED_PATH,
    STAGING_EGGS_DIR,
)
from pokefusion.scripts.assets.workspace import clean_staging_assets
from pokefusion.scripts.utils import regex_filter
from pokefusion.types import FusionMapping, StrPath

logger = logging.getLogger(__name__)

SPRITE_PATTERN = re.compile(r"^\d+\.\d+\.png$")
EGG_PATTERN = re.compile(r"^\d*[1-9]\d*\.png$")


class IncompleteStagingError(RuntimeError):
    pass


def stage_assets(pack_path: Path, *, custom_workers: int | None = None) -> None:
    logger.info("Staging assets")
    start_time = time.perf_counter()

    clean_staging_assets()
    stage_autogen_sprites()
    stage_custom_sprites(pack_path, workers=custom_workers)
    stage_egg_sprites(pack_path)
    generate_asset_metadata()

    elapsed_time = time.perf_counter() - start_time
    logger.info("Staged assets in %.2f seconds", elapsed_time)


def generate_asset_metadata() -> None:
    logger.info("Generating asset metadata")
    start_time = time.perf_counter()

    _validate_staged_sprites()

    autogen_old = _get_fusions(AssetPaths.FUSIONS_AUTOGEN_DIR)
    autogen_new = _get_fusions(STAGING_AUTOGEN_DIR)
    custom_old = _get_fusions(AssetPaths.FUSIONS_CUSTOM_DIR)
    custom_new = _get_fusions(STAGING_CUSTOM_DIR)
    eggs_old = _get_eggs(AssetPaths.EGGS_DIR)
    eggs_new = _get_eggs(STAGING_EGGS_DIR)

    autogen_diff_added = _get_fusions_diff(autogen_old, autogen_new)
    autogen_diff_removed = _get_fusions_diff(autogen_new, autogen_old)
    custom_diff_added = _get_fusions_diff(custom_old, custom_new)
    custom_diff_removed = _get_fusions_diff(custom_new, custom_old)
    eggs_diff_added = _get_eggs_diff(eggs_old, eggs_new)
    eggs_diff_removed = _get_eggs_diff(eggs_new, eggs_old)

    metadata = {
        STAGING_CUSTOM_FUSIONS_PATH: custom_new,
        STAGING_AUTOGEN_DIFF_ADDED_PATH: autogen_diff_added,
        STAGING_AUTOGEN_DIFF_REMOVED_PATH: autogen_diff_removed,
        STAGING_CUSTOM_DIFF_ADDED_PATH: custom_diff_added,
        STAGING_CUSTOM_DIFF_REMOVED_PATH: custom_diff_removed,
        STAGING_EGGS_DIFF_ADDED_PATH: eggs_diff_added,
        STAGING_EGGS_DIFF_REMOVED_PATH: eggs_diff_removed,
    }

    for path, contents in metadata.items():
        path.write_text(json.dumps(contents), encoding="utf-8")

    elapsed_time = time.perf_counter() - start_time
    logger.info(
        "Generated asset metadata for +%d/-%d autogen fusions, +%d/-%d custom fusions and +%d/-%d eggs in %.2f seconds",
        sum(map(len, autogen_diff_added.values())),
        sum(map(len, autogen_diff_removed.values())),
        sum(map(len, custom_diff_added.values())),
        sum(map(len, custom_diff_removed.values())),
        len(eggs_diff_added),
        len(eggs_diff_removed),
        elapsed_time,
    )


def validate_staged_assets() -> None:
    _validate_staged_sprites()

    missing_paths = [staged_path for staged_path in APPLIED_METADATA_PATHS if not staged_path.exists()]

    if missing_paths:
        formatted_paths = "\n".join(f"  - {path}" for path in missing_paths)
        raise IncompleteStagingError(f"The following metadata files are missing:\n{formatted_paths}")


def _validate_staged_sprites() -> None:
    sprite_patterns = (
        (STAGING_AUTOGEN_DIR, SPRITE_PATTERN),
        (STAGING_CUSTOM_DIR, SPRITE_PATTERN),
        (STAGING_EGGS_DIR, EGG_PATTERN),
    )

    invalid_directories = [
        directory for directory, pattern in sprite_patterns if not _contains_sprite(directory, pattern)
    ]

    if invalid_directories:
        formatted_directories = "\n".join(f"  - {directory}" for directory in invalid_directories)
        raise IncompleteStagingError(f"The following sprite directories are missing or empty:\n{formatted_directories}")


def _contains_sprite(directory: Path, pattern: re.Pattern[str]) -> bool:
    return directory.is_dir() and any(
        path.is_file() and pattern.fullmatch(path.name) for path in directory.rglob("*.png")
    )


def _get_fusions(directory: StrPath) -> FusionMapping:
    fusions = defaultdict(list)

    for _, _, filenames in os.walk(directory):
        for filename in regex_filter(filenames, SPRITE_PATTERN):
            head, body = Path(filename).stem.split(".", 1)
            fusions[int(head)].append(int(body))

    return {key: sorted(val) for key, val in sorted(fusions.items(), key=lambda item: item[0])}


def _get_fusions_diff(old: FusionMapping, new: FusionMapping) -> FusionMapping:
    diff = defaultdict(list)

    for head, new_bodies in new.items():
        if head not in old:
            diff[head] = new_bodies[:]
            continue

        old_bodies = old[head]
        for body in new_bodies:
            if body not in old_bodies:
                diff[head].append(body)

    return diff


def _get_eggs(directory: StrPath) -> list[int]:
    eggs = []

    for _, _, filenames in os.walk(directory):
        for filename in regex_filter(filenames, EGG_PATTERN):
            eggs.append(int(Path(filename).stem))

    return sorted(eggs)


def _get_eggs_diff(old: list[int], new: list[int]) -> list[int]:
    i = j = 0
    diff = []

    while i < len(old) and j < len(new):
        if old[i] < new[j]:
            i += 1
        elif old[i] > new[j]:
            diff.append(new[j])
            j += 1
        else:
            i += 1
            j += 1

    diff.extend(new[j:])
    return diff
