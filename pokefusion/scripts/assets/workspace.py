import logging
import time
from pathlib import Path

from pokefusion.scripts.assets.paths import STAGING_DIR, STAGING_METADATA_PATHS
from pokefusion.scripts.utils import fast_delete

logger = logging.getLogger(__name__)


def clean_staging_assets() -> None:
    if not STAGING_DIR.exists():
        logger.info("Asset staging directory is already clean")
        return

    logger.info("Cleaning staging assets: '%s'", STAGING_DIR.resolve())
    start_time = time.perf_counter()

    fast_delete(STAGING_DIR)

    elapsed_time = time.perf_counter() - start_time
    logger.info("Cleaned staging assets in %.2f seconds", elapsed_time)


def prepare_staging_directory(path: Path) -> None:
    _invalidate_staged_metadata()

    if path.exists():
        logger.info("Cleaning existing staging directory: '%s'", path.resolve())
        clean_start_time = time.perf_counter()

        fast_delete(path)

        clean_elapsed_time = time.perf_counter() - clean_start_time
        logger.info("Cleaned existing staging directory in %.2f seconds", clean_elapsed_time)

    path.mkdir(parents=True)


def _invalidate_staged_metadata() -> None:
    for path in STAGING_METADATA_PATHS:
        path.unlink(missing_ok=True)
