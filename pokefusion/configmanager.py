from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import time
from functools import cache
from typing import Any, Self

from .enums import Environment, Language
from .types import Dex
from .utils import TwoWayDict, normalize

type JsonDict = dict[str, Any]


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


@dataclass(frozen=True, slots=True)
class BotConfig:
    environment: Environment
    owner_id: int
    default_prefix: str
    token: str = field(repr=False)
    extensions: tuple[str, ...]
    database: DatabaseConfig
    logging: LoggingConfig
    maintenance: bool
    block_dms: bool
    main_color: str | None = None

    @classmethod
    def from_dict(cls, cfg: JsonDict) -> Self:
        return cls(
            environment=Environment(cfg["environment"]),
            owner_id=int(cfg["owner_id"]),
            default_prefix=cfg["default_prefix"],
            token=cfg["token"],
            extensions=tuple(cfg.get("extensions", ())),
            database=DatabaseConfig.from_dict(cfg["database"]),
            logging=LoggingConfig.from_dict(cfg["logging"]),
            maintenance=cfg["maintenance"],
            block_dms=cfg["block_dms"],
            main_color=cfg.get("main_color")
        )


@dataclass(frozen=True, slots=True)
class DatabaseConfig:
    path: str
    pragmas: JsonDict

    @classmethod
    def from_dict(cls, cfg: JsonDict) -> Self:
        return cls(
            path=os.path.abspath(cfg["path"]),
            pragmas=cfg.get("pragmas", {})
        )


@dataclass(frozen=True, slots=True)
class LoggingConfig:
    path: str
    encoding: str
    errors: str
    level: int
    timezone: str
    date_format: str
    file_format: str
    console_format: str
    rotation: LoggingRotationConfig
    colors: LoggingColorConfig

    @classmethod
    def from_dict(cls, cfg: JsonDict) -> Self:
        level_name = cfg["level"].upper()
        level = getattr(logging, level_name)

        if not isinstance(level, int):
            raise ValueError(f"Invalid logging level: {level_name!r}")

        return cls(
            path=os.path.abspath(cfg["path"]),
            encoding=cfg["encoding"],
            errors=cfg["errors"],
            level=level,
            timezone=cfg["timezone"],
            date_format=cfg["date_format"],
            file_format=cfg["file_format"],
            console_format=cfg["console_format"],
            rotation=LoggingRotationConfig.from_dict(cfg["rotation"]),
            colors=LoggingColorConfig.from_dict(cfg["colors"]),
        )


@dataclass(frozen=True, slots=True)
class LoggingRotationConfig:
    when: str
    interval: int
    backup_count: int
    delay: bool
    utc: bool
    at_time: time | None

    @classmethod
    def from_dict(cls, cfg: JsonDict) -> Self:
        at_time = cfg["at_time"]

        return cls(
            when=cfg["when"],
            interval=cfg["interval"],
            backup_count=cfg["backup_count"],
            delay=cfg["delay"],
            utc=cfg["utc"],
            at_time=time.fromisoformat(str(at_time)) if at_time is not None else None
        )


@dataclass(frozen=True, slots=True)
class LoggingColorConfig:
    debug: str
    info: str
    warning: str
    error: str
    critical: str
    time: str
    name: str
    reset: str

    @classmethod
    def from_dict(cls, cfg: JsonDict) -> Self:
        return cls(
            debug=cfg["debug"],
            info=cfg["info"],
            warning=cfg["warning"],
            error=cfg["error"],
            critical=cfg["critical"],
            time=cfg["time"],
            name=cfg["name"],
            reset=cfg["reset"]
        )
