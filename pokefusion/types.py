from os import PathLike

from pokefusion.utils import TwoWayDict

type StrPath = str | PathLike[str]

type RawDex = dict[str, dict[str, str]]
type Dex = dict[str, TwoWayDict[str, str]]
type FusionMapping = dict[int, list[int]]
