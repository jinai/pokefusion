import base64
import io
import json
from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Any

import unidecode

type JsonDict = dict[str, Any]


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


def load_json(path: str) -> JsonDict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_timestamp(*, fmt: str = "%d %b %H:%M:%S", wrap: Callable[[str], str] = lambda ts: f"[{ts}]") -> str:
    ts = datetime.now().strftime(fmt)
    if callable(wrap):
        return wrap(ts)
    return ts


def yes(s: str) -> bool:
    return s.lower() in ("y", "yes", "o", "oui")


def no(s: str) -> bool:
    return s.lower() in ("n", "no", "non")


def normalize(text: str, wrap: Callable[[str], str] = lambda s: s.title()) -> str:
    return unidecode.unidecode(wrap(text))


def base64_to_file(data: str) -> io.BytesIO:
    return io.BytesIO(base64.b64decode(data))


def cleanup_code(content: str) -> str:
    if content.startswith('```') and content.endswith('```'):
        return '\n'.join(content.split('\n')[1:-1])
    return content.strip('` \n')


def replace_all(text: str, dic: dict[str, str]) -> str:
    for i, j in dic.items():
        text = text.replace(i, j)
    return text


def remove_extra_spaces(text: str) -> str:
    return " ".join(text.split())


def special_join(sequence: Sequence[Any], main_join: str, last_join: str) -> str:
    if len(sequence) == 0:
        return ""
    elif len(sequence) == 1:
        return sequence[0]
    elif len(sequence) == 2:
        return last_join.join(sequence)
    else:
        return main_join.join(sequence[:-1]) + last_join + str(sequence[-1])
