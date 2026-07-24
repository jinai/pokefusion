from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import cache
from typing import Any, Self

from .enums import Environment, Language
from .utils import TwoWayDict, normalize

type JsonDict = dict[str, Any]
type RawDex = dict[str, dict[str, str]]
type Dex = dict[str, TwoWayDict[str, str]]


class ConfigManager:
    CONFIG_DIR = os.path.join("pokefusion", "config")
    CONFIG_FILE = "config.json"
    POKEDEX_FILE = "pokedex.json"
    INFINITEDEX_FILE = "infinitedex.json"

    @classmethod
    @cache
    def _load_lookup_dex(cls, filename: str) -> Dex:
        raw = cls.read_json(filename)

        return {
            lang: TwoWayDict({
                key: normalize(value) for key, value in names.items()
            })
            for lang, names in raw.items() if lang in Language
        }

    @classmethod
    def get_lookup_pokedex(cls) -> Dex:
        return cls._load_lookup_dex(cls.POKEDEX_FILE)

    @classmethod
    def get_lookup_infinitedex(cls) -> Dex:
        return cls._load_lookup_dex(cls.INFINITEDEX_FILE)

    @classmethod
    @cache
    def read_json(cls, filename: str) -> JsonDict:
        with open(os.path.join(cls.CONFIG_DIR, filename), "r", encoding="utf-8") as f:
            return json.load(f)

    @classmethod
    def get_bot_config(cls) -> BotConfig:
        return BotConfig.from_dict(cls.read_json(cls.CONFIG_FILE))


@dataclass
class BotConfig:
    env: Environment
    owner_id: int
    default_prefix: str
    token: str
    init_cogs: list[str]
    dbconf: DatabaseConfig
    maintenance: bool
    block_dms: bool
    main_color: str

    @classmethod
    def from_dict(cls, cfg: JsonDict) -> Self:
        return cls(
            env=cfg["environment"],
            owner_id=cfg["owner_id"],
            default_prefix=cfg["default_prefix"],
            token=cfg["token"],
            init_cogs=cfg["init_cogs"],
            dbconf=DatabaseConfig.from_dict(cfg["database"]),
            maintenance=cfg["maintenance"],
            block_dms=cfg["block_dms"],
            main_color=cfg["main_color"]
        )


@dataclass
class DatabaseConfig:
    path: str
    pragmas: JsonDict

    @classmethod
    def from_dict(cls, cfg: JsonDict) -> Self:
        return cls(
            path=os.path.abspath(cfg["path"]),
            pragmas=cfg.get("pragmas", {})
        )
