import os
import random
from io import BytesIO

import colorthief
import requests
import unidecode


def get_token():
    token = os.getenv("POKEFUSION_TOKEN")
    if token:
        return token
    with open("data/.token", "r", encoding="utf-8") as f:
        return f.read().strip()


def normalize(s):
    return unidecode.unidecode(s.lower())


def resolve(query, pokedex):
    if query.isdigit():
        return query, pokedex[query]

    if query in ("random", "rand", "r", "?", "x"):
        r = str(random.randint(0, 151))
        return r, pokedex[r]
    else:
        n = normalize(query)
        return pokedex[n], n


def rgb_to_int(rgb):
    r, g, b = rgb
    return (r << 16) + (g << 8) + b


def get_dominant_color(url):
    r = requests.get(url)
    if r.status_code == 200:
        cf = colorthief.ColorThief(BytesIO(r.content))
        return rgb_to_int(cf.get_color(quality=1))


def get_changelog():
    path = "../changelog.txt"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


class TwoWayDict(dict):
    def __init__(self, seq=None, **kwargs):
        if seq is None:
            super().__init__(**kwargs)
        else:
            super().__init__(seq, **kwargs)
            for k, v in seq.items(): dict.__setitem__(self, v, k)
        for k, v in kwargs.items(): dict.__setitem__(self, v, k)

    def __setitem__(self, key, value):
        if key in self:
            del self[key]
        if value in self:
            del self[value]
        dict.__setitem__(self, key, value)
        dict.__setitem__(self, value, key)

    def __delitem__(self, key):
        dict.__delitem__(self, self[key])
        dict.__delitem__(self, key)

    def __len__(self):
        return dict.__len__(self) // 2
