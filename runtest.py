import json
from datetime import date, timedelta

from hyphen import Hyphenator

from pokefusion.cogs.cogutils import WeekDay
from pokefusion.configmanager import ConfigManager
from pokefusion.environment import Environment
from pokefusion.models import models
from pokefusion.tools.dbutils import create_migration, run_migrations


def next_weekday(d: date, weekday: WeekDay) -> date:
    days_ahead = weekday - d.isoweekday()
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    return d + timedelta(days_ahead)


def create_db(env: Environment) -> None:
    config = ConfigManager.get_bot_config(env)
    models.init_db(config.database, drop_tables=True)


# def keyval_db(env: Environment) -> None:
#     config = ConfigManager.get_bot_config(env)
#     keyval_store(config.database)


def hyphens() -> None:
    with open("pokefusion/config/pokedex_fr.json", "r", encoding="utf-8") as f:
        dex = json.load(f)

    h = Hyphenator("fr_FR")
    for name in dex.values():
        print(h.syllables(name))


def main():
    import logging

    logging.basicConfig(level=logging.INFO)
    env = Environment.PROD
    config = ConfigManager.get_bot_config(env)
    run_migrations(config.database)
    # create_migration(config.database, "remove_seeds")
    # # rollback_migration(config.database)


if __name__ == "__main__":
    main()
