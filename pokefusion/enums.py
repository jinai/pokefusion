from enum import StrEnum, auto


class Environment(StrEnum):
    PROD = auto()
    STAGING = auto()
    DEV = auto()


class Language(StrEnum):
    FR = auto()
    EN = auto()
    DE = auto()
