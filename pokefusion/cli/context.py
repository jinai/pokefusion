import typer

from pokefusion.configmanager import BotConfig, ConfigManager
from pokefusion.db.migrations import MigrationService
from pokefusion.environment import Environment
from pokefusion.log import setup_logging


class Context:
    def __init__(self, env: Environment, *, require_confirmation: bool = False, action: str | None = None, ):
        if require_confirmation:
            typer.confirm(f"[{env}] {action or 'This operation'} - continue?", abort=True)
        self.env = env
        setup_logging(env)
        self.config: BotConfig = ConfigManager.get_bot_config(env)
        self._migration_service = None

    @property
    def migration_service(self):
        if self._migration_service is None:
            self._migration_service = MigrationService(self.env)
        return self._migration_service
