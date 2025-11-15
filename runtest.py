import json
from datetime import date, timedelta

from hyphen import Hyphenator

from pokefusion.cogs.cogutils import WeekDay
from pokefusion.configmanager import ConfigManager
from pokefusion.environment import Environment
from pokefusion.models import models
from tools.dbutils import create_migration, keyval_store, run_migrations


def next_weekday(d: date, weekday: WeekDay) -> date:
    days_ahead = weekday - d.isoweekday()
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    return d + timedelta(days_ahead)


def main() -> None:
    day = WeekDay.THURSDAY
    day2 = WeekDay(4)
    print(day is day2)

    today = date.today()
    for i in range(WeekDay.SUNDAY):
        weekday = WeekDay(i + 1)
        print(next_weekday(today, weekday))


def create_db(env: Environment) -> None:
    config = ConfigManager.get_bot_config(env)
    models.init_db(config.database, drop_tables=True)


def migrate_db(env: Environment) -> None:
    config = ConfigManager.get_bot_config(env)
    create_migration(config.database)


def keyval_db(env: Environment) -> None:
    config = ConfigManager.get_bot_config(env)
    keyval_store(config.database)


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
    # create_db(env)
    # migrate_db(env)
    run_migrations(config.database)
    # keyval_db(env)


if __name__ == "__main__":
    main()
