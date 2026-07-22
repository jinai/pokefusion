import json
import logging
import os

from pokefusion.configmanager import ConfigManager

logger = logging.getLogger(__name__)

OVERRIDES = {
    "430": {"fr": "Plumeline-Flamenco", "de": "Choreogel-Flamenco"},
    "431": {"fr": "Plumeline-Pom-Pom", "de": "Choreogel-Cheerleading"},
    "432": {"fr": "Plumeline-Hula", "de": "Choreogel-Hula"},
    "433": {"fr": "Plumeline-Buyō", "de": "Choreogel-Buyo"},

    "464": {"fr": "Lougaroc-Diurne", "de": "Wolwerock-Tag"},
    "465": {"fr": "Lougaroc-Nocturne", "de": "Wolwerock-Nacht"},

    "466": {"fr": "Meloetta-Chant", "de": "Meloetta-Gesangs"},
    "467": {"fr": "Meloetta-Danse", "de": "Meloetta-Tanz"},

    "498": {"fr": "Météno-Météore", "de": "Meteno-Meteor"},
    "499": {"fr": "Météno-Noyau", "de": "Meteno-Kern"},

    "553": {"fr": "Morphéo-Soleil", "de": "Formeo-Sonnen"},
    "554": {"fr": "Morphéo-Pluie", "de": "Formeo-Regen"},
    "555": {"fr": "Morphéo-Neige", "de": "Formeo-Schnee"},

    "573": {"fr": "Sancoki-Est", "de": "Schalellos-Ost"},
    "574": {"fr": "Tritosor-Est", "de": "Gastrodon-Ost"},
    "575": {"fr": "Sancoki-Ouest", "de": "Schalellos-West"},
    "576": {"fr": "Tritosor-Ouest", "de": "Gastrodon-West"},
}


def build_reverse_english_index(pokedex):
    return {name: species_id for species_id, name in pokedex["en"].items()}


def resolve_species(name, reverse_en):
    if name in reverse_en:
        return reverse_en[name], ""

    if "-" in name:
        base, _, form_part = name.partition("-")
        if base in reverse_en:
            return reverse_en[base], "-" + form_part

    return None, None


def build_infinitedex(pokedex, infinitedex_en):
    reverse_en = build_reverse_english_index(pokedex)
    languages = sorted(pokedex.keys())

    infinitedex = {lang: {} for lang in languages}
    unmatched = []

    for infinitedex_id, english_name in infinitedex_en.items():
        species_id, suffix = resolve_species(english_name, reverse_en)

        if species_id is not None:
            names = {lang: pokedex[lang][species_id] + suffix for lang in languages}
        else:
            unmatched.append((infinitedex_id, english_name))
            names = {lang: english_name for lang in languages}

        for lang, override_name in OVERRIDES.get(infinitedex_id, {}).items():
            names[lang] = override_name

        for lang in languages:
            infinitedex[lang][infinitedex_id] = names[lang]

    return infinitedex, unmatched


def generate_infinitedex():
    pokedex = ConfigManager.read_json("pokedex.json")
    infinitedex_en = ConfigManager.read_json("infinitedex_en.json")
    out_file = os.path.join(ConfigManager.CONFIG_DIR, "infinitedex.json")

    infinitedex, unmatched = build_infinitedex(pokedex, infinitedex_en)

    if unmatched:
        logger.warning(f"{len(unmatched)} entries couldn't be matched and were defaulted to English:")
        for infinitedex_id, name in unmatched:
            logger.warning(f"  - ID {infinitedex_id}: {name}")

    ordered = {
        lang: dict(sorted(infinitedex[lang].items(), key=lambda kv: int(kv[0])))
        for lang in sorted(infinitedex)
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(ordered, f, ensure_ascii=False, indent=4)

    logger.info(f"Wrote {len(ordered["en"])} entries in {len(ordered)} languages to {out_file}")
