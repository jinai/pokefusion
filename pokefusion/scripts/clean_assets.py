import logging
import os
import platform
import shutil
import subprocess

logger = logging.getLogger(__name__)


def fast_delete(path: str) -> None:
    system = platform.system()
    if system in ("Linux", "Darwin"):
        subprocess.run(["rm", "-rf", path], check=True)
    elif system == "Windows":
        subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", path], check=True)
    else:
        shutil.rmtree(path)


def restore_git_files() -> None:
    commands = [
        "git reset --mixed HEAD",
        "git checkout-index -a"
    ]
    for command in commands:
        subprocess.run(command, shell=True)


def clean_output_folder() -> None:
    folder = os.path.abspath(os.path.join("pokefusion", "scripts", "output"))
    logger.info(f"About to clean: {folder}")
    if os.path.exists(folder):
        fast_delete(folder)


def clean_assets_folder() -> None:
    folders = [
        os.path.abspath(os.path.join("pokefusion", "assets", "eggs")),
        os.path.abspath(os.path.join("pokefusion", "assets", "fusions"))
    ]

    for folder in folders:
        logger.info(f"About to clean: {folder}")
        if os.path.exists(folder):
            fast_delete(folder)
