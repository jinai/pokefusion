import os
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
MAX_WORKERS = 1


def process_dir(input_dir: StrPath, output_dir: StrPath):
    spritesheets = [
        Path(input_dir, sheet)
        for sheet in next(os.walk(input_dir))[2]
    ]

    cores = cpu_count()
    desc = f"Splitting spritesheets (on {cores} cores)"
    with Pool(cores) as pool:
        func = partial(split_spritesheet, output_dir=output_dir)
        list(tqdm(pool.imap_unordered(func, spritesheets), total=len(spritesheets), desc=desc))  # force iter


def split_spritesheet(path: StrPath, output_dir: StrPath):
    with Image.open(path) as sheet:
        if SPRITE_SCALE > 1:
            sheet = sheet.resize(
                size=(
                    sheet.width * SPRITE_SCALE,
                    sheet.height * SPRITE_SCALE
                ),
                resample=Resampling.NEAREST
            )

        boxes = [
            (
                col * SPRITE_WIDTH * SPRITE_SCALE,
                row * SPRITE_HEIGHT * SPRITE_SCALE,
                (col + 1) * SPRITE_WIDTH * SPRITE_SCALE,
                (row + 1) * SPRITE_HEIGHT * SPRITE_SCALE,
            )
            for row in range(SPRITESHEET_ROWS)
            for col in range(SPRITESHEET_COLUMNS)
        ]

        sheet_name = Path(path).stem
        sheet_output_dir = Path(output_dir, sheet_name)
        os.makedirs(sheet_output_dir, exist_ok=True)

        for index, box in enumerate(boxes[1:FusionClient.MAX_ID + 1]):
            output_file = sheet_output_dir / f"{sheet_name}.{index + 1}.png"
            sprite = sheet.crop(box)
            sprite.save(output_file)
