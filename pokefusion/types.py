from os import PathLike

from pokefusion.utils import TwoWayDict

type RawDex = dict[str, dict[str, str]]
type Dex = dict[str, TwoWayDict[str, str]]
type StrPath = str | PathLike[str]
