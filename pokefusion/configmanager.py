from __future__ import annotations

import glob
import json
import os
from dataclasses import dataclass
from typing import Any, Self

from .environment import Environment

type JsonDict = dict[str, Any]


class ConfigManager:
    CONFIG_DIR = os.path.join("pokefusion", "config")
    INFINITEDEX_PATTERN = "infinitedex_*.json"
    POKEDEX_PATTERN = "pokedex_*.json"

    @classmethod
    def get_infinitedex(cls) -> list[str]:
        return glob.glob(os.path.join(cls.CONFIG_DIR, cls.INFINITEDEX_PATTERN))

    @classmethod
    def get_pokedex(cls) -> list[str]:
        return glob.glob(os.path.join(cls.CONFIG_DIR, cls.POKEDEX_PATTERN))

    @classmethod
    def read_json(cls, filename: str) -> JsonDict:
        with open(os.path.join(cls.CONFIG_DIR, filename), "r", encoding="utf-8") as f:
            return json.load(f)

    @classmethod
    def get_bot_config(cls, env: Environment) -> BotConfig:
        return BotConfig.from_dict(cls.read_json(f"config.{env}.json"), env)


@dataclass
class BotConfig:
    env: Environment
    owner_id: int
    default_prefix: str
    token: str
    init_cogs: list[str]
    database: DatabaseConfig
    maintenance: bool
    block_dms: bool

    @classmethod
    def from_dict(cls, obj: JsonDict, env: Environment) -> Self:
        _owner_id = int(obj.get("owner_id"))
        _default_prefix = str(obj.get("default_prefix"))
        _token = str(obj.get("token"))
        _init_cogs = obj.get("init_cogs")
        _database = DatabaseConfig.from_dict(obj.get("database"))
        _maintenance = obj.get("maintenance")
        _block_dms = obj.get("block_dms")

        return cls(env, _owner_id, _default_prefix, _token, _init_cogs, _database, _maintenance, _block_dms)


@dataclass
class DatabaseConfig:
    path: str
    pragmas: JsonDict

    @classmethod
    def from_dict(cls, obj: JsonDict) -> Self:
        _path = os.path.abspath(obj.get("path"))
        _pragmas = obj.get("pragmas")
        return cls(_path, _pragmas)
