import logging
import shlex
import subprocess
from collections.abc import Sequence
from os import PathLike

type StrPath = str | PathLike[str]

logger = logging.getLogger(__name__)


def run_git(arguments: Sequence[str], *, cwd: StrPath | None = None) -> None:
    command = ["git", *arguments]

    logger.info(f"Running command: {shlex.join(command)}")

    process = subprocess.Popen(
        command,
        bufsize=1,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=cwd,
        text=True,
        errors="replace"
    )

    # noinspection not-iterable
    for line in process.stdout:
        logger.info(f"[git] {line.rstrip()}")

    returncode = process.wait()

    if returncode:
        raise subprocess.CalledProcessError(returncode, command)


def restore_deleted_files() -> None:
    list_command = ["git", "ls-files", "--deleted", "-z"]
    logger.info(f"Running command: {shlex.join(list_command)}")

    result = subprocess.run(
        list_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    for line in result.stderr.decode(errors="replace").splitlines():
        logger.error(f"[git] {line}")

    result.check_returncode()

    if not result.stdout:
        logger.info("No deleted files to restore")
        return

    deleted_count = result.stdout.count(b"\0")
    logger.info(f"Restoring {deleted_count} deleted files")

    restore_command = [
        "git",
        "restore",
        "--pathspec-from-file=-",
        "--pathspec-file-nul",
    ]
    logger.info(f"Running command: {shlex.join(restore_command)}")

    result = subprocess.run(
        restore_command,
        input=result.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    for line in result.stdout.decode(errors="replace").splitlines():
        logger.info(f"[git] {line}")

    result.check_returncode()
