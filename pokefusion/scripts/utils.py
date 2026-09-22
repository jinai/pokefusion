import platform
import re
import shutil
import subprocess
from collections.abc import Generator, Iterable
from datetime import UTC, datetime
from pathlib import Path

from pokefusion.types import StrPath


def regex_filter(sequence: Iterable[str], pattern: re.Pattern[str]) -> Generator[str]:
    for elem in sequence:
        if pattern.match(elem):
            yield elem


def make_backup(path: StrPath):
    src = Path(path)
    counter = 1
    date_suffix = datetime.now(UTC).strftime("_%Y%m%d")
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


def fast_delete(path: StrPath) -> None:
    path = Path(path)
    resolved_path = path.resolve()

    protected_paths = {
        Path(resolved_path.anchor),
        Path.cwd().resolve(),
        Path.home().resolve(),
    }

    if resolved_path in protected_paths:
        raise ValueError(f"Preventing deletion of protected directory: {resolved_path}")

    system = platform.system()

    if system in ("Linux", "Darwin"):
        subprocess.run(["rm", "-rf", "--", path], check=True)
    elif system == "Windows":
        subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", path], check=True)
    else:
        shutil.rmtree(path)
