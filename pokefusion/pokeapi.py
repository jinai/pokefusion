import asyncio
import random
import re
from dataclasses import dataclass
from typing import Any, TypedDict, cast

import aiohttp

from pokefusion.enums import Language

type LocalizedNames = dict[Language, str]
type LocalizedDescriptions = dict[Language, tuple[str, ...]]


class Resource(TypedDict):
    name: str
    url: str


class NameEntry(TypedDict):
    name: str
    language: Resource


class FlavorTextEntry(TypedDict):
    flavor_text: str
    language: Resource


class TypeSlot(TypedDict):
    slot: int
    type: Resource


class PokemonResponse(TypedDict):
    types: list[TypeSlot]


class PokemonSpeciesResponse(TypedDict):
    names: list[NameEntry]
    flavor_text_entries: list[FlavorTextEntry]
    generation: Resource


class TypeResponse(TypedDict):
    names: list[NameEntry]


@dataclass(frozen=True, slots=True)
class PokeApiResult:
    dex_id: int
    names: LocalizedNames
    descriptions: LocalizedDescriptions
    types: tuple[LocalizedNames, ...]
    generation: int

    def get_name(self, lang: Language) -> str:
        return self.names.get(lang, self.names[Language.EN])

    def get_types(self, lang: Language) -> tuple[str, ...]:
        return tuple(names.get(lang, names[Language.EN]) for names in self.types)

    def get_random_description(self, lang: Language) -> str:
        descriptions = self.descriptions.get(lang)

        if not descriptions:
            descriptions = self.descriptions[Language.EN]
            lang = Language.EN

        description = random.choice(descriptions)
        name = self.get_name(lang)

        return re.sub(
            re.escape(name),
            PokeApiClient.REDACTED_STRING,
            description,
            flags=re.IGNORECASE,
        )


class PokeApiClient:
    MIN_ID = 1
    MAX_ID = 1025
    REDACTED_STRING = "███████"

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._session: aiohttp.ClientSession | None = None
        self._type_cache: dict[int, LocalizedNames] = {}

    async def start(self) -> None:
        if self._session is not None:
            raise RuntimeError("PokéAPI client is already started")

        self._session = aiohttp.ClientSession()

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None

    async def get_random_pokemon(self) -> PokeApiResult:
        dex_id = random.randint(self.MIN_ID, self.MAX_ID)
        return await self.get_pokemon(dex_id)

    async def get_pokemon(self, dex_id: int) -> PokeApiResult:
        species_data, pokemon_data = await asyncio.gather(
            self._get_json(f"pokemon-species/{dex_id}/"),
            self._get_json(f"pokemon/{dex_id}/"),
        )

        species = cast(PokemonSpeciesResponse, species_data)
        pokemon = cast(PokemonResponse, pokemon_data)

        type_ids = [
            self._parse_resource_id(slot["type"]["url"])
            for slot in sorted(pokemon["types"], key=lambda slot: slot["slot"])
        ]

        types = await asyncio.gather(*(self._get_type_names(type_id) for type_id in type_ids))

        return PokeApiResult(
            dex_id=dex_id,
            names=self._parse_names(species["names"]),
            descriptions=self._parse_descriptions(species["flavor_text_entries"]),
            types=tuple(types),
            generation=self._parse_resource_id(species["generation"]["url"]),
        )

    async def _get_json(self, path: str) -> dict[str, Any]:
        if self._session is None:
            raise RuntimeError("PokéAPI client is not started")

        url = f"{self.base_url}/{path.lstrip('/')}"

        async with self._session.get(url) as response:
            response.raise_for_status()
            return await response.json()

    async def _get_type_names(self, type_id: int) -> LocalizedNames:
        if type_id not in self._type_cache:
            data = cast(TypeResponse, await self._get_json(f"type/{type_id}/"))
            self._type_cache[type_id] = self._parse_names(data["names"])

        return self._type_cache[type_id]

    @staticmethod
    def _parse_names(entries: list[NameEntry]) -> LocalizedNames:
        names: LocalizedNames = {}

        for entry in entries:
            try:
                lang = Language(entry["language"]["name"])
            except ValueError:
                continue

            names[lang] = entry["name"]

        return names

    @staticmethod
    def _parse_descriptions(entries: list[FlavorTextEntry]) -> LocalizedDescriptions:
        descriptions: dict[Language, list[str]] = {}

        for entry in entries:
            try:
                lang = Language(entry["language"]["name"])
            except ValueError:
                continue

            text = re.sub(
                r"\s+",
                " ",
                entry["flavor_text"],
            ).strip()

            descriptions.setdefault(lang, []).append(text)

        return {
            lang: tuple(values)
            for lang, values in descriptions.items()
        }

    @staticmethod
    def _parse_resource_id(url: str) -> int:
        return int(url.rstrip("/").rsplit("/", 1)[1])
