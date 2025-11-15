import random
from dataclasses import dataclass, field

import aiopoke

from pokefusion import utils


def get_names(base_name) -> tuple[str, ...]:
    return base_name, base_name.lower(), base_name.upper(), base_name.title(), base_name.capitalize()


class PokeApiClient:
    MIN_ID = 1
    MAX_ID = 1025
    REDACTED_STRING = "███████"

    @staticmethod
    async def get_random_pokemon():
        async with aiopoke.AiopokeClient() as client:
            dex_id: int = random.randint(PokeApiClient.MIN_ID, PokeApiClient.MAX_ID)
            species = await client.get_pokemon_species(dex_id)
            pokemon = await client.get_pokemon(dex_id)
            generation = (await species.generation.fetch()).id
            type_1 = await pokemon.types[0].type.fetch()
            type_2 = await pokemon.types[1].type.fetch() if len(pokemon.types) > 1 else None
            name_fr, name_en = "", ""
            desc_fr, desc_en = [], []
            type_1_name, type_2_name = "", ""
            for name in species.names:
                if name.language.name == "fr":
                    name_fr = name.name
                elif name.language.name == "en":
                    name_en = name.name
            for desc in species.flavor_text_entries:
                if desc.language.name == "fr":
                    desc_fr.append(desc.flavor_text)
                elif desc.language.name == "en":
                    desc_en.append(desc.flavor_text)
            for name in type_1.names:
                if name.language.name == "fr":
                    type_1_name = name.name
            if type_2 is not None:
                for name in type_2.names:
                    if name.language.name == "fr":
                        type_2_name = name.name

            poke = PokeApiResult(dex_id, name_fr, name_en, desc_fr, desc_en, type_1_name, type_2_name, generation)
            return poke


@dataclass
class PokeApiResult:
    REDACTED_CHAR = "█"

    dex_id: int
    name_fr: str = ""
    name_en: str = ""
    desc_fr: list[str] = field(default_factory=list)
    desc_en: list[str] = field(default_factory=list)
    type_1: str = ""
    type_2: str = ""
    generation: int = 0

    def get_random_desc(self):
        desc = random.choice(self.desc_fr if self.desc_fr else self.desc_en)
        desc = utils.replace_all(desc, {name: PokeApiClient.REDACTED_STRING for name in
                                        get_names(self.name_fr if self.desc_fr else self.name_en)})
        return desc
