import json
import os
import re
import shutil
import time
from collections import defaultdict
from collections.abc import Generator
from io import BytesIO

from PIL import Image

from pokefusion import imagelib

AUTOGEN_SPRITE_PATTERN = re.compile(r"[0-9]+\.png")
CUSTOM_SPRITE_PATTERN = re.compile(r"[0-9]+\.[0-9]+\.png")
SPRITESHEET_ROWS = 51
SPRITESHEET_COLUMNS = 10
SPRITE_WIDTH = 96
SPRITE_HEIGHT = 96
MAX_ID = 501


def regex_filter(sequence: list[str], pattern: re.Pattern[str]) -> Generator[str, None, None]:
    for elem in sequence:
        if pattern.match(elem):
            yield elem


def split_spritesheet(path: str, rows: int, columns: int, height: int, width: int) -> Generator[BytesIO, None, None]:
    with Image.open(path) as im:
        for row in range(rows):
            for col in range(columns):
                x = col * width
                y = row * height
                box = (x, y, x + width, y + height)
                sprite = im.crop(box)
                buffer = BytesIO()
                sprite.save(buffer, format="png")
                yield buffer


def get_fusions(folder: str) -> dict[int, list[int]]:
    fusions = defaultdict(list)
    for root, directories, filenames in os.walk(folder):
        for filename in sorted(regex_filter(filenames, CUSTOM_SPRITE_PATTERN)):
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


def import_autogen_sprites(verbose: bool = True) -> None:
    start_time = time.perf_counter()
    input_folder = r"input\Full Sprite pack 1-114 (May 2025)\spritesheets\spritesheets_autogen"
    output_folder = os.path.join("output", "fusions", "autogen")
    sprite_count = 0
    file_count = 0
    existing_folders = set()

    for root, directories, filenames in os.walk(input_folder):
        file_count += len(filenames)
        for filename in regex_filter(filenames, AUTOGEN_SPRITE_PATTERN):
            path = os.path.join(root, filename)
            head = os.path.splitext(filename)[0]
            folder = os.path.join(output_folder, head)
            if head not in existing_folders:
                os.makedirs(folder, exist_ok=True)
                existing_folders.add(head)
            for body, buffer in enumerate(
                    split_spritesheet(path, SPRITESHEET_ROWS, SPRITESHEET_COLUMNS, SPRITE_HEIGHT, SPRITE_WIDTH)):
                if body == 0 or body > MAX_ID:  # unused sprites
                    continue
                sprite_count += 1
                sprite_path = os.path.join(folder, f"{head}.{body}.png")

                # Autogen sprites have a 1:1 pixel ratio whereas custom sprites have a 3:1 pixel ratio
                zoomed = imagelib.zoom_image(buffer, factor=3)

                with open(sprite_path, "wb") as f:
                    f.write(zoomed.getvalue())

                if verbose:
                    print(f"[{str(sprite_count).zfill(6)}/{head.zfill(6)}] {sprite_path}")

    elapsed_time = time.perf_counter() - start_time
    print(f"Processed {sprite_count} autogen sprites (out of {file_count} spritesheets) in {elapsed_time:.2f} seconds")


def import_custom_sprites(verbose: bool = True) -> None:
    start_time = time.perf_counter()
    input_folder = r"D:\infinitefusion\Full Sprite pack 1-111 (February 2025)\CustomBattlers"
    output_folder = os.path.join("output", "fusions", "custom")
    sprite_count = 0
    file_count = 0
    existing_folders = set()

    for root, directories, filenames in os.walk(input_folder):
        file_count += len(filenames)
        for filename in regex_filter(filenames, CUSTOM_SPRITE_PATTERN):
            head, body = os.path.splitext(filename)[0].split(".", 1)
            if int(head) > MAX_ID or int(body) > MAX_ID:
                continue
            sprite_count += 1
            sprite_path = os.path.join(root, filename)
            folder = os.path.join(output_folder, head)
            if head not in existing_folders:
                os.makedirs(folder, exist_ok=True)
                existing_folders.add(head)
            shutil.copy2(sprite_path, folder)
            if verbose:
                print(f"[{str(sprite_count).zfill(6)}/{str(file_count).zfill(6)}] {sprite_path}")

    elapsed_time = time.perf_counter() - start_time
    print(f"Processed {sprite_count} custom sprites (out of {file_count} files) in {elapsed_time:.2f} seconds")


def save_diff() -> None:
    start_time = time.perf_counter()

    autogen_folder_old = r"D:\Discord\PokeFusion\pokefusion\assets\fusions\autogen"
    autogen_folder_new = r"D:\Discord\PokeFusion\pokefusion\tools\fusions\autogen"
    custom_folder_old = r"D:\Discord\PokeFusion\pokefusion\assets\fusions\custom"
    custom_folder_new = r"D:\Discord\PokeFusion\pokefusion\tools\fusions\custom"

    base_output = os.path.join("output")
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


def run():
    start_time = time.perf_counter()
    import_autogen_sprites(verbose=False)
    import_custom_sprites(verbose=False)
    save_diff()
    elapsed_time = time.perf_counter() - start_time
    print(f"Total runtime is {elapsed_time:.2f} seconds")
    print()
    print("Don't forget to update fusionapi.PREVIOUS_MAX_ID if necessary (new sprites)")


if __name__ == "__main__":
    run()
