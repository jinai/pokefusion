import json
import os
import re
import subprocess
import tempfile
import time
import zipfile
from collections import defaultdict
from collections.abc import Generator
from pathlib import Path
from typing import Iterable

from colorama import Fore, init
from tqdm import tqdm

import spritesheets

init(autoreset=True)

ZIP_FUSION_PATTERN = re.compile(r"CustomBattlers/\d+\.\d+\.png")
ZIP_EGG_PATTERN = re.compile(r"Other/Eggs/(?!000)\d+.png")
SPRITE_PATTERN = re.compile(r"\d+\.\d+\.png")
MAX_ID = 501


def import_autogen_sprites() -> None:
    start_time = time.perf_counter()

    print(Fore.CYAN + "Downloading autogen spritesheets...")
    output_dir = os.path.join("output", "fusions", "autogen")
    git_folder = Path("Graphics", "Battlers", "spritesheets_autogen")

    tempdir = tempfile.TemporaryDirectory(prefix="pokefusion_")
    commands = [
        f"git clone -n --depth=1 --filter=tree:0 -b releases --single-branch https://github.com/infinitefusion/infinitefusion-e18.git \"{tempdir.name}\"",
        f"git sparse-checkout set --no-cone /{git_folder.as_posix()}",
        "git checkout",
    ]
    for command in commands:
        subprocess.run(command, shell=True, cwd=tempdir.name)
    input_dir = os.path.join(tempdir.name, git_folder)
    sheet_count = len(next(os.walk(input_dir))[2])
    elapsed_time = time.perf_counter() - start_time
    print(f"Downloaded {sheet_count} autogen spritesheets in {elapsed_time:.2f} seconds")
    if sheet_count > MAX_ID:
        print(
            Fore.RED + f"\nFound more than {MAX_ID} autogen spritesheets! Check if new autogen sprites were released, and adapt MAX_ID accordingly\n")

    start_time = time.perf_counter()
    spritesheets.process_dir(input_dir, output_dir)
    tempdir.cleanup()
    sprite_count = sum(len(filenames) for _, _, filenames in os.walk(output_dir))

    elapsed_time = time.perf_counter() - start_time
    print(f"Processed {sprite_count} autogen sprites (from {sheet_count} spritesheets) in {elapsed_time:.2f} seconds")


def import_custom_sprites(pack_name: str) -> None:
    start_time = time.perf_counter()

    print(Fore.CYAN + "Importing custom sprites...")
    input_file = os.path.join("input", pack_name)
    if not zipfile.is_zipfile(input_file):
        print(f"Invalid ZIP: {input_file}")
        return

    output_dir = os.path.join("output", "fusions", "custom")
    sprite_count = 0
    file_count = 0
    existing_folders = set()
    with zipfile.ZipFile(input_file, "r") as zipf:
        desc = f"Importing sprites from ZIP file"
        for filename in regex_filter(tqdm(zipf.namelist(), desc=desc), ZIP_FUSION_PATTERN):
            file_count += 1
            head, body = map(int, os.path.splitext(os.path.basename(filename))[0].split(".", 1))
            if head > MAX_ID or body > MAX_ID:
                continue
            sprite_count += 1
            sprite_output_dir = os.path.join(output_dir, str(head))
            if head not in existing_folders:
                os.makedirs(sprite_output_dir, exist_ok=True)
                existing_folders.add(head)
            with open(os.path.join(sprite_output_dir, f"{head}.{body}.png"), "wb") as sprite_file:
                sprite_file.write(zipf.read(filename))

    elapsed_time = time.perf_counter() - start_time
    print(
        f"Processed {sprite_count} custom sprites (discarded {file_count - sprite_count} sprites > MAX_ID) in {elapsed_time:.2f} seconds")


def import_eggs(pack_name: str) -> None:
    start_time = time.perf_counter()

    print(Fore.CYAN + "Importing eggs...")
    input_file = os.path.join("input", pack_name)
    if not zipfile.is_zipfile(input_file):
        print(f"Invalid ZIP: {input_file}")
        return

    output_dir = os.path.join("output", "eggs")
    os.makedirs(output_dir, exist_ok=True)
    egg_count = 0
    file_count = 0
    with zipfile.ZipFile(input_file, "r") as zipf:
        desc = f"Importing eggs from ZIP file"
        for filename in regex_filter(tqdm(zipf.namelist(), desc=desc), ZIP_EGG_PATTERN):
            file_count += 1
            dex_id = int(os.path.splitext(os.path.basename(filename))[0])
            if dex_id < 1 or dex_id > MAX_ID:
                continue
            egg_count += 1
            with open(os.path.join(output_dir, f"{dex_id}.png"), "wb") as egg_file:
                egg_file.write(zipf.read(filename))

    elapsed_time = time.perf_counter() - start_time
    print(
        f"Processed {egg_count} eggs (discarded {file_count - egg_count} eggs > MAX_ID) in {elapsed_time:.2f} seconds")


def save_diff() -> None:
    start_time = time.perf_counter()

    print(Fore.CYAN + "Saving diffs...")

    autogen_folder_old = os.path.join("..", "assets", "fusions", "autogen")
    autogen_folder_new = os.path.join("output", "fusions", "autogen")
    custom_folder_old = os.path.join("..", "assets", "fusions", "custom")
    custom_folder_new = os.path.join("output", "fusions", "custom")

    base_output = "output"
    custom_fusions_output = os.path.join(base_output, "custom_fusions.json")
    autogen_diff_added_output = os.path.join(base_output, "autogen_diff_added.json")
    autogen_diff_removed_output = os.path.join(base_output, "autogen_diff_removed.json")
    custom_diff_added_output = os.path.join(base_output, "custom_diff_added.json")
    custom_diff_removed_output = os.path.join(base_output, "custom_diff_removed.json")

    autogen_old = get_fusions(autogen_folder_old)
    autogen_new = get_fusions(autogen_folder_new)
    custom_old = get_fusions(custom_folder_old)
    custom_new = get_fusions(custom_folder_new)
    autogen_diff_added = get_fusions_diff(autogen_old, autogen_new)
    autogen_diff_removed = get_fusions_diff(autogen_new, autogen_old)
    custom_diff_added = get_fusions_diff(custom_old, custom_new)
    custom_diff_removed = get_fusions_diff(custom_new, custom_old)

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

    elapsed_time = time.perf_counter() - start_time
    print(
        f"Saved diffs for +{autogen_diff_added_count}/-{autogen_diff_removed_count} autogen and +{custom_diff_added_count}/-{custom_diff_removed_count} custom fusions in {elapsed_time:.2f} seconds")


def regex_filter(sequence: Iterable[str], pattern: re.Pattern[str]) -> Generator[str, None, None]:
    for elem in sequence:
        if pattern.match(elem):
            yield elem


def get_fusions(folder: str) -> dict[int, list[int]]:
    fusions = defaultdict(list)
    for root, directories, filenames in os.walk(folder):
        for filename in sorted(regex_filter(filenames, SPRITE_PATTERN)):
            head, body = os.path.splitext(filename)[0].split(".", 1)
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


def run():
    start_time = time.perf_counter()
    pack_name = "Full Sprite pack 1-118 (September 2025).zip"
    import_autogen_sprites()
    print()
    import_custom_sprites(pack_name=pack_name)
    print()
    import_eggs(pack_name=pack_name)
    print()
    save_diff()
    print()
    elapsed_time = time.perf_counter() - start_time
    print(Fore.CYAN + f"Total runtime is {elapsed_time:.2f} seconds")
    print(Fore.MAGENTA + "Don't forget to update fusionapi.PREVIOUS_MAX_ID (even if no new base sprites)")


if __name__ == "__main__":
    run()
