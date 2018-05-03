import base64
import datetime
import io
import os

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
    path = "../changelog.md"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def normalize(string, wrap=lambda s: s.lower().replace(" ", "")):
    return unidecode.unidecode(wrap(string))


def get_dominant_color(f):
    if isinstance(f, str):
        f = open(f, 'rb')
    im = Image.open(f)
    w, h = im.size
    colors = im.convert("RGBA").getcolors(w * h)
    dominant = colors[0]
    for count, color in colors:
        cmax, cmin = max(color[:3]), min(color[:3])
        lightness = (cmax + cmin) / 2
        if lightness > 51 and count > dominant[0]:
            # Discard transparent & dark pixels (lightness < 20%)
            dominant = (count, color)
    r, g, b, _ = dominant[1]
    return r, g, b


def yes_or_no(s):
    return s.lower() in ("yes", "no")


def url_to_file(url):
    r = requests.get(url)
    if r.status_code == 200:
        return io.BytesIO(r.content)
    r.raise_for_status()


def base64_to_file(data):
    return io.BytesIO(base64.b64decode(data))


def get_timestamp(*, format="%Y-%m-%d %H:%M:%S", wrap=lambda ts: f"[{ts}]"):
    return wrap(datetime.datetime.now().strftime(format))


def strict_whitespace(s):
    return " ".join(s.split())


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
