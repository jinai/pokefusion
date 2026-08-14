from os import PathLike

from pokefusion.utils import TwoWayDict

type Dex = dict[str, TwoWayDict[str, str]]
type StrPath = str | PathLike[str]
