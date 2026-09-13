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
from pokefusion.scripts import spritesheets
from pokefusion.scripts.git import run_git
from pokefusion.scripts.utils import make_backup, regex_filter
from pokefusion.types import StrPath

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
        with zipfile.ZipFile(pack) as zf, contextlib.suppress(KeyError):
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
        logger.info("Downloaded %d autogen spritesheets in %.2f seconds", sheet_count, elapsed_time)

        if sheet_count > FusionClient.MAX_ID:
            logger.warning(
                "Found more than %d autogen spritesheets! "
                "Check if new autogen sprites were released, and adapt MAX_ID accordingly",
                FusionClient.MAX_ID,
            )

        start_time = time.perf_counter()

        spritesheets.process_dir(input_dir, output_dir)

    sprite_count = sum(len(filenames) for _, _, filenames in os.walk(output_dir))

    elapsed_time = time.perf_counter() - start_time
    logger.info(
        "Processed %d autogen sprites (from %d spritesheets) in %.2f seconds",
        sprite_count,
        sheet_count,
        elapsed_time,
    )


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
        "Processed %d custom sprites (discarded %d sprites > MAX_ID) in %.2f seconds",
        sprite_count,
        file_count - sprite_count,
        elapsed_time,
    )


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
            (output_dir / f"{dex_id}.png").write_bytes(zipf.read(filename))

    elapsed_time = time.perf_counter() - start_time
    logger.info(
        "Processed %d egg sprites (discarded %d egg sprites > MAX_ID) in %.2f seconds",
        egg_count,
        file_count - egg_count,
        elapsed_time,
    )


def save_diff() -> None:
    start_time = time.perf_counter()

    autogen_old = _get_fusions(AssetPaths.FUSIONS_AUTOGEN_DIR)
    autogen_new = _get_fusions(OUTPUT_DIR / "fusions" / "autogen")
    custom_old = _get_fusions(AssetPaths.FUSIONS_CUSTOM_DIR)
    custom_new = _get_fusions(OUTPUT_DIR / "fusions" / "custom")
    eggs_old = _get_eggs(AssetPaths.EGGS_DIR)
    eggs_new = _get_eggs(OUTPUT_DIR / "eggs")

    autogen_diff_added = _get_fusions_diff(autogen_old, autogen_new)
    autogen_diff_removed = _get_fusions_diff(autogen_new, autogen_old)
    custom_diff_added = _get_fusions_diff(custom_old, custom_new)
    custom_diff_removed = _get_fusions_diff(custom_new, custom_old)
    eggs_diff_added = _get_eggs_diff(eggs_old, eggs_new)
    eggs_diff_removed = _get_eggs_diff(eggs_new, eggs_old)

    (OUTPUT_DIR / "custom_fusions.json").write_text(json.dumps(custom_new), encoding="utf-8")
    (OUTPUT_DIR / "autogen_diff_added.json").write_text(json.dumps(autogen_diff_added), encoding="utf-8")
    (OUTPUT_DIR / "autogen_diff_removed.json").write_text(json.dumps(autogen_diff_removed), encoding="utf-8")
    (OUTPUT_DIR / "custom_diff_added.json").write_text(json.dumps(custom_diff_added), encoding="utf-8")
    (OUTPUT_DIR / "custom_diff_removed.json").write_text(json.dumps(custom_diff_removed), encoding="utf-8")
    (OUTPUT_DIR / "eggs_diff_added.json").write_text(json.dumps(eggs_diff_added), encoding="utf-8")
    (OUTPUT_DIR / "eggs_diff_removed.json").write_text(json.dumps(eggs_diff_removed), encoding="utf-8")

    elapsed_time = time.perf_counter() - start_time
    logger.info(
        "Saved diffs for +%d/-%d autogen fusions, +%d/-%d custom fusions, and +%d/-%d eggs in %.2f seconds",
        sum(map(len, autogen_diff_added.values())),
        sum(map(len, autogen_diff_removed.values())),
        sum(map(len, custom_diff_added.values())),
        sum(map(len, custom_diff_removed.values())),
        len(eggs_diff_added),
        len(eggs_diff_removed),
        elapsed_time,
    )


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
    logger.info("Moved files to assets folder in %.2f seconds", elapsed_time)


def _get_fusions(folder: StrPath) -> dict[int, list[int]]:
    fusions = defaultdict(list)

    for root, directories, filenames in os.walk(folder):
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


def _get_eggs(folder: StrPath) -> list[int]:
    eggs = []

    for root, directories, filenames in os.walk(folder):
        for filename in regex_filter(filenames, EGG_PATTERN):
            egg = Path(filename).stem
            eggs.append(int(egg))

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
