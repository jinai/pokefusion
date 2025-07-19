import os

from discord import Color

from pokefusion import imagelib
from pokefusion.environment import Environment


class AssetManager:
    ASSETS_DIR = os.path.join("pokefusion", "assets")
    EGGS_DIR = os.path.join(ASSETS_DIR, "eggs")
    FUSIONS_DIR = os.path.join(ASSETS_DIR, "fusions")
    FUSIONS_AUTOGEN_DIR = os.path.join(FUSIONS_DIR, "autogen")
    FUSIONS_CUSTOM_DIR = os.path.join(FUSIONS_DIR, "custom")
    MISC_DIR = os.path.join(ASSETS_DIR, "misc")
    SPRITES_DIR = os.path.join(ASSETS_DIR, "sprites")
    SPRITES_BASE_DIR = os.path.join(SPRITES_DIR, "base")
    SPRITES_SHINY_DIR = os.path.join(SPRITES_DIR, "shiny")

    @classmethod
    def get_avatar_path(cls, env: Environment) -> str:
        return os.path.join(cls.ASSETS_DIR, f"avatar.{env}.png")

    @classmethod
    def get_default_egg_path(cls) -> str:
        return os.path.join(cls.EGGS_DIR, "000.png")

    @staticmethod
    def get_asset_color(path: str) -> Color:
        rgb = imagelib.get_dominant_color(path, normalize=True)
        return Color.from_rgb(*rgb)
