import logging
from datetime import datetime
from logging import LogRecord
from logging.handlers import TimedRotatingFileHandler
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pokefusion.configmanager import LoggingColorConfig, LoggingConfig


class TimezoneFormatter(logging.Formatter):
    def __init__(self, fmt: str, datefmt: str, timezone: str | None, ) -> None:
        super().__init__(fmt=fmt, datefmt=datefmt)

        if timezone is None:
            self.timezone = None
            return

        try:
            self.timezone = ZoneInfo(timezone)
        except ZoneInfoNotFoundError as error:
            raise ValueError(f"Unknown logging timezone: {timezone!r}") from error

    def formatTime(self, record: LogRecord, datefmt: str | None = None, ) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=self.timezone)

        if datefmt is not None:
            return timestamp.strftime(datefmt)

        return timestamp.isoformat(timespec="seconds")


class ColorFormatter(TimezoneFormatter):
    def __init__(self, fmt: str, datefmt: str, timezone: str | None, colors: LoggingColorConfig) -> None:
        super().__init__(fmt=fmt, datefmt=datefmt, timezone=timezone)
        self.colors = colors
        self.level_colors = {
            logging.DEBUG: colors.debug,
            logging.INFO: colors.info,
            logging.WARNING: colors.warning,
            logging.ERROR: colors.error,
            logging.CRITICAL: colors.critical
        }

    def format(self, record: LogRecord) -> str:
        record.time_color = self.colors.time
        record.level_color = self.level_colors.get(record.levelno, self.colors.reset)
        record.name_color = self.colors.name
        record.reset = self.colors.reset
        return super().format(record)


def setup_logging(config: LoggingConfig):
    config.path.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(config.level)

    file_handler = TimedRotatingFileHandler(
        filename=config.path,
        encoding=config.encoding,
        errors=config.errors,
        when=config.rotation.when,
        interval=config.rotation.interval,
        backupCount=config.rotation.backup_count,
        delay=config.rotation.delay,
        utc=config.rotation.utc,
        atTime=config.rotation.at_time,
    )
    file_handler.setLevel(config.level)
    file_handler.setFormatter(
        TimezoneFormatter(
            fmt=config.file_format,
            datefmt=config.date_format,
            timezone=config.timezone,
        )
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(config.level)
    stream_handler.setFormatter(
        ColorFormatter(
            fmt=config.console_format,
            datefmt=config.date_format,
            timezone=config.timezone,
            colors=config.colors
        )
    )

    root.addHandler(file_handler)
    root.addHandler(stream_handler)
