import csv
import io
import json
import logging
import urllib.request
from collections import defaultdict

from pokefusion.configmanager import ConfigManager

type CsvRow = dict[str, str | None]

logger = logging.getLogger(__name__)

BASE_URL = "https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/"

LANGUAGES_URL = BASE_URL + "languages.csv"
SPECIES_NAMES_URL = BASE_URL + "pokemon_species_names.csv"

CHARACTER_REPLACEMENTS = {
    "♀": "F",
    "♂": "M",
    "’": "'"
}


def fetch_csv(url: str) -> list[CsvRow]:
    with urllib.request.urlopen(url, timeout=5) as response:
        raw = response.read().decode("utf-8")
        return list(csv.DictReader(io.StringIO(raw)))


def clean_name(name: str) -> str:
    for old, new in CHARACTER_REPLACEMENTS.items():
        name = name.replace(old, new)
    return name


def build_language_map(languages_rows):
    return {row["id"]: row["identifier"].replace("-", "_") for row in languages_rows}


def build_pokedex(species_names_rows, language_map):
    pokedex = defaultdict(dict)
    for row in species_names_rows:
        species_id = int(row["pokemon_species_id"])
        lang_key = language_map[row["local_language_id"]]
        pokedex[lang_key][str(species_id)] = clean_name(row["name"])
    return pokedex


def generate_pokedex():
    out_file = ConfigManager.CONFIG_DIR / ConfigManager.POKEDEX_FILE

    logger.info(f"Fetching languages")
    languages_rows = fetch_csv(LANGUAGES_URL)

    logger.info(f"Fetching species names")
    species_names_rows = fetch_csv(SPECIES_NAMES_URL)

    language_map = build_language_map(languages_rows)
    pokedex = build_pokedex(species_names_rows, language_map)

    ordered = {
        lang_key: dict(sorted(pokedex[lang_key].items(), key=lambda item: int(item[0])))
        for lang_key in sorted(pokedex)
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(ordered, f, ensure_ascii=False, indent=4)

    logger.info(f"Wrote {len(ordered["en"])} entries in {len(ordered)} languages to {out_file}")
