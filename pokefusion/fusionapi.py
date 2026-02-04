from __future__ import annotations

import os
import random
from enum import StrEnum, auto
from os.path import basename, splitext
from typing import Self

from fuzzywuzzy import fuzz, process

from . import utils
from .assetmanager import AssetManager
from .configmanager import ConfigManager
from .utils import TwoWayDict, normalize

temp = ConfigManager.read_json("custom_diff_added.json")
CUSTOM_DIFF_ADDED: dict[int, list[int]] = {int(key): value for key, value in temp.items()}
temp = ConfigManager.read_json("custom_fusions.json")
CUSTOM_FUSIONS: dict[int, list[int]] = {int(key): value for key, value in temp.items()}


# noinspection PyEnum
class Language(StrEnum):
    FR = auto()
    EN = auto()
    DE = auto()
    DEFAULT = FR


class LookupResult:
    def __init__(self, client: BaseClient, lang: Language):
        self.client = client
        self.lang = lang
        self.dex_id: int | None = None
        self.species: str | None = None
        self.guess: str | None = None
        self.guess_score: int | None = None
        self.bad_query: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.dex_id is not None and self.species is not None and self.guess is None

    @property
    def failed(self) -> bool:
        return not self.succeeded

    def succeed(self, dex_id: int, species: str) -> Self:
        self.dex_id = dex_id
        self.species = species
        return self

    def fail(self, bad_query: str) -> Self:
        self.bad_query = bad_query
        if not bad_query.isdigit():
            choices = self.client.get_species(self.lang)
            self.guess, self.guess_score = process.extractOne(bad_query, choices, score_cutoff=0, scorer=fuzz.ratio)
        return self

    def __repr__(self) -> str:
        if self.succeeded:
            return f"<LookupResult dex_id={self.dex_id}, species={self.species}, lang={self.lang}>"
        else:
            return f"<LookupResult bad_query={self.bad_query}, guess={self.guess}, guess_score={self.guess_score} lang={self.lang}>"


class FusionResult:
    def __init__(self, head: LookupResult, body: LookupResult, head_query: str, body_query: str):
        self.head = head
        self.body = body
        self.head_query = head_query
        self.body_query = body_query

    def swap(self) -> Self:
        return FusionResult(head=self.body, body=self.head, head_query=self.body_query, body_query=self.head_query)

    @property
    def succeeded(self) -> bool:
        return self.head.succeeded and self.body.succeeded

    @property
    def failed(self) -> bool:
        return not self.succeeded

    @property
    def is_new(self) -> bool:
        new_autogen = self.head.dex_id > FusionClient.PREVIOUS_MAX_ID or self.body.dex_id > FusionClient.PREVIOUS_MAX_ID
        return new_autogen or self.body.dex_id in CUSTOM_DIFF_ADDED.get(self.head.dex_id, [])

    @property
    def is_custom(self) -> bool:
        filename = f"{self.head.dex_id}.{self.body.dex_id}.png"
        custom = os.path.join(AssetManager.FUSIONS_CUSTOM_DIR, str(self.head.dex_id), filename)
        return os.path.isfile(custom)

    @property
    def path(self) -> str | None:
        if self.failed:
            return None

        filename = f"{self.head.dex_id}.{self.body.dex_id}.png"
        autogen = os.path.join(AssetManager.FUSIONS_AUTOGEN_DIR, str(self.head.dex_id), filename)
        custom = os.path.join(AssetManager.FUSIONS_CUSTOM_DIR, str(self.head.dex_id), filename)

        if os.path.isfile(custom):
            return custom
        else:
            return autogen

    @property
    def egg_path(self) -> str | None:
        if self.failed:
            return None

        filename = f"{self.head.dex_id}.png"
        path = os.path.join(AssetManager.EGGS_DIR, filename)

        if os.path.isfile(path):
            return path
        else:
            return AssetManager.get_default_egg_path()

    def __repr__(self) -> str:
        return f"<FusionResult head={self.head}, body={self.body}, head_query={self.head_query}, body_query={self.body_query}>"


class BaseClient:
    RANDOM_QUERIES = {"?", "."}
    MIN_ID = None
    MAX_ID = None

    def __init__(self, config_files: list[str]):
        self.data: dict[Language, dict[str, str]] = {}
        for path in config_files:
            lang = Language(splitext(filename := basename(path))[0].split("_")[-1])  # conf_{lang}.json
            raw = ConfigManager.read_json(filename)
            normalized = {key: normalize(value) for key, value in raw.items()}
            self.data[lang] = TwoWayDict(normalized)

    @classmethod
    def get_random_id(cls):
        return random.randint(cls.MIN_ID, cls.MAX_ID)

    def lookup(self, query: str, lang: Language = Language.DEFAULT) -> LookupResult:
        result = LookupResult(self, lang)

        # Example: client.lookup("122")
        if query.isdigit():
            if query in self.data[lang]:
                return result.succeed(int(query), self.data[lang][query])
            else:
                return result.fail(query)

        # Example: client.lookup("?")
        elif query in BaseClient.RANDOM_QUERIES:
            rand = self.get_random_id()
            return result.succeed(rand, self.data[lang][str(rand)])

        # Example: client.lookup("mr. mime")
        else:
            query = utils.normalize(query)
            if query in self.data[lang]:
                return result.succeed(int(self.data[lang][query]), query)
            else:
                return result.fail(query)

    def get_species(self, lang: Language = Language.DEFAULT) -> list[str]:
        return [k for k in self.data[lang] if not k.isdigit()]


class FusionClient(BaseClient):
    MIN_ID = 1
    MAX_ID = 501
    PREVIOUS_MAX_ID = 501  # TODO: update when adding sprites

    def __init__(self):
        super().__init__(ConfigManager.get_infinitedex())

    def fusion(self, head: str = "?", body: str = "?", lang: Language = Language.DEFAULT,
               custom_only: bool = False) -> FusionResult:
        head_result = self.lookup(head, lang)

        if custom_only and head_result.succeeded:
            body = str(random.choice(FusionClient.get_custom_fusions(head=head_result.dex_id)))

        body_result = self.lookup(body, lang)
        return FusionResult(head_result, body_result, head, body)

    def totem(self, seed: int | None, lang: Language = Language.DEFAULT) -> FusionResult:
        rand = random.Random(seed)
        head = rand.randint(FusionClient.MIN_ID, FusionClient.MAX_ID)
        body = rand.choice(FusionClient.get_custom_fusions(head=head))  # Only custom fusions for Totems
        return self.fusion(head=str(head), body=str(body), lang=lang)

    @staticmethod
    def get_custom_fusions(head: int = None, body: int = None) -> list[int]:
        fusions: list[int] = []
        if head is not None and head in CUSTOM_FUSIONS:
            fusions = CUSTOM_FUSIONS[head]
        elif body is not None:
            for key in CUSTOM_FUSIONS:
                if body in CUSTOM_FUSIONS[key]:
                    fusions.append(int(key))
        return fusions


class SpriteClient(BaseClient):
    MIN_ID = 1
    MAX_ID = 898

    def __init__(self):
        super().__init__(ConfigManager.get_pokedex())

    def get_sprite(self, query: str, lang: Language = Language.DEFAULT) -> Sprite:
        return Sprite(self.lookup(query, lang))


class Sprite:
    def __init__(self, lookup: LookupResult):
        self.lookup = lookup

    @property
    def found(self) -> bool:
        return self.lookup.succeeded

    @property
    def not_found(self) -> bool:
        return not self.found

    @property
    def path(self) -> str | None:
        if self.not_found:
            return None

        filename = f"{self.lookup.dex_id}.png"
        path = os.path.join(AssetManager.SPRITES_BASE_DIR, filename)
        return path

    @property
    def path_shiny(self) -> str | None:
        if self.not_found:
            return None

        filename = f"{self.lookup.dex_id}.png"
        path = os.path.join(AssetManager.SPRITES_SHINY_DIR, filename)
        return path

    def __repr__(self) -> str:
        return f"<Sprite dex_id={self.lookup.dex_id}, species={self.lookup.species}>"
