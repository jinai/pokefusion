import logging
import platform
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from tqdm import tqdm

from pokefusion.assetpaths import AssetPaths
from pokefusion.scripts.assets.paths import (
    APPLIED_METADATA_PATHS,
    STAGING_AUTOGEN_DIR,
    STAGING_CUSTOM_DIR,
    STAGING_EGGS_DIR,
)
from pokefusion.scripts.assets.staging import (
    stage_assets,
    validate_staged_assets,
)
from pokefusion.scripts.git import restore_deleted_files
from pokefusion.scripts.utils import fast_delete, make_backup

logger = logging.getLogger(__name__)

ASSET_CLEANUP_WORKERS = 8


def update_assets(pack_path: Path, *, custom_workers: int | None = None) -> None:
    logger.info("Updating assets")
    start_time = time.perf_counter()

    stage_assets(pack_path, custom_workers=custom_workers)
    apply_staged_assets()

    elapsed_time = time.perf_counter() - start_time
    logger.info("Updated assets in %.2f seconds", elapsed_time)


def apply_staged_assets() -> None:
    logger.info("Applying staged assets")
    apply_start_time = time.perf_counter()

    validate_staged_assets()

    for current_path in APPLIED_METADATA_PATHS.values():
        if current_path.exists():
            make_backup(current_path)

    try:
        _clean_current_assets()

        logger.info("Moving staged assets into place")
        move_start_time = time.perf_counter()

        AssetPaths.FUSIONS_DIR.mkdir(parents=True, exist_ok=True)

        _move_staged_directory(STAGING_AUTOGEN_DIR, AssetPaths.FUSIONS_AUTOGEN_DIR)
        _move_staged_directory(STAGING_CUSTOM_DIR, AssetPaths.FUSIONS_CUSTOM_DIR)
        _move_staged_directory(STAGING_EGGS_DIR, AssetPaths.EGGS_DIR)

        for staged_path, current_path in APPLIED_METADATA_PATHS.items():
            staged_path.move(current_path)

        move_elapsed_time = time.perf_counter() - move_start_time
        logger.info("Moved staged assets into place in %.2f seconds", move_elapsed_time)
    finally:
        restore_deleted_files()

    apply_elapsed_time = time.perf_counter() - apply_start_time
    logger.info("Applied staged assets in %.2f seconds", apply_elapsed_time)


def _clean_current_assets() -> None:
    start_time = time.perf_counter()

    if platform.system() == "Windows":
        fusion_directories = []

        for root in (AssetPaths.FUSIONS_AUTOGEN_DIR, AssetPaths.FUSIONS_CUSTOM_DIR):
            if root.is_dir():
                for child in root.iterdir():
                    if child.is_dir() and not child.is_symlink():
                        fusion_directories.append(child)

        if fusion_directories:
            logger.info("Cleaning %d fusion sprite directories", len(fusion_directories))
            desc = f"Cleaning fusion sprite directories ({ASSET_CLEANUP_WORKERS} workers)"

            with ThreadPoolExecutor(max_workers=ASSET_CLEANUP_WORKERS) as executor:
                futures = [executor.submit(fast_delete, directory) for directory in fusion_directories]

                for future in tqdm(as_completed(futures), total=len(futures), desc=desc):
                    future.result()

    directories = (
        AssetPaths.EGGS_DIR,
        AssetPaths.FUSIONS_DIR,
    )

    for directory in directories:
        if directory.exists():
            logger.info("Cleaning current asset directory: '%s'", directory.resolve())
            fast_delete(directory)

    elapsed_time = time.perf_counter() - start_time
    logger.info("Cleaned current assets in %.2f seconds", elapsed_time)


def _move_staged_directory(source: Path, destination: Path) -> None:
    retry_deadline = time.monotonic() + 5
    retries = 0

    while True:
        try:
            source.move(destination)
            if retries:
                retry_label = "retry" if retries == 1 else "retries"
                logger.info("Moved '%s' after %d %s", source, retries, retry_label)
            return
        except PermissionError as error:
            if (
                platform.system() != "Windows"
                or error.winerror != 5
                or destination.exists()
                or time.monotonic() >= retry_deadline
            ):
                raise

            retries += 1
            time.sleep(0.1)
