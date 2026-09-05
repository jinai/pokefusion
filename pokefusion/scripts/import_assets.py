import contextlib
import json
import logging
import os
import re
import shutil
import tempfile
import time
import zipfile
from collections import defaultdict
from pathlib import Path

from tqdm import tqdm

from pokefusion.assetpaths import AssetPaths
from pokefusion.configmanager import ConfigManager
from pokefusion.fusionapi import FusionClient
from pokefusion.imagelib import save_resized_image
from pokefusion.types import StrPath
from . import spritesheets
from .git import run_git
from .utils import make_backup, regex_filter

logger = logging.getLogger(__name__)

ZIP_FUSION_PATTERN = re.compile(r"CustomBattlers/\d+\.\d+\.png")
ZIP_EGG_PATTERN = re.compile(r"Other/Eggs/(?!000)\d+.png")
SPRITE_PATTERN = re.compile(r"\d+\.\d+\.png")
EGG_PATTERN = re.compile(r"\d+\.png")

INPUT_DIR = Path("pokefusion", "scripts", "input")
OUTPUT_DIR = Path("pokefusion", "scripts", "output")


class InvalidPackError(ValueError):
    pass


def resolve_pack(pack: Path) -> Path:
    if pack.suffix.casefold() != ".zip":
        pack = pack.with_name(pack.name + ".zip")

    if not pack.is_absolute():
        pack = INPUT_DIR / pack

    pack = pack.resolve()

    if zipfile.is_zipfile(pack):
        with zipfile.ZipFile(pack) as zf:
            with contextlib.suppress(KeyError):
                zf.getinfo("CustomBattlers/")
                return pack

    raise InvalidPackError(f"Invalid pack: {pack!r}")


def import_autogen_sprites() -> None:
    start_time = time.perf_counter()

    output_dir = OUTPUT_DIR / "fusions" / "autogen"
    git_folder = Path("Graphics", "Battlers", "spritesheets_autogen")

    with tempfile.TemporaryDirectory(prefix="pokefusion_") as tempdir:
        commands = [
            [
                "clone",
                "-n",
                "--depth=1",
                "--filter=tree:0",
                "-b",
                "develop-6.6",
                "--single-branch",
                "https://github.com/infinitefusion/infinitefusion-e18.git",
                tempdir,
            ],
            [
                "-C",
                tempdir,
                "sparse-checkout",
                "set",
                "--no-cone",
                f"/{git_folder.as_posix()}",
            ],
            [
                "-C",
                tempdir,
                "checkout",
            ],
        ]

        for arguments in commands:
            run_git(arguments)

        input_dir = Path(tempdir) / git_folder
        sheet_count = len(next(os.walk(input_dir))[2])

        elapsed_time = time.perf_counter() - start_time
        logger.info(f"Downloaded {sheet_count} autogen spritesheets in {elapsed_time:.2f} seconds")

        if sheet_count > FusionClient.MAX_ID:
            logger.warning(
                f"Found more than {FusionClient.MAX_ID} autogen spritesheets! "
                "Check if new autogen sprites were released, and adapt MAX_ID accordingly"
            )

        start_time = time.perf_counter()

        spritesheets.process_dir(input_dir, output_dir)

    sprite_count = sum(len(filenames) for _, _, filenames in os.walk(output_dir))

    elapsed_time = time.perf_counter() - start_time
    logger.info(
        f"Processed {sprite_count} autogen sprites (from {sheet_count} spritesheets) in {elapsed_time:.2f} seconds")


def import_custom_sprites(pack_path: Path) -> None:
    start_time = time.perf_counter()

    output_dir = OUTPUT_DIR / "fusions" / "custom"

    sprite_count = 0
    file_count = 0
    existing_folders = set()

    with zipfile.ZipFile(pack_path, "r") as zipf:
        desc = "Importing sprites from ZIP file"

        for filename in regex_filter(tqdm(zipf.namelist(), desc=desc), ZIP_FUSION_PATTERN):
            file_count += 1
            head, body = map(int, Path(filename).stem.split(".", 1))

            if head > FusionClient.MAX_ID or body > FusionClient.MAX_ID:
                continue

            sprite_count += 1
            sprite_output_dir = output_dir / str(head)

            if head not in existing_folders:
                sprite_output_dir.mkdir(parents=True, exist_ok=True)
                existing_folders.add(head)

            sprite_output_path = sprite_output_dir / f"{head}.{body}.png"
            with zipf.open(filename) as sprite_file:
                save_resized_image(sprite_file, sprite_output_path, scale=2 / 3)

    elapsed_time = time.perf_counter() - start_time
    logger.info(
        f"Processed {sprite_count} custom sprites (discarded {file_count - sprite_count} sprites > MAX_ID) in {elapsed_time:.2f} seconds")


def import_egg_sprites(pack_path: Path) -> None:
    start_time = time.perf_counter()

    output_dir = OUTPUT_DIR / "eggs"
    output_dir.mkdir(parents=True, exist_ok=True)

    egg_count = 0
    file_count = 0

    with zipfile.ZipFile(pack_path, "r") as zipf:
        desc = "Importing egg sprites from ZIP file"

        for filename in regex_filter(tqdm(zipf.namelist(), desc=desc), ZIP_EGG_PATTERN):
            file_count += 1
            dex_id = int(Path(filename).stem)

            if dex_id < 1 or dex_id > FusionClient.MAX_ID:
                continue

            egg_count += 1
            with open(output_dir / f"{dex_id}.png", "wb") as egg_file:
                egg_file.write(zipf.read(filename))

    elapsed_time = time.perf_counter() - start_time
    logger.info(
        f"Processed {egg_count} egg sprites (discarded {file_count - egg_count} egg sprites > MAX_ID) in {elapsed_time:.2f} seconds")


def save_diff() -> None:
    start_time = time.perf_counter()

    autogen_folder_new = OUTPUT_DIR / "fusions" / "autogen"
    custom_folder_new = OUTPUT_DIR / "fusions" / "custom"
    eggs_folder_new = OUTPUT_DIR / "eggs"

    custom_fusions_output = OUTPUT_DIR / "custom_fusions.json"
    autogen_diff_added_output = OUTPUT_DIR / "autogen_diff_added.json"
    autogen_diff_removed_output = OUTPUT_DIR / "autogen_diff_removed.json"
    custom_diff_added_output = OUTPUT_DIR / "custom_diff_added.json"
    custom_diff_removed_output = OUTPUT_DIR / "custom_diff_removed.json"
    eggs_diff_added_output = OUTPUT_DIR / "eggs_diff_added.json"
    eggs_diff_removed_output = OUTPUT_DIR / "eggs_diff_removed.json"

    autogen_old = get_fusions(AssetPaths.FUSIONS_AUTOGEN_DIR)
    autogen_new = get_fusions(autogen_folder_new)
    custom_old = get_fusions(AssetPaths.FUSIONS_CUSTOM_DIR)
    custom_new = get_fusions(custom_folder_new)
    eggs_old = get_eggs(AssetPaths.EGGS_DIR)
    eggs_new = get_eggs(eggs_folder_new)
    autogen_diff_added = get_fusions_diff(autogen_old, autogen_new)
    autogen_diff_removed = get_fusions_diff(autogen_new, autogen_old)
    custom_diff_added = get_fusions_diff(custom_old, custom_new)
    custom_diff_removed = get_fusions_diff(custom_new, custom_old)
    eggs_diff_added = get_eggs_diff(eggs_old, eggs_new)
    eggs_diff_removed = get_eggs_diff(eggs_new, eggs_old)

    autogen_diff_added_count = 0
    autogen_diff_removed_count = 0
    custom_diff_added_count = 0
    custom_diff_removed_count = 0
    for head in autogen_diff_added:
        autogen_diff_added_count += len(autogen_diff_added[head])
    for head in autogen_diff_removed:
        autogen_diff_removed_count += len(autogen_diff_removed[head])
    for head in custom_diff_added:
        custom_diff_added_count += len(custom_diff_added[head])
    for head in custom_diff_removed:
        custom_diff_removed_count += len(custom_diff_removed[head])

    with open(custom_fusions_output, "w", encoding="utf-8") as f:
        json.dump(custom_new, f)
    with open(autogen_diff_added_output, "w", encoding="utf-8") as f:
        json.dump(autogen_diff_added, f)
    with open(autogen_diff_removed_output, "w", encoding="utf-8") as f:
        json.dump(autogen_diff_removed, f)
    with open(custom_diff_added_output, "w", encoding="utf-8") as f:
        json.dump(custom_diff_added, f)
    with open(custom_diff_removed_output, "w", encoding="utf-8") as f:
        json.dump(custom_diff_removed, f)
    with open(eggs_diff_added_output, "w", encoding="utf-8") as f:
        json.dump(eggs_diff_added, f)
    with open(eggs_diff_removed_output, "w", encoding="utf-8") as f:
        json.dump(eggs_diff_removed, f)

    elapsed_time = time.perf_counter() - start_time
    logger.info(
        f"Saved diffs for +{autogen_diff_added_count}/-{autogen_diff_removed_count} autogen fusions, +{custom_diff_added_count}/-{custom_diff_removed_count} custom fusions and +{len(eggs_diff_added)}/-{len(eggs_diff_removed)} eggs in {elapsed_time:.2f} seconds")


def move_to_assets():
    start_time = time.perf_counter()

    autogen_output = OUTPUT_DIR / "fusions" / "autogen"
    custom_output = OUTPUT_DIR / "fusions" / "custom"
    eggs_output = OUTPUT_DIR / "eggs"
    custom_fusions_output = OUTPUT_DIR / "custom_fusions.json"
    custom_diff_added_output = OUTPUT_DIR / "custom_diff_added.json"

    custom_fusions_assets = ConfigManager.CONFIG_DIR / "custom_fusions.json"
    custom_diff_added_assets = ConfigManager.CONFIG_DIR / "custom_diff_added.json"

    move_autogen = autogen_output.exists()
    move_custom = custom_output.exists()
    move_eggs = eggs_output.exists()
    move_config = custom_fusions_output.exists() and custom_diff_added_output.exists()

    if move_autogen or move_custom:
        AssetPaths.FUSIONS_DIR.mkdir(parents=True, exist_ok=True)

    if move_autogen:
        shutil.move(autogen_output, AssetPaths.FUSIONS_DIR)

    if move_custom:
        shutil.move(custom_output, AssetPaths.FUSIONS_DIR)

    if move_eggs:
        shutil.move(eggs_output, AssetPaths.ASSETS_DIR)

    if move_config:
        if custom_fusions_assets.exists():
            make_backup(custom_fusions_assets)

        if custom_diff_added_assets.exists():
            make_backup(custom_diff_added_assets)

        shutil.move(custom_fusions_output, custom_fusions_assets)
        shutil.move(custom_diff_added_output, custom_diff_added_assets)

    elapsed_time = time.perf_counter() - start_time
    logger.info(f"Moved files to assets folder in {elapsed_time:.2f} seconds")


def get_fusions(folder: StrPath) -> dict[int, list[int]]:
    fusions = defaultdict(list)

    for root, directories, filenames in os.walk(folder):
        for filename in regex_filter(filenames, SPRITE_PATTERN):
            head, body = Path(filename).stem.split(".", 1)
            fusions[int(head)].append(int(body))

    return {key: sorted(val) for key, val in sorted(fusions.items(), key=lambda item: item[0])}


def get_fusions_diff(old: dict[int, list[int]], new: dict[int, list[int]]) -> dict[int, list[int]]:
    diff = defaultdict(list)

    for head in new:
        if head in old:
            for body in new[head]:
                if body not in old[head]:
                    diff[head].append(body)
        else:
            diff[head] = new[head][:]

    return diff


def get_eggs(folder: StrPath) -> list[int]:
    eggs = []

    for root, directories, filenames in os.walk(folder):
        for filename in regex_filter(filenames, EGG_PATTERN):
            egg = Path(filename).stem
            eggs.append(int(egg))

    return sorted(eggs)


def get_eggs_diff(old: list[int], new: list[int]) -> list[int]:
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
