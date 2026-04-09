import json
import shutil
from pathlib import Path


def normalize(s: str):
    return s.lower().replace("é", "e").translate({ord(x): "" for x in UNWANTED_CHARS})


MAIN_DIR = Path("D:\Pokémon 5G Sprites")
SHINY_DIR = MAIN_DIR / "shiny"
PNG_PATTERN = "*.png"
UNWANTED_CHARS = [" ", "-", ".", ":", "'", "(", ")"]
with open("../config/pokedex_en.json", "r", encoding="utf-8") as f:
    raw = json.load(f)
    POKEDEX = {normalize(species): dex_id for dex_id, species in raw.items()}


def remove_garbage(directory: Path):
    paths = [p for p in directory.glob(PNG_PATTERN)]
    garbage = [p for p in paths if p.stem not in POKEDEX]

    for path in garbage:
        print(f"Removing {path}")
        path.unlink()


def rename_to_dexid(directory: Path):
    dest = directory / "renamed"
    dest.mkdir(parents=True, exist_ok=True)
    paths = [p for p in directory.glob(PNG_PATTERN)]

    for old in paths:
        shutil.copy(old, dest)
        new = dest / old.name
        new.rename(dest / f"{POKEDEX[old.stem]}.png")


if __name__ == '__main__':
    remove_garbage(MAIN_DIR)
    remove_garbage(SHINY_DIR)
    rename_to_dexid(MAIN_DIR)
    rename_to_dexid(SHINY_DIR)
