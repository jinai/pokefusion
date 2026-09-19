import json
import logging
import os
import platform
import re
import shutil
import subprocess
import time
import zipfile
from collections import defaultdict
from pathlib import Path

from tqdm import tqdm

from pokefusion.assetpaths import AssetPaths
from pokefusion.configmanager import ConfigManager
from pokefusion.fusionapi import FusionClient
from pokefusion.imagelib import save_resized_image
from pokefusion.scripts.git import restore_deleted_files, run_git
from pokefusion.scripts.spritesheets import split_spritesheets
from pokefusion.scripts.utils import make_backup, regex_filter
from pokefusion.types import StrPath

logger = logging.getLogger(__name__)

ZIP_FUSION_PATTERN = re.compile(r"CustomBattlers/\d+\.\d+\.png")
ZIP_EGG_PATTERN = re.compile(r"Other/Eggs/\d*[1-9]\d*\.png")
SPRITE_PATTERN = re.compile(r"\d+\.\d+\.png")
EGG_PATTERN = re.compile(r"\d*[1-9]\d*\.png")

AUTOGEN_REPOSITORY_URL = "https://github.com/infinitefusion/infinitefusion-e18.git"
AUTOGEN_REPOSITORY_BRANCH = "develop-6.6"
AUTOGEN_SPRITESHEETS_RELATIVE_DIR = Path("Graphics", "Battlers", "spritesheets_autogen")

PACKS_DIR = Path("pokefusion", "scripts", "input")
STAGING_DIR = Path("pokefusion", "scripts", "output")
CACHE_DIR = Path("cache")

AUTOGEN_REPOSITORY_DIR = CACHE_DIR / "infinitefusion-e18"
AUTOGEN_SPRITESHEETS_DIR = AUTOGEN_REPOSITORY_DIR / AUTOGEN_SPRITESHEETS_RELATIVE_DIR

STAGING_FUSIONS_DIR = STAGING_DIR / "fusions"
STAGING_AUTOGEN_DIR = STAGING_FUSIONS_DIR / "autogen"
STAGING_CUSTOM_DIR = STAGING_FUSIONS_DIR / "custom"
STAGING_EGGS_DIR = STAGING_DIR / "eggs"
STAGING_DEFAULT_EGG_PATH = STAGING_EGGS_DIR / AssetPaths.DEFAULT_EGG_PATH.name

STAGING_CUSTOM_FUSIONS_PATH = STAGING_DIR / "custom_fusions.json"
STAGING_AUTOGEN_DIFF_ADDED_PATH = STAGING_DIR / "autogen_diff_added.json"
STAGING_AUTOGEN_DIFF_REMOVED_PATH = STAGING_DIR / "autogen_diff_removed.json"
STAGING_CUSTOM_DIFF_ADDED_PATH = STAGING_DIR / "custom_diff_added.json"
STAGING_CUSTOM_DIFF_REMOVED_PATH = STAGING_DIR / "custom_diff_removed.json"
STAGING_EGGS_DIFF_ADDED_PATH = STAGING_DIR / "eggs_diff_added.json"
STAGING_EGGS_DIFF_REMOVED_PATH = STAGING_DIR / "eggs_diff_removed.json"

CUSTOM_FUSIONS_CONFIG_PATH = ConfigManager.CONFIG_DIR / STAGING_CUSTOM_FUSIONS_PATH.name
CUSTOM_DIFF_ADDED_CONFIG_PATH = ConfigManager.CONFIG_DIR / STAGING_CUSTOM_DIFF_ADDED_PATH.name

STAGING_SPRITE_DIRS = (
    STAGING_AUTOGEN_DIR,
    STAGING_CUSTOM_DIR,
    STAGING_EGGS_DIR,
)

STAGING_METADATA_PATHS = (
    STAGING_CUSTOM_FUSIONS_PATH,
    STAGING_AUTOGEN_DIFF_ADDED_PATH,
    STAGING_AUTOGEN_DIFF_REMOVED_PATH,
    STAGING_CUSTOM_DIFF_ADDED_PATH,
    STAGING_CUSTOM_DIFF_REMOVED_PATH,
    STAGING_EGGS_DIFF_ADDED_PATH,
    STAGING_EGGS_DIFF_REMOVED_PATH,
)

APPLIED_METADATA_PATHS = {
    STAGING_CUSTOM_FUSIONS_PATH: CUSTOM_FUSIONS_CONFIG_PATH,
    STAGING_CUSTOM_DIFF_ADDED_PATH: CUSTOM_DIFF_ADDED_CONFIG_PATH,
}


class InvalidPackError(ValueError):
    pass


class IncompleteStagingError(RuntimeError):
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


def update_assets(pack_path: Path) -> None:
    logger.info("Updating assets")
    start_time = time.perf_counter()

    stage_assets(pack_path)
    apply_staged_assets()

    elapsed_time = time.perf_counter() - start_time
    logger.info("Updated assets in %.2f seconds", elapsed_time)
    logger.info("Remember to update FusionClient.PREVIOUS_MAX_ID if necessary")


def stage_assets(pack_path: Path) -> None:
    logger.info("Staging assets")
    start_time = time.perf_counter()

    clean_staging_assets()
    stage_autogen_sprites()
    stage_custom_sprites(pack_path)
    stage_egg_sprites(pack_path)
    generate_asset_metadata()

    elapsed_time = time.perf_counter() - start_time
    logger.info("Staged assets in %.2f seconds", elapsed_time)


def stage_autogen_sprites() -> None:
    logger.info("Staging autogen sprites from the Infinite Fusion repository")
    stage_start_time = time.perf_counter()

    _prepare_staging_directory(STAGING_AUTOGEN_DIR)
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

    split_spritesheets(AUTOGEN_SPRITESHEETS_DIR, STAGING_AUTOGEN_DIR)

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


def stage_custom_sprites(pack_path: Path) -> None:
    logger.info("Staging custom sprites from '%s'", pack_path)
    start_time = time.perf_counter()

    _prepare_staging_directory(STAGING_CUSTOM_DIR)

    sprite_count = 0
    created_directories = set()

    with zipfile.ZipFile(pack_path, "r") as archive:
        filenames = list(regex_filter(archive.namelist(), ZIP_FUSION_PATTERN))
        desc = "Staging custom sprites from ZIP file"

        for filename in tqdm(filenames, desc=desc):
            head, body = map(int, Path(filename).stem.split(".", 1))

            if head > FusionClient.MAX_ID or body > FusionClient.MAX_ID:
                continue

            sprite_count += 1
            sprite_output_dir = STAGING_CUSTOM_DIR / str(head)

            if head not in created_directories:
                sprite_output_dir.mkdir(parents=True, exist_ok=True)
                created_directories.add(head)

            sprite_output_path = sprite_output_dir / f"{head}.{body}.png"
            with archive.open(filename) as sprite_file:
                save_resized_image(sprite_file, sprite_output_path, scale=2 / 3)

    elapsed_time = time.perf_counter() - start_time
    logger.info(
        "Staged %d custom sprites (discarded %d above MAX_ID) in %.2f seconds",
        sprite_count,
        len(filenames) - sprite_count,
        elapsed_time,
    )


def stage_egg_sprites(pack_path: Path) -> None:
    logger.info("Staging egg sprites from '%s'", pack_path)
    start_time = time.perf_counter()

    _prepare_staging_directory(STAGING_EGGS_DIR)

    if not AssetPaths.DEFAULT_EGG_PATH.is_file():
        raise FileNotFoundError(f"Default egg sprite not found: '{AssetPaths.DEFAULT_EGG_PATH}'")

    AssetPaths.DEFAULT_EGG_PATH.copy(STAGING_DEFAULT_EGG_PATH)

    egg_count = 0

    with zipfile.ZipFile(pack_path, "r") as archive:
        filenames = list(regex_filter(archive.namelist(), ZIP_EGG_PATTERN))
        desc = "Staging egg sprites from ZIP file"

        for filename in tqdm(filenames, desc=desc):
            dex_id = int(Path(filename).stem)

            if dex_id > FusionClient.MAX_ID:
                continue

            egg_count += 1
            (STAGING_EGGS_DIR / f"{dex_id}.png").write_bytes(archive.read(filename))

    elapsed_time = time.perf_counter() - start_time
    logger.info(
        "Staged %d egg sprites (discarded %d above MAX_ID) in %.2f seconds",
        egg_count,
        len(filenames) - egg_count,
        elapsed_time,
    )


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


def apply_staged_assets() -> None:
    logger.info("Applying staged assets")
    apply_start_time = time.perf_counter()

    _validate_staged_assets()

    for current_path in APPLIED_METADATA_PATHS.values():
        if current_path.exists():
            make_backup(current_path)

    try:
        _clean_current_assets()

        logger.info("Moving staged assets into place")
        move_start_time = time.perf_counter()

        AssetPaths.FUSIONS_DIR.mkdir(parents=True, exist_ok=True)

        STAGING_AUTOGEN_DIR.move(AssetPaths.FUSIONS_AUTOGEN_DIR)
        STAGING_CUSTOM_DIR.move(AssetPaths.FUSIONS_CUSTOM_DIR)
        STAGING_EGGS_DIR.move(AssetPaths.EGGS_DIR)

        for staged_path, current_path in APPLIED_METADATA_PATHS.items():
            staged_path.move(current_path)

        move_elapsed_time = time.perf_counter() - move_start_time
        logger.info("Moved staged assets into place in %.2f seconds", move_elapsed_time)
    finally:
        restore_deleted_files()

    apply_elapsed_time = time.perf_counter() - apply_start_time
    logger.info("Applied staged assets in %.2f seconds", apply_elapsed_time)


def clean_staging_assets() -> None:
    if not STAGING_DIR.exists():
        logger.info("Asset staging directory is already clean")
        return

    logger.info("Cleaning staging assets: '%s'", STAGING_DIR.resolve())
    start_time = time.perf_counter()

    _fast_delete(STAGING_DIR)

    elapsed_time = time.perf_counter() - start_time
    logger.info("Cleaned staging assets in %.2f seconds", elapsed_time)


def clean_asset_cache() -> None:
    if not CACHE_DIR.exists():
        logger.info("Asset cache is already clean")
        return

    logger.info("Cleaning asset cache directory: '%s'", CACHE_DIR.resolve())
    start_time = time.perf_counter()

    _fast_delete(CACHE_DIR)

    elapsed_time = time.perf_counter() - start_time
    logger.info("Cleaned asset cache in %.2f seconds", elapsed_time)


def _clean_current_assets() -> None:
    start_time = time.perf_counter()

    directories = (
        AssetPaths.EGGS_DIR,
        AssetPaths.FUSIONS_DIR,
    )

    for directory in directories:
        if directory.exists():
            logger.info("Cleaning current asset directory: '%s'", directory.resolve())
            _fast_delete(directory)

    elapsed_time = time.perf_counter() - start_time
    logger.info("Cleaned current assets in %.2f seconds", elapsed_time)


def _prepare_staging_directory(path: Path) -> None:
    _invalidate_asset_metadata()

    if path.exists():
        logger.info("Cleaning existing staging directory: '%s'", path.resolve())
        clean_start_time = time.perf_counter()

        _fast_delete(path)

        clean_elapsed_time = time.perf_counter() - clean_start_time
        logger.info("Cleaned existing staging directory in %.2f seconds", clean_elapsed_time)

    path.mkdir(parents=True)


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


def _invalidate_asset_metadata() -> None:
    for path in STAGING_METADATA_PATHS:
        path.unlink(missing_ok=True)


def _validate_staged_assets() -> None:
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


def _get_fusions(directory: StrPath) -> dict[int, list[int]]:
    fusions = defaultdict(list)

    for _, _, filenames in os.walk(directory):
        for filename in regex_filter(filenames, SPRITE_PATTERN):
            head, body = Path(filename).stem.split(".", 1)
            fusions[int(head)].append(int(body))

    return {key: sorted(val) for key, val in sorted(fusions.items(), key=lambda item: item[0])}


def _get_fusions_diff(old: dict[int, list[int]], new: dict[int, list[int]]) -> dict[int, list[int]]:
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


def _fast_delete(path: StrPath) -> None:
    path = Path(path)
    resolved_path = path.resolve()

    protected_paths = {
        Path(resolved_path.anchor),
        Path.cwd().resolve(),
        Path.home().resolve(),
    }

    if resolved_path in protected_paths:
        raise ValueError(f"Preventing deletion of protected directory: {resolved_path}")

    system = platform.system()

    if system in ("Linux", "Darwin"):
        subprocess.run(["rm", "-rf", "--", path], check=True)
    elif system == "Windows":
        subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", path], check=True)
    else:
        shutil.rmtree(path)
