from pathlib import Path


class AssetPaths:
    ASSETS_DIR = Path("pokefusion", "assets")
    EGGS_DIR = ASSETS_DIR / "eggs"
    DEFAULT_EGG_PATH = EGGS_DIR / "000.png"
    FUSIONS_DIR = ASSETS_DIR / "fusions"
    FUSIONS_AUTOGEN_DIR = FUSIONS_DIR / "autogen"
    FUSIONS_CUSTOM_DIR = FUSIONS_DIR / "custom"
    MISC_DIR = ASSETS_DIR / "misc"
    SPRITES_DIR = ASSETS_DIR / "sprites"
    SPRITES_BASE_DIR = SPRITES_DIR / "base"
    SPRITES_SHINY_DIR = SPRITES_DIR / "shiny"
    AVATARS_DIR = ASSETS_DIR / "avatars"
