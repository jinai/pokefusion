import logging
import platform
import shutil
import subprocess
from pathlib import Path

from pokefusion.assetpaths import AssetPaths
from pokefusion.types import StrPath

logger = logging.getLogger(__name__)


def fast_delete(path: StrPath) -> None:
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


def clean_output_folder() -> None:
    folder = Path("pokefusion", "scripts", "output")

    if folder.exists():
        logger.info(f"Cleaning '{folder.resolve()}'")
        fast_delete(folder)


def clean_assets_folder() -> None:
    folders = [
        AssetPaths.EGGS_DIR,
        AssetPaths.FUSIONS_DIR,
    ]

    for folder in folders:
        if folder.exists():
            logger.info(f"Cleaning '{folder.resolve()}'")
            fast_delete(folder)
