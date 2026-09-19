from functools import partial
from multiprocessing import Pool, cpu_count
from pathlib import Path

from PIL import Image
from PIL.Image import Resampling
from tqdm import tqdm

from pokefusion.fusionapi import FusionClient
from pokefusion.types import StrPath

SPRITESHEET_ROWS = 58
SPRITESHEET_COLUMNS = 10
SPRITE_WIDTH = 96
SPRITE_HEIGHT = 96
SPRITE_SCALE = 2


def split_spritesheets(input_dir: StrPath, output_dir: StrPath) -> None:
    spritesheet_paths = sorted(Path(input_dir).glob("*.png"))
    worker_count = cpu_count()

    worker_label = "worker" if worker_count == 1 else "workers"
    desc = f"Splitting spritesheets ({worker_count} {worker_label})"
    split = partial(_split_spritesheet, output_dir=output_dir)

    with Pool(worker_count) as pool:
        results = pool.imap_unordered(split, spritesheet_paths)

        for _ in tqdm(results, total=len(spritesheet_paths), desc=desc):
            pass


def _split_spritesheet(spritesheet_path: StrPath, output_dir: StrPath) -> None:
    with Image.open(spritesheet_path) as sheet:
        if SPRITE_SCALE > 1:
            sheet = sheet.resize(
                size=(
                    sheet.width * SPRITE_SCALE,
                    sheet.height * SPRITE_SCALE,
                ),
                resample=Resampling.NEAREST,
            )

        sheet_name = Path(spritesheet_path).stem
        sheet_output_dir = Path(output_dir) / sheet_name
        sheet_output_dir.mkdir(parents=True, exist_ok=True)

        sprite_width = SPRITE_WIDTH * SPRITE_SCALE
        sprite_height = SPRITE_HEIGHT * SPRITE_SCALE
        sheet_capacity = SPRITESHEET_ROWS * SPRITESHEET_COLUMNS - 1
        max_sprite_id = min(FusionClient.MAX_ID, sheet_capacity)

        for sprite_id in range(1, max_sprite_id + 1):
            row, column = divmod(sprite_id, SPRITESHEET_COLUMNS)
            box = (
                column * sprite_width,
                row * sprite_height,
                (column + 1) * sprite_width,
                (row + 1) * sprite_height,
            )

            output_path = sheet_output_dir / f"{sheet_name}.{sprite_id}.png"
            sprite = sheet.crop(box)
            sprite.save(output_path)
