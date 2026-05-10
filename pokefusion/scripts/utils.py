import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Generator, Iterable


def regex_filter(sequence: Iterable[str], pattern: re.Pattern[str]) -> Generator[str, None, None]:
    for elem in sequence:
        if pattern.match(elem):
            yield elem


def make_backup(path):
    src = Path(path)
    counter = 1
    date_suffix = datetime.now().strftime("_%Y%m%d")
    backup_name = f"{src.stem}{date_suffix}_{counter:02d}{src.suffix}"
    backup_path = src.parent / backup_name
    while backup_path.exists():
        counter += 1
        backup_name = f"{src.stem}{date_suffix}_{counter:02d}{src.suffix}"
        backup_path = src.parent / backup_name

    if src.is_file():
        shutil.copy2(src, backup_path)
    elif src.is_dir():
        shutil.copytree(src, backup_path)

    return backup_path
