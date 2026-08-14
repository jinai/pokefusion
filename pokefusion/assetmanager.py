import os


class AssetManager:
    ASSETS_DIR = os.path.join("pokefusion", "assets")
    EGGS_DIR = os.path.join(ASSETS_DIR, "eggs")
    DEFAULT_EGG_PATH = os.path.join(EGGS_DIR, "000.png")
    FUSIONS_DIR = os.path.join(ASSETS_DIR, "fusions")
    FUSIONS_AUTOGEN_DIR = os.path.join(FUSIONS_DIR, "autogen")
    FUSIONS_CUSTOM_DIR = os.path.join(FUSIONS_DIR, "custom")
    MISC_DIR = os.path.join(ASSETS_DIR, "misc")
    SPRITES_DIR = os.path.join(ASSETS_DIR, "sprites")
    SPRITES_BASE_DIR = os.path.join(SPRITES_DIR, "base")
    SPRITES_SHINY_DIR = os.path.join(SPRITES_DIR, "shiny")
    AVATARS_DIR = os.path.join(ASSETS_DIR, "avatars")
