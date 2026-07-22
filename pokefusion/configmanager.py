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
        return cls._load_lookup_dex("pokedex.json")

    @classmethod
    def get_lookup_infinitedex(cls) -> Dex:
        return cls._load_lookup_dex("infinitedex.json")

    @classmethod
    @cache
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
    dbconf: DatabaseConfig
    maintenance: bool
    block_dms: bool
    main_color: str

    @classmethod
    def from_dict(cls, obj: JsonDict, env: Environment) -> Self:
        _owner_id = int(obj.get("owner_id"))
        _default_prefix = str(obj.get("default_prefix"))
        _token = str(obj.get("token"))
        _init_cogs = obj.get("init_cogs")
        _database = DatabaseConfig.from_dict(obj.get("database"))
        _maintenance = obj.get("maintenance")
        _block_dms = obj.get("block_dms")
        _main_color = obj.get("main_color")

        return cls(env, _owner_id, _default_prefix, _token, _init_cogs, _database, _maintenance, _block_dms,
                   _main_color)


@dataclass
class DatabaseConfig:
    path: str
    pragmas: JsonDict

    @classmethod
    def from_dict(cls, obj: JsonDict) -> Self:
        _path = os.path.abspath(obj.get("path"))
        _pragmas = obj.get("pragmas")
        return cls(_path, _pragmas)
