import asyncio
from typing import Awaitable, Sequence

import aiopoke
from aiopoke.objects.resources import PokemonSpecies


async def main():
    async with aiopoke.AiopokeClient() as client:
        tasks: Sequence[Awaitable[PokemonSpecies]] = [client.get_pokemon_species(x) for x in range(1000, 1002)]
        result: Sequence[PokemonSpecies] = await asyncio.gather(*tasks)
        for pokemon in result:
            for flavor_text in pokemon.flavor_text_entries:
                if flavor_text.language.name in ("fr", "en"):
                    print(flavor_text)


if __name__ == "__main__":
    asyncio.run(main())
