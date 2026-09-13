import logging
import shlex
import subprocess
from collections.abc import Sequence

from pokefusion.types import StrPath

logger = logging.getLogger(__name__)


def run_git(arguments: Sequence[str], *, cwd: StrPath | None = None) -> None:
    command = ["git", *arguments]

    logger.info("Running command: %s", shlex.join(command))

    process = subprocess.Popen(
        command,
        bufsize=1,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=cwd,
        text=True,
        errors="replace",
    )

    # noinspection not-iterable
    for line in process.stdout:
        logger.info("[git] %s", line.rstrip("\r\n"))

    returncode = process.wait()

    if returncode:
        raise subprocess.CalledProcessError(returncode, command)


def restore_deleted_files() -> None:
    list_command = ["git", "ls-files", "--deleted", "-z"]
    logger.info("Running command: %s", shlex.join(list_command))

    result = subprocess.run(list_command, capture_output=True, check=False)

    for line in result.stderr.decode(errors="replace").splitlines():
        logger.error("[git] %s", line)

    result.check_returncode()

    if not result.stdout:
        logger.info("No deleted files to restore")
        return

    deleted_count = result.stdout.count(b"\0")
    logger.info("Restoring %d deleted files", deleted_count)

    restore_command = [
        "git",
        "restore",
        "--pathspec-from-file=-",
        "--pathspec-file-nul",
    ]
    logger.info("Running command: %s", shlex.join(restore_command))

    result = subprocess.run(
        restore_command,
        input=result.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    for line in result.stdout.decode(errors="replace").splitlines():
        logger.info("[git] %s", line)

    result.check_returncode()
