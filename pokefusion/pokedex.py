import glob
import json
import random
from enum import Enum
from os.path import basename, join, splitext

import utils


class Language(Enum):
    FR = "fr"
    EN = "en"
    DE = "de"
    DEFAULT = EN


class Pokedex:
    DATA_DIR = "data"
    FILE_PATTERN = "pokedex_*.json"
    RANDOM_QUERY = {"random", "rand", "r", "?", "x", "."}

    def __init__(self):
        self.data = {}
        for path in glob.glob(join(Pokedex.DATA_DIR, Pokedex.FILE_PATTERN)):
            lang = Language(splitext(basename(path))[0].split("_")[-1])  # pokedex_{lang}.json
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
                normalized = {key: utils.normalize(value) for key, value in list(raw.items())}
                self.data[lang] = utils.TwoWayDict(normalized)

    def resolve(self, query, lang):
        """Returns (id, name)"""
        if query.isdigit():
            return query, self.data[lang][query]

        if query in Pokedex.RANDOM_QUERY:
            r = str(random.randint(0, 151))
            return r, self.data[lang][r]
        else:
            n = utils.normalize(query)
            return self.data[lang][n], n
