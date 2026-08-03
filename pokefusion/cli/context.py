from functools import cached_property

import typer

from pokefusion.configmanager import BotConfig, ConfigManager
from pokefusion.db.migrations import MigrationService
from pokefusion.log import setup_logging


class Context:
    def __init__(self, *, require_confirmation: bool = False, action: str | None = None):
        self.config: BotConfig = ConfigManager.get_bot_config()
        setup_logging(self.config.logging)

        if require_confirmation:
            typer.confirm(f"[{self.config.environment.upper()}] {action or 'This operation'} - continue?", abort=True)

    @cached_property
    def migration_service(self) -> MigrationService:
        return MigrationService(self.config.database)
