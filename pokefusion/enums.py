from enum import StrEnum, auto


class Environment(StrEnum):
    PROD = auto()
    DEV = auto()


class Language(StrEnum):
    FR = auto()
    EN = auto()
    DE = auto()
    DEFAULT = FR
