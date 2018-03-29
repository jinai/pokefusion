import os
from io import BytesIO

import requests
import unidecode
from PIL import Image


def get_token():
    token = os.getenv("POKEFUSION_TOKEN")
    if token:
        return token
    with open("data/.token", "r", encoding="utf-8") as f:
        return f.read().strip()


def get_changelog():
    path = "../changelog.txt"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def normalize(string, func=lambda s: s.lower().replace(" ", "")):
    return unidecode.unidecode(func(string))


def get_dominant_color(url):
    r = requests.get(url)
    if r.status_code == 200:
        im = Image.open(BytesIO(r.content))
        w, h = im.size
        colors = im.convert("RGBA").getcolors(w * h)
        dominant = colors[0]
        for count, color in colors:
            cmax, cmin = max(color[:3]), min(color[:3])
            lightness = (cmax + cmin) / 2
            if lightness > 51 and count > dominant[0]:
                # Discard transparent & dark pixels (lightness < 20%)
                dominant = (count, color)
        r, g, b, a = dominant[1]
        return (r << 16) | (g << 8) | b


def yes(s):
    return s.lower() in ("yes", "y")


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
